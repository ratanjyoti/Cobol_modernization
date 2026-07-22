from typing import List, Optional
import asyncio
import json
import os
import re
import shutil
import stat
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.orm import Session

from Persistence.neo4j.graph_service import GraphService
from Persistence.sqlite.models import FileChunk, FileComplexity, FileRelation, FileStatus, ProjectFile, ProjectComplexity
from Persistence.sqlite.session import SessionLocal, get_db
from Processes.discovery_process import DiscoveryProcess, GitHubIngestionError
from Processes.graphing_process import GraphingProcess
from Processes.analysis_process import AnalysisProcess
from Config.llm_config import settings
from source.websockets.socket_manager import manager
from Chunking.chunking_orchestrator import ChunkingOrchestrator
from Chunking.core.complexity_manager import ComplexityManager
from Chunking.dependency_scanner.resolution_service import ResolutionService
from paths import UPLOADS_DIR


router = APIRouter(prefix="/discovery", tags=["Discovery"])


def path_safe(filename: str | None) -> str:
    return os.path.basename(filename or "upload.zip")


def save_file_sync(upload_file: UploadFile, destination: Path):
    """Helper for asyncio.to_thread."""
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


def remove_tree_sync(path: Path):
    def handle_remove_error(func, failed_path, _exc_info):
        os.chmod(failed_path, stat.S_IWRITE)
        func(failed_path)

    if path.exists():
        shutil.rmtree(path, onerror=handle_remove_error)

def parse_calculation(calculation: str | None):
    if not calculation:
        return []
    try:
        parsed = json.loads(calculation)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


LEGACY_CALCULATION_LABELS = {
    "IF statements",
    "PERFORM UNTIL loops",
    "PERFORM VARYING loops",
    "EVALUATE branches",
    "Unique SQL tables",
}


def has_current_calculation(calculation: list) -> bool:
    return any(
        isinstance(item, dict)
        and item.get("label")
        and item.get("label") not in LEGACY_CALCULATION_LABELS
        for item in calculation
    )


def normalize_calculation_labels(calculation: list) -> list:
    normalized = []
    for item in calculation:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        if not label:
            continue
        normalized.append({
            **item,
            "label": re.sub(r"\((\d+)x(\d+)\)", r"(\1 x \2)", label),
        })
    return normalized


def safe_relative_upload_path(rel_path: str | None) -> Path | None:
    normalized = (rel_path or "").replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part]
    if not parts or any(part in {".", ".."} for part in parts) or any(":" in part for part in parts):
        return None
    path = Path(*parts)
    return None if path.is_absolute() else path


def uploaded_file_candidates(run_id: str, filepath: str | None, filename: str | None) -> list[Path]:
    project_folder = UPLOADS_DIR / run_id
    candidates = []
    rel_path = safe_relative_upload_path(filepath or filename)
    if rel_path is not None:
        candidates.append(project_folder / rel_path)
        candidates.append(project_folder / "local_repo" / rel_path)
    if filename:
        candidates.append(project_folder / filename)
    return candidates


def read_uploaded_file_content(run_id: str, filepath: str | None, filename: str | None) -> str:
    for candidate in uploaded_file_candidates(run_id, filepath, filename):
        try:
            if candidate.exists() and candidate.is_file():
                return candidate.read_text(errors="ignore")
        except OSError as exc:
            print(f"Could not read file {candidate}: {exc}")
    return ""


def infer_file_language(project_file: ProjectFile | None, filename: str | None) -> str:
    detected_lang = (project_file.detected_lang if project_file else "") or ""
    if detected_lang.strip():
        return detected_lang

    suffix = Path(filename or "").suffix.lower()
    if suffix in {".cbl", ".cob", ".cpy"}:
        return "cobol"
    if suffix == ".jcl":
        return "jcl"
    if suffix in {".tln", ".tel"}:
        return "telon"
    return "unknown"

def run_analysis_task(run_id: str):
    """Build dependency maps and analysis data after upload without blocking the response."""
    db = SessionLocal()
    try:
        result = DiscoveryProcess(db).analyze_run(run_id)
        print(f"Background analysis completed for {run_id}: {result}")
    except Exception as exc:
        db.rollback()
        print(f"Background analysis failed for {run_id}: {exc}")
    finally:
        db.close()

# 1. THE COMPLEXITY TAB DATA
@router.get("/complexity/{run_id}")
async def get_complexity(run_id: str, db: Session = Depends(get_db)):
    proj_comp = db.query(ProjectComplexity).filter_by(run_id=run_id).first()
    file_scores = db.query(FileComplexity).filter_by(run_id=run_id).order_by(FileComplexity.score.desc()).all()
    scorer = ComplexityManager()

    file_breakdown = []
    total_score = 0
    for fs in file_scores:
        chunk_count = db.query(FileChunk).filter(
            FileChunk.run_id == run_id,
            FileChunk.file_id == fs.file_id,
        ).count()

        project_file = None
        if fs.file_id:
            project_file = db.query(ProjectFile).filter(
                ProjectFile.run_id == run_id,
                ProjectFile.id == fs.file_id,
            ).first()

        calculation = normalize_calculation_labels(parse_calculation(fs.calculation))
        score = fs.score or 0
        tier = fs.tier or "Low"
        mode = fs.mode or fs.effort or "Turbo"
        multiplier = fs.multiplier or 1.5

        if not has_current_calculation(calculation):
            content = read_uploaded_file_content(run_id, fs.filepath, fs.filename)
            if content:
                lang = infer_file_language(project_file, fs.filename)
                recalculated = scorer.score_file(content, lang)
                if recalculated.get("calculation"):
                    calculation = normalize_calculation_labels(recalculated["calculation"])
                    score = recalculated["score"]
                    tier = recalculated["tier"]
                    mode = recalculated["mode"]
                    multiplier = recalculated["multiplier"]

        total_score += score
        file_breakdown.append({
            "id": str(fs.file_id or fs.id),
            "name": fs.filename,
            "filename": fs.filename,
            "filepath": fs.filepath,
            "score": score,
            "tier": tier,
            "effort": mode,
            "mode": mode,
            "multiplier": multiplier,
            "chunks": chunk_count or 1,
            "logic_count": fs.logic_count or 0,
            "table_count": fs.table_count or 0,
            "table_bonus": fs.table_bonus or 0,
            "if_count": fs.if_count or 0,
            "perform_until_count": fs.perform_until_count or 0,
            "perform_varying_count": fs.perform_varying_count or 0,
            "evaluate_count": fs.evaluate_count or 0,
            "calculation": calculation,
        })

    average_score = round(total_score / len(file_scores), 1) if file_scores else 0
    return {
        "overall_tier": proj_comp.tier if proj_comp else "Unknown",
        "overall_effort": proj_comp.reasoning_effort if proj_comp else "Balanced",
        "average_score": average_score,
        "files": file_breakdown,
        "method": "Language-specific complexity scoring. COBOL uses weighted indicators plus density/proximity/database bonuses; JCL uses step, DD, include, output, and conditional intensity; Telon uses panel, screen, map, and field density. Score < 5 uses Turbo, 5-14 uses Balanced, and 15+ uses Thorough.",
    }

# 2. THE DEPENDENCIES TAB DATA
@router.get("/graph/{run_id}")
async def get_graph_data(run_id: str, db: Session = Depends(get_db)):
    try:
        ResolutionService(db).resolve_run_relations(run_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Dependency resolution skipped for {run_id}: {exc}")

    graph_refreshed = False
    try:
        GraphingProcess(db).build_full_graph(run_id)
        graph_refreshed = True
    except Exception as exc:
        print(f"Neo4j graph refresh skipped for {run_id}: {exc}")

    graph_service = None
    try:
        if not graph_refreshed:
            raise RuntimeError("Skipping Neo4j read because graph refresh did not complete")
        graph_service = GraphService()
        graph_data = graph_service.get_graph(run_id)
        if graph_data["nodes"] or graph_data["edges"]:
            return graph_data
    except Exception as exc:
        print(f"Neo4j graph read skipped for {run_id}: {exc}")
    finally:
        if graph_service is not None:
            graph_service.close()

    files = db.query(ProjectFile).filter(ProjectFile.run_id == run_id).all()
    relations = db.query(FileRelation).filter(FileRelation.run_id == run_id).all()

    nodes_by_id = {}

    def frontend_type(filename: str, detected_lang: str | None):
        name = (filename or "").lower()
        lang = (detected_lang or "").lower()

        if "jcl" in lang or name.endswith(".jcl"):
            return "job"
        if "copy" in lang or name.endswith(".cpy"):
            return "copybook"
        if "cobol" in lang or name.endswith((".cbl", ".cob")):
            return "program"
        if name.endswith((".sql", ".ddl")):
            return "table"
        return "file"

    for file in files:
        node_id = file.filepath or file.filename
        nodes_by_id[node_id] = {
            "id": node_id,
            "label": file.filename,
            "type": frontend_type(file.filename, file.detected_lang),
            "filepath": file.filepath,
            "resolved": True,
        }

    edges = []

    for relation in relations:
        source = relation.source_file
        target = relation.target_item
        rel_type = relation.relation_type or "REFERENCES"

        if source not in nodes_by_id:
            continue

        if target not in nodes_by_id:
            nodes_by_id[target] = {
                "id": target,
                "label": target.split("/")[-1],
                "type": "external",
                "filepath": target,
                "resolved": False,
            }
            rel_type = "UNRESOLVED"

        edges.append({
            "id": str(relation.id),
            "from": source,
            "to": target,
            "type": rel_type,
            "relationType": rel_type,
        })

    return {
        "nodes": list(nodes_by_id.values()),
        "edges": edges,
    }

# 3. THE DDD TAB DATA
@router.get("/ddd/{run_id}")
async def get_ddd_discovery(run_id: str, db: Session = Depends(get_db)):
    try:
        ResolutionService(db).resolve_run_relations(run_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Dependency resolution skipped for DDD {run_id}: {exc}")

    files = db.query(ProjectFile).filter(ProjectFile.run_id == run_id).all()
    valid_names = {file.filepath or file.filename for file in files}
    relations = db.query(FileRelation).filter(FileRelation.run_id == run_id).all()
    relations = [relation for relation in relations if relation.source_file in valid_names and relation.target_item in valid_names]

    domain_map = {
        "ACCESSES": {"name": "Data Access", "programs": set(), "rules": 0, "color": "bg-rose-500"},
        "READS": {"name": "Data Reads", "programs": set(), "rules": 0, "color": "bg-sky-500"},
        "WRITES": {"name": "Data Writes", "programs": set(), "rules": 0, "color": "bg-rose-500"},
        "CALLS": {"name": "Program Calls", "programs": set(), "rules": 0, "color": "bg-blue-500"},
        "EXECUTES": {"name": "Job Execution", "programs": set(), "rules": 0, "color": "bg-violet-500"},
        "MAPS_TO": {"name": "Telon Module Mapping", "programs": set(), "rules": 0, "color": "bg-indigo-500"},
        "INCLUDES": {"name": "Shared Copybooks", "programs": set(), "rules": 0, "color": "bg-emerald-500"},
        "UNLINKED": {"name": "Standalone Modules", "programs": set(), "rules": 0, "color": "bg-amber-500"},
    }

    linked_sources = set()
    for relation in relations:
        bucket = domain_map.get(relation.relation_type, domain_map["UNLINKED"])
        bucket["programs"].add(relation.source_file)
        bucket["rules"] += 1
        linked_sources.add(relation.source_file)

    for file in files:
        if file.filename not in linked_sources:
            domain_map["UNLINKED"]["programs"].add(file.filename)

    domains = []
    for domain in domain_map.values():
        if domain["programs"] or domain["rules"]:
            domains.append({
                "name": domain["name"],
                "programs": sorted(domain["programs"]),
                "rules": domain["rules"],
                "color": domain["color"],
            })

    return domains
@router.post("/upload-zip")
async def upload_zip(
    background_tasks: BackgroundTasks,
    run_id: str = Form(...),
    zip_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not zip_file.filename or not zip_file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file")

    upload_dir = UPLOADS_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_zip_path = upload_dir / f"temp_{run_id}.zip"

    try:
        await asyncio.to_thread(save_file_sync, zip_file, temp_zip_path)
        discovery = DiscoveryProcess(db)
        mapped_files = await discovery.process_zip_upload(run_id, str(temp_zip_path), analyze_inline=False)
        background_tasks.add_task(run_analysis_task, run_id)
        return {"status": "Success", "mapped_files": mapped_files, "analysis_status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing zip: {str(e)}")
    finally:
        if temp_zip_path.exists():
            os.remove(temp_zip_path)


@router.post("/launch")
async def launch_pipeline(
    background_tasks: BackgroundTasks,
    run_id: str = Form(...),
    source_lang: str = Form(""),
    target_lang: str = Form(""),
    scope: str = Form(""),
):
    # 1. Run Neo4j Graphing in background
    background_tasks.add_task(run_graphing_task, run_id)
    
    # 2. Run Smart Chunking, then Technical YAML, in order.
    background_tasks.add_task(run_chunking_then_analysis_task, run_id)

    return {
        "status": "Pipeline Launched",
        "run_id": run_id,
        "parallel_tasks": ["Neo4j_Graphing", "Semantic_Chunking", "Technical_Analysis"],
    }

def run_graphing_task(run_id: str):
    """Best-effort Neo4j graph build; SQLite remains the dependency source of truth."""
    db = SessionLocal()
    try:
        GraphingProcess(db).build_full_graph(run_id)
        print(f"Graphing completed for project {run_id}")
    except Exception as e:
        print(f"Graphing skipped for {run_id}: {str(e)}")
    finally:
        db.close()


def run_technical_analysis_task(run_id: str):
    """Generate Technical YAML rows consumed by business-rule extraction."""
    db = SessionLocal()
    try:
        provider = "openrouter" if settings.OPENROUTER_API_KEY else "local"
        asyncio.run(AnalysisProcess(db, provider).analyze_project(run_id))
        print(f"Technical analysis completed for project {run_id}")
    except Exception as e:
        db.rollback()
        print(f"Technical analysis failed for {run_id}: {str(e)}")
    finally:
        db.close()


def run_chunking_then_analysis_task(run_id: str):
    run_chunking_task(run_id)
    run_technical_analysis_task(run_id)


def run_chunking_task(run_id: str):
    """Process all confirmed files through the Smart Chunker."""
    db = SessionLocal()
    try:
        # 1. Get only files that the human confirmed the language for
        from Persistence.sqlite.models import ProjectFile, FileStatus
        confirmed_files = db.query(ProjectFile).filter(
            ProjectFile.run_id == run_id,
            ProjectFile.status == FileStatus.CONFIRMED
        ).all()

        orchestrator = ChunkingOrchestrator(db)
        
        for f in confirmed_files:
            # Construct path to the file
            full_path = UPLOADS_DIR / run_id / f.filename
            if full_path.exists():
                with open(full_path, 'r', errors='ignore') as file_handle:
                    content = file_handle.read()
                    # This does the Sizing -> Slicing -> SQLite storing
                    orchestrator.process_file(
                        run_id=run_id,
                        file_id=f.id,
                        filename=f.filename,
                        content=content,
                        lang=f.detected_lang
                    )
        print(f"Chunking completed for project {run_id}")
    except Exception as e:
        print(f"Chunking Error for {run_id}: {str(e)}")
    finally:
        db.close()


@router.get("/impact/{item_name}")
@router.get("/impact-analysis/{item_name}")
async def get_impact_analysis(item_name: str):
    """
    Returns programs affected by the selected dependency item.
    """
    graph_service = None
    try:
        graph_service = GraphService()
        impacted_programs = graph_service.get_impacted_programs(item_name)

        return {
            "target": item_name,
            "impacted_programs": impacted_programs,
            "count": len(impacted_programs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if graph_service is not None:
            graph_service.close()


@router.post("/upload-folder")
async def upload_folder(
    background_tasks: BackgroundTasks,
    run_id: str = Form(...),
    files: List[UploadFile] = File(...),
    paths: List[str] = Form(...),
    db: Session = Depends(get_db),
):
    try:
        discovery = DiscoveryProcess(db)
        mapped_files = await discovery.process_folder_upload(run_id, files, paths, analyze_inline=False)
        background_tasks.add_task(run_analysis_task, run_id)
        return {"status": "Success", "mapped_files": mapped_files, "analysis_status": "queued"}
    except Exception as e:
        print(f"Folder upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Folder upload failed: {str(e)}")


@router.post("/local-repo")
async def ingest_local_repo(
    background_tasks: BackgroundTasks,
    run_id: str = Form(...),
    repo_path: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Ingests an existing local Git repository from the backend machine.
    The path must point to a folder containing a .git directory or file.
    """
    try:
        discovery = DiscoveryProcess(db)
        mapped_files = await discovery.ingest_local_git_repo(run_id, repo_path, analyze_inline=False)
        background_tasks.add_task(run_analysis_task, run_id)
        return {
            "status": "Success",
            "message": f"Successfully inventoried {len(mapped_files)} files from local repository",
            "mapped_files": mapped_files,
            "analysis_status": "queued",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Local repository ingestion failed: {str(e)}")


@router.post("/github")
async def ingest_github(
    background_tasks: BackgroundTasks,
    request: Request,
    run_id: Optional[str] = Form(None),
    repo_url: Optional[str] = Form(None),
    github_token: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Ingests a GitHub repository using the DiscoveryProcess logic.
    Accepts multipart form data from the current UI and JSON from older clients.
    """
    if run_id is None or repo_url is None:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            payload = await request.json()
            run_id = run_id or payload.get("run_id")
            repo_url = repo_url or payload.get("repo_url") or payload.get("url")
            github_token = github_token or payload.get("github_token")

    if not run_id or not repo_url:
        raise HTTPException(status_code=400, detail="Missing run_id or repo_url")

    repo_url = repo_url.strip()
    github_token = github_token.strip() if github_token else None

    if not repo_url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL. Must be a github.com URL.")

    try:
        discovery = DiscoveryProcess(db)
        mapped_files = await discovery.ingest_github_repo(run_id, repo_url, github_token, analyze_inline=False)
        background_tasks.add_task(run_analysis_task, run_id)

        return {
            "status": "Success",
            "message": f"Successfully ingested {len(mapped_files)} files from GitHub",
            "mapped_files": mapped_files,
            "analysis_status": "queued",
        }
    except GitHubIngestionError as e:
        print(f"GitHub Error: {str(e)}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        print(f"GitHub Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"GitHub ingestion failed unexpectedly: {str(e)}")

@router.post("/upload")
async def upload_source(
    background_tasks: BackgroundTasks,
    run_id: str = Form(...),
    files: Optional[List[UploadFile]] = File(None),
    zip_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    discovery = DiscoveryProcess(db)

    if zip_file:
        upload_dir = UPLOADS_DIR
        upload_dir.mkdir(parents=True, exist_ok=True)
        temp_path = upload_dir / path_safe(zip_file.filename)

        try:
            await asyncio.to_thread(save_file_sync, zip_file, temp_path)
            mapped_files = await discovery.process_upload(run_id, str(temp_path), analyze_inline=False)
        finally:
            if temp_path.exists():
                os.remove(temp_path)
    elif files:
        mapped_files = await discovery.process_individual_files(run_id, files, analyze_inline=False)
    else:
        raise HTTPException(status_code=400, detail="No files uploaded")

    background_tasks.add_task(run_analysis_task, run_id)
    return {"status": "Success", "mapped_files": mapped_files, "analysis_status": "queued"}


@router.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    await manager.connect(websocket, run_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)


@router.post("/confirm-language")
async def confirm_language(
    data: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    run_id = data.get("run_id")
    filename = data.get("filename")
    lang = data.get("lang")
    file_id = data.get("file_id")
    filepath = data.get("filepath")

    if not all([run_id, filename, lang]):
        raise HTTPException(status_code=400, detail="Missing run_id, filename, or lang")

    query = db.query(ProjectFile).filter(ProjectFile.run_id == run_id)
    file_record = None

    if file_id:
        try:
            file_record = query.filter(ProjectFile.id == int(file_id)).first()
        except (TypeError, ValueError):
            file_record = None

    if not file_record and filepath:
        normalized_path = filepath.replace("\\", "/")
        file_record = query.filter(ProjectFile.filepath == filepath).first()
        if not file_record and normalized_path != filepath:
            file_record = query.filter(ProjectFile.filepath == normalized_path).first()

    if not file_record:
        file_record = query.filter(ProjectFile.filename == filename).first()

    if not file_record and filepath:
        basename = filepath.replace("\\", "/").split("/")[-1]
        file_record = query.filter(ProjectFile.filename == basename).first()

    if not file_record:
        raise HTTPException(status_code=404, detail="File is not ready for confirmation yet. Please try again.")

    try:
        normalized_lang = str(lang).strip().lower() or "unknown"
        file_record.detected_lang = normalized_lang
        file_record.status = FileStatus.CONFIRMED
        db.commit()
        db.refresh(file_record)
        background_tasks.add_task(run_analysis_task, run_id)
        return {
            "status": "Success",
            "message": f"Language updated to {normalized_lang} for {file_record.filename}",
            "file": {
                "id": str(file_record.id),
                "filename": file_record.filename,
                "filepath": file_record.filepath,
                "detected_lang": file_record.detected_lang,
                "status": file_record.status.value if file_record.status else None,
                "is_valid": file_record.status == FileStatus.CONFIRMED,
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")








