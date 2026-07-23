# Implementation for project.py
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pathlib import Path
import os
import shutil
import stat
import datetime
import requests
from Processes.graphing_process import GraphingProcess
from Processes.onboarding_process import OnboardingProcess
from Persistence.neo4j.graph_service import GraphService
from Chunking.dependency_scanner.resolution_service import ResolutionService
from Config.llm_config import settings
from Persistence.sqlite.models import BusinessRule, ChunkAnalysis, FileAnalysis, FileChunk, FileComplexity, FileRelation, Project, ProjectComplexity, ProjectFile
from Persistence.sqlite.project_repo import ProjectRepository
from Persistence.sqlite.session import SessionLocal, get_db
from paths import UPLOADS_DIR

router = APIRouter(prefix="/projects", tags=["Projects"])
SERVICE_HEALTH_CACHE: dict[str, dict] = {}


def mask_api_key(api_key: str | None):
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:5]}****{api_key[-4:]}"


def mask_secret(secret: str | None):
    if not secret:
        return None
    if len(secret) <= 4:
        return "****"
    return f"****{secret[-4:]}"


def api_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:500] or response.reason

    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or payload)[:500]
    if error:
        return str(error)[:500]
    return str(payload)[:500]


def remove_tree_sync(path: Path):
    def handle_remove_error(func, failed_path, _exc_info):
        try:
            os.chmod(failed_path, stat.S_IWRITE)
            func(failed_path)
        except PermissionError:
            pass

    if not path.exists():
        return

    try:
        for child in path.rglob("*"):
            try:
                os.chmod(child, stat.S_IWRITE)
            except OSError:
                pass
        os.chmod(path, stat.S_IWRITE)
        shutil.rmtree(path, onerror=handle_remove_error)
    except PermissionError as exc:
        print(f"Warning: could not fully remove upload directory {path}: {exc}")


def clear_uploads_sync(upload_dir: Path):
    if not upload_dir.exists():
        return
    for child in upload_dir.iterdir():
        if child.is_dir():
            remove_tree_sync(child)
        else:
            child.unlink(missing_ok=True)


def get_project_status(files):
    if not files:
        return "CONFIGURING"

    statuses = [project_file.status.value if project_file.status else "PENDING_CONFIRMATION" for project_file in files]
    if any(status == "REJECTED" for status in statuses):
        return "FAILED"
    if all(status == "CONFIRMED" for status in statuses):
        return "ANALYZING"
    return "INGESTING"


def serialize_project(project, files=None):
    files = files if files is not None else []
    file_status_counts = {}
    language_counts = {}

    for project_file in files:
        status = project_file.status.value if project_file.status else "PENDING_CONFIRMATION"
        file_status_counts[status] = file_status_counts.get(status, 0) + 1
        language = project_file.detected_lang or "unknown"
        language_counts[language] = language_counts.get(language, 0) + 1

    return {
        "run_id": project.run_id,
        "name": project.project_name,
        "status": get_project_status(files),
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "files_count": len(files),
        "target": project.llm_model,
        "llm_provider": project.llm_provider,
        "ai_mode": project.ai_mode,
        "custom_api_base_url": project.custom_api_base_url,
        "has_custom_api_key": bool(project.custom_api_key),
        "llm_model": project.llm_model,
        "interaction_lang": project.interaction_lang,
        "neo4j_uri": project.neo4j_uri,
        "neo4j_user": project.neo4j_user,
        "has_neo4j_password": bool(project.neo4j_password),
        "speed_profile": project.speed_profile,
        "reasoning_effort": project.reasoning_effort,
        "parallel_workers": project.parallel_workers,
        "file_status_counts": file_status_counts,
        "language_counts": language_counts,
    }



def get_project_status_from_counts(files_count: int, file_status_counts: dict):
    if files_count == 0:
        return "CONFIGURING"
    if file_status_counts.get("REJECTED", 0) > 0:
        return "FAILED"
    if file_status_counts.get("CONFIRMED", 0) == files_count:
        return "ANALYZING"
    return "INGESTING"


def serialize_project_summary(project, files_count: int, file_status_counts: dict, language_counts: dict):
    return {
        "run_id": project.run_id,
        "name": project.project_name,
        "status": get_project_status_from_counts(files_count, file_status_counts),
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "files_count": files_count,
        "target": project.llm_model,
        "llm_provider": project.llm_provider,
        "ai_mode": project.ai_mode,
        "custom_api_base_url": project.custom_api_base_url,
        "has_custom_api_key": bool(project.custom_api_key),
        "llm_model": project.llm_model,
        "interaction_lang": project.interaction_lang,
        "neo4j_uri": project.neo4j_uri,
        "neo4j_user": project.neo4j_user,
        "has_neo4j_password": bool(project.neo4j_password),
        "speed_profile": project.speed_profile,
        "reasoning_effort": project.reasoning_effort,
        "parallel_workers": project.parallel_workers,
        "file_status_counts": file_status_counts,
        "language_counts": language_counts,
    }
def serialize_file(project_file):
    return {
        "id": str(project_file.id),
        "filename": project_file.filename,
        "filepath": project_file.filepath,
        "detected_lang": project_file.detected_lang,
        "status": project_file.status.value if project_file.status else None,
        "size": 0,
    }


def serialize_relation(relation):
    return {
        "id": str(relation.id),
        "source_file": relation.source_file,
        "target_item": relation.target_item,
        "relation_type": relation.relation_type,
    }


def refresh_dependency_map(run_id: str, db: Session):
    try:
        ResolutionService(db).resolve_run_relations(run_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        print(f"Dependency resolution skipped for {run_id}: {exc}")
        return False

    try:
        GraphingProcess(db).build_full_graph(run_id)
        return True
    except Exception as exc:
        print(f"Neo4j graph refresh skipped for {run_id}: {exc}")
        return False

def get_neo4j_discovery_data(run_id: str, project: Project | None = None):
    graph_service = None
    try:
        graph_service = GraphService.for_project(project)
        data = graph_service.get_discovery_data(run_id)
        if data["files"] or data["relations"]:
            return data
    except Exception as exc:
        print(f"Neo4j discovery-data read skipped for {run_id}: {exc}")
    finally:
        if graph_service is not None:
            graph_service.close()
    return None



def check_ai_api_status(project):
    mode = (project.ai_mode or project.llm_provider or "openrouter").lower()
    model = project.llm_model or ("llama3" if mode == "local" else settings.OPENROUTER_MODEL)

    if mode == "local":
        base_url = (project.custom_api_base_url or "http://localhost:11434").rstrip("/")
        local_provider = (project.local_provider or ("openai-compatible" if base_url.endswith("/v1") else "ollama")).lower()
        started = datetime.datetime.utcnow()

        def elapsed_ms():
            return int((datetime.datetime.utcnow() - started).total_seconds() * 1000)

        def openai_url():
            return base_url if base_url.endswith("/v1") else f"{base_url}/v1"

        errors = []

        if local_provider == "ollama":
            try:
                tags_response = requests.get(f"{base_url}/api/tags", timeout=(4, 8))
                if tags_response.status_code == 200:
                    tags_data = tags_response.json()
                    installed_models = [
                        item.get("name") or item.get("model")
                        for item in tags_data.get("models", [])
                        if item.get("name") or item.get("model")
                    ]
                    if model not in installed_models:
                        installed = ", ".join(installed_models) if installed_models else "none"
                        return {
                            "active": False,
                            "provider": "ollama",
                            "model": model,
                            "status": "MODEL_NOT_FOUND",
                            "detail": f"Model '{model}' is not installed. Installed models: {installed}.",
                        }

                    generate_response = requests.post(
                        f"{base_url}/api/generate",
                        json={
                            "model": model,
                            "prompt": "Reply with exactly: OK",
                            "stream": False,
                            "options": {"temperature": 0, "num_predict": 8},
                        },
                        timeout=(4, 45),
                    )
                    latency_ms = elapsed_ms()
                    if generate_response.status_code != 200:
                        return {
                            "active": False,
                            "provider": "ollama",
                            "model": model,
                            "status": "GENERATION_FAILED",
                            "detail": f"Model '{model}' failed to generate output. HTTP {generate_response.status_code}: {generate_response.text[:180]}",
                            "latency_ms": latency_ms,
                        }
                    output = (generate_response.json().get("response") or "").strip()
                    if not output:
                        return {
                            "active": False,
                            "provider": "ollama",
                            "model": model,
                            "status": "EMPTY_OUTPUT",
                            "detail": f"Model '{model}' responded, but the output was empty.",
                            "latency_ms": latency_ms,
                            "sample_output": "",
                        }
                    return {
                        "active": True,
                        "provider": "ollama",
                        "model": model,
                        "status": "READY",
                        "detail": f"Local model '{model}' generated output successfully in {latency_ms} ms.",
                        "latency_ms": latency_ms,
                        "sample_output": output[:120],
                    }
                errors.append(f"Ollama /api/tags returned HTTP {tags_response.status_code}")
            except Exception as exc:
                errors.append(f"Ollama check failed: {str(exc)[:180]}")
        else:
            errors.append("Ollama check skipped because local_provider is openai-compatible")

        try:
            api_base = openai_url()
            models_response = requests.get(f"{api_base}/models", timeout=(4, 8))
            if models_response.status_code != 200:
                return {
                    "active": False,
                    "provider": "openai-compatible",
                    "model": model,
                    "status": "SERVER_ERROR",
                    "detail": f"Local server is reachable, but model list failed at {api_base}/models. HTTP {models_response.status_code}: {models_response.text[:180]}. {' | '.join(errors)}",
                }

            models_data = models_response.json()
            installed_models = [
                item.get("id") or item.get("name")
                for item in models_data.get("data", [])
                if item.get("id") or item.get("name")
            ]
            if model not in installed_models:
                installed = ", ".join(installed_models) if installed_models else "none"
                return {
                    "active": False,
                    "provider": "openai-compatible",
                    "model": model,
                    "status": "MODEL_NOT_FOUND",
                    "detail": f"Model '{model}' is not available from the local server. Available models: {installed}.",
                }

            chat_response = requests.post(
                f"{api_base}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                    "temperature": 0,
                    "max_tokens": 8,
                    "stream": False,
                },
                timeout=(4, 45),
            )
            latency_ms = elapsed_ms()
            if chat_response.status_code != 200:
                return {
                    "active": False,
                    "provider": "openai-compatible",
                    "model": model,
                    "status": "GENERATION_FAILED",
                    "detail": f"Model '{model}' failed to generate output. HTTP {chat_response.status_code}: {chat_response.text[:180]}",
                    "latency_ms": latency_ms,
                }

            choices = chat_response.json().get("choices") or []
            message = choices[0].get("message") if choices else {}
            output = ((message or {}).get("content") or (choices[0].get("text") if choices else "") or "").strip()
            if not output:
                return {
                    "active": False,
                    "provider": "openai-compatible",
                    "model": model,
                    "status": "EMPTY_OUTPUT",
                    "detail": f"Model '{model}' responded, but the output was empty.",
                    "latency_ms": latency_ms,
                    "sample_output": "",
                }
            return {
                "active": True,
                "provider": "openai-compatible",
                "model": model,
                "status": "READY",
                "detail": f"Local model '{model}' generated output successfully in {latency_ms} ms.",
                "latency_ms": latency_ms,
                "sample_output": output[:120],
            }
        except requests.exceptions.ConnectionError as exc:
            return {
                "active": False,
                "provider": "local",
                "model": model,
                "status": "SERVER_NOT_RUNNING",
                "detail": f"Local LLM server is not reachable from the backend at {base_url}. Start the local server or use a reachable endpoint URL. {' | '.join(errors + [str(exc)[:180]])}",
            }
        except requests.exceptions.Timeout as exc:
            return {
                "active": False,
                "provider": "local",
                "model": model,
                "status": "TIMEOUT",
                "detail": f"Local LLM did not respond before timeout. {' | '.join(errors + [str(exc)[:180]])}",
            }
        except Exception as exc:
            return {
                "active": False,
                "provider": "local",
                "model": model,
                "status": "UNKNOWN_ERROR",
                "detail": f"Unexpected error while checking local LLM: {' | '.join(errors + [str(exc)[:180]])}",
            }

    api_key = project.custom_api_key or settings.OPENROUTER_API_KEY
    base_url = (project.custom_api_base_url or settings.OPENROUTER_BASE_URL).rstrip("/")

    if not api_key:
        return {
            "active": False,
            "provider": mode,
            "model": model,
            "detail": "Please add your OpenRouter API key in AI Configuration.",
            "has_api_key": False,
        }

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "ModernizerAI",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Reply only with OK."},
                    {"role": "user", "content": "health check"},
                ],
                "temperature": 0,
                "max_tokens": 8,
            },
            timeout=20,
        )
        if response.status_code >= 400:
            return {
                "active": False,
                "provider": mode,
                "model": model,
                "detail": f"OpenRouter rejected model '{model}': {api_error_message(response)}",
                "has_api_key": True,
            }

        content = response.json().get("choices", [{}])[0].get("message", {}).get("content") or ""
        return {
            "active": bool(content.strip()),
            "provider": mode,
            "model": model,
            "detail": "OpenRouter key and selected model are working." if content.strip() else f"OpenRouter key is saved, but model '{model}' did not return chat text. Choose a text chat model.",
            "has_api_key": True,
        }
    except Exception as exc:
        return {
            "active": False,
            "provider": mode,
            "model": model,
            "detail": f"OpenRouter health check failed: {str(exc)[:180]}",
            "has_api_key": True,
        }


def check_neo4j_status(project: Project | None = None):
    graph_service = None
    try:
        graph_service = GraphService.for_project(project)
        graph_service.driver.verify_connectivity()
        return {
            "active": True,
            "provider": "Neo4j",
            "detail": "Neo4j connection verified.",
        }
    except Exception as exc:
        return {
            "active": False,
            "provider": "Neo4j",
            "detail": str(exc)[:180],
        }
    finally:
        if graph_service is not None:
            graph_service.close()


def build_service_health(project: Project):
    return {
        "ai_api": check_ai_api_status(project),
        "neo4j": check_neo4j_status(project),
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }


def refresh_service_health_cache(run_id: str):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.run_id == run_id).first()
        if project:
            SERVICE_HEALTH_CACHE[run_id] = build_service_health(project)
    except Exception as exc:
        SERVICE_HEALTH_CACHE[run_id] = {
            "ai_api": {"active": False, "provider": "AI API", "detail": f"Health refresh failed: {str(exc)[:180]}"},
            "neo4j": {"active": False, "provider": "Neo4j", "detail": f"Health refresh failed: {str(exc)[:180]}"},
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        }
    finally:
        db.close()


def get_cached_service_health(run_id: str, project: Project):
    cached = SERVICE_HEALTH_CACHE.get(run_id)
    if cached:
        return cached
    SERVICE_HEALTH_CACHE[run_id] = build_service_health(project)
    return SERVICE_HEALTH_CACHE[run_id]

def clear_neo4j_run(run_id: str, project: Project | None = None):
    graph_service = None
    try:
        graph_service = GraphService.for_project(project)
        graph_service.clear_run(run_id)
    except Exception as exc:
        print(f"Neo4j clear skipped for {run_id}: {exc}")
    finally:
        if graph_service is not None:
            graph_service.close()

@router.get("")
async def list_projects(db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    projects = repo.list_projects()
    run_ids = [project.run_id for project in projects]
    file_status_counts = {run_id: {} for run_id in run_ids}
    language_counts = {run_id: {} for run_id in run_ids}
    files_count = {run_id: 0 for run_id in run_ids}

    if run_ids:
        status_rows = db.query(
            ProjectFile.run_id,
            ProjectFile.status,
            func.count(ProjectFile.id),
        ).filter(ProjectFile.run_id.in_(run_ids)).group_by(
            ProjectFile.run_id,
            ProjectFile.status,
        ).all()

        for run_id, status, count in status_rows:
            status_key = status.value if status else "PENDING_CONFIRMATION"
            file_status_counts[run_id][status_key] = count
            files_count[run_id] += count

        language_rows = db.query(
            ProjectFile.run_id,
            ProjectFile.detected_lang,
            func.count(ProjectFile.id),
        ).filter(ProjectFile.run_id.in_(run_ids)).group_by(
            ProjectFile.run_id,
            ProjectFile.detected_lang,
        ).all()

        for run_id, language, count in language_rows:
            language_counts[run_id][language or "unknown"] = count

    return [
        serialize_project_summary(
            project,
            files_count[project.run_id],
            file_status_counts[project.run_id],
            language_counts[project.run_id],
        )
        for project in projects
    ]

@router.post("")
@router.post("/create")
async def create_project(config: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    process = OnboardingProcess(db)
    result = process.create_new_project(config, user_id=1)
    if result.get("run_id"):
        background_tasks.add_task(refresh_service_health_cache, result["run_id"])
    return result


@router.delete("/runs")
async def delete_all_runs(db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    result = repo.delete_all_projects()
    clear_uploads_sync(UPLOADS_DIR)
    return {"status": "Success", **result}


@router.delete("/{run_id}")
async def delete_run(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_by_run_id(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    clear_neo4j_run(run_id, project)
    result = repo.delete_project(run_id)
    remove_tree_sync(UPLOADS_DIR / run_id)
    return {"status": "Success", **result}


@router.delete("/{run_id}/files")
async def clear_project_files(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_by_run_id(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    clear_neo4j_run(run_id, project)
    deleted_count = repo.delete_files_by_run_id(run_id)
    remove_tree_sync(UPLOADS_DIR / run_id)
    return {"status": "Success", "files_deleted": deleted_count}


@router.get("/{run_id}")
async def get_project(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_by_run_id(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return serialize_project(project, repo.get_files_by_run_id(run_id))





def count_by_status(rows, default_status="PENDING"):
    counts = {}
    for status, count in rows:
        key = status or default_status
        counts[key] = count
    return counts


def status_from_counts(total: int, complete: int, started: int = 0):
    if total <= 0 and started <= 0:
        return "Pending"
    if total > 0 and complete >= total:
        return "Complete"
    if started > 0 or complete > 0:
        return "In Progress"
    return "Pending"


@router.get("/{run_id}/dashboard-status")
async def get_project_dashboard_status(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_by_run_id(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    files = repo.get_files_by_run_id(run_id)
    serialized_project = serialize_project(project, files)
    files_total = len(files)
    confirmed_files = serialized_project["file_status_counts"].get("CONFIRMED", 0)
    rejected_files = serialized_project["file_status_counts"].get("REJECTED", 0)
    pending_files = max(files_total - confirmed_files - rejected_files, 0)

    relations_count = db.query(func.count(FileRelation.id)).filter(FileRelation.run_id == run_id).scalar() or 0
    critical_paths = db.query(func.count(FileRelation.id)).filter(
        FileRelation.run_id == run_id,
        FileRelation.relation_type.in_(["CALLS", "EXECUTES", "MAPS_TO"]),
    ).scalar() or 0
    shared_assets = db.query(func.count(FileRelation.id)).filter(
        FileRelation.run_id == run_id,
        FileRelation.relation_type.in_(["INCLUDES", "ACCESSES", "READS", "WRITES"]),
    ).scalar() or 0

    complexity_rows = db.query(FileComplexity).filter(FileComplexity.run_id == run_id).all()
    complexity_files = len(complexity_rows)
    complex_modules = len([
        row for row in complexity_rows
        if (row.tier or "").lower() in {"high", "very high"} or (row.score or 0) >= 15
    ])
    project_complexity = db.query(ProjectComplexity).filter(ProjectComplexity.run_id == run_id).first()

    chunk_total = db.query(func.count(FileChunk.id)).filter(FileChunk.run_id == run_id).scalar() or 0
    chunk_status_rows = db.query(FileChunk.status, func.count(FileChunk.id)).filter(
        FileChunk.run_id == run_id,
    ).group_by(FileChunk.status).all()
    chunk_status_counts = count_by_status(chunk_status_rows)
    converted_chunks = db.query(func.count(FileChunk.id)).filter(
        FileChunk.run_id == run_id,
        FileChunk.converted_code.isnot(None),
        FileChunk.converted_code != "",
    ).scalar() or 0

    technical_total = db.query(func.count(ChunkAnalysis.id)).filter(ChunkAnalysis.run_id == run_id).scalar() or 0
    technical_completed = db.query(func.count(ChunkAnalysis.id)).filter(
        ChunkAnalysis.run_id == run_id,
        ChunkAnalysis.analysis_status == "COMPLETED",
    ).scalar() or 0
    file_analysis_count = db.query(func.count(FileAnalysis.id)).filter(FileAnalysis.run_id == run_id).scalar() or 0

    rule_total = db.query(func.count(BusinessRule.id)).filter(BusinessRule.run_id == run_id).scalar() or 0
    rule_status_rows = db.query(BusinessRule.status, func.count(BusinessRule.id)).filter(
        BusinessRule.run_id == run_id,
    ).group_by(BusinessRule.status).all()
    rule_status_counts = count_by_status(rule_status_rows)
    verified_rules = rule_status_counts.get("VERIFIED", 0)
    pending_rules = rule_status_counts.get("PENDING", 0)
    rejected_rules = rule_status_counts.get("REJECTED", 0)

    environment_status = "Complete" if project else "Pending"
    ingestion_status = status_from_counts(files_total, confirmed_files, files_total)
    discovery_status = status_from_counts(files_total, min(files_total, complexity_files), relations_count + complexity_files)
    analysis_status = status_from_counts(max(chunk_total, confirmed_files), technical_completed, chunk_total + technical_total + file_analysis_count)
    rules_status = status_from_counts(rule_total, verified_rules, rule_total)
    code_status = status_from_counts(chunk_total, converted_chunks, converted_chunks)

    journey = [
        {"id": "select_project", "name": "Select Project", "status": environment_status, "progress": 100 if project else 0, "detail": "Project run is selected." if project else "Create or select a project run."},
        {"id": "upload_source", "name": "Upload Source", "status": ingestion_status, "progress": round((confirmed_files / files_total) * 100) if files_total else 0, "detail": f"{confirmed_files} of {files_total} files confirmed."},
        {"id": "discovery", "name": "Discovery", "status": discovery_status, "progress": round((complexity_files / files_total) * 100) if files_total else 0, "detail": f"{relations_count} relations and {complexity_files} complexity profiles."},
        {"id": "knowledge_extraction", "name": "Knowledge Extraction", "status": rules_status, "progress": round((verified_rules / rule_total) * 100) if rule_total else 0, "detail": f"{verified_rules} verified, {pending_rules} pending, {rejected_rules} rejected rules."},
        {"id": "plan_migration", "name": "Plan Migration", "status": "Complete" if relations_count or rule_total or complexity_files else "Pending", "progress": 100 if relations_count or rule_total or complexity_files else 0, "detail": "Dashboard is backed by live project metrics."},
        {"id": "generate_code", "name": "Generate Code", "status": code_status, "progress": round((converted_chunks / chunk_total) * 100) if chunk_total else 0, "detail": f"{converted_chunks} of {chunk_total} chunks have generated code."},
        {"id": "refinement", "name": "Refinement", "status": "Pending", "progress": 0, "detail": "Compile-test-fix loops start after generated code is available."},
        {"id": "deploy", "name": "Deploy", "status": "Pending", "progress": 0, "detail": "Export is available after generation and refinement."},
    ]

    return {
        "project": serialized_project,
        "files": {
            "total": files_total,
            "confirmed": confirmed_files,
            "pending": pending_files,
            "rejected": rejected_files,
            "status_counts": serialized_project["file_status_counts"],
            "language_counts": serialized_project["language_counts"],
        },
        "discovery": {
            "relations": relations_count,
            "critical_paths": critical_paths,
            "shared_assets": shared_assets,
        },
        "complexity": {
            "files": complexity_files,
            "complex_modules": complex_modules,
            "overall_tier": project_complexity.tier if project_complexity else "Unknown",
            "overall_effort": project_complexity.reasoning_effort if project_complexity else "Balanced",
        },
        "analysis": {
            "chunks": chunk_total,
            "chunk_status_counts": chunk_status_counts,
            "technical_reports": technical_total,
            "technical_completed": technical_completed,
            "file_reports": file_analysis_count,
        },
        "rules": {
            "total": rule_total,
            "verified": verified_rules,
            "pending": pending_rules,
            "rejected": rejected_rules,
            "status_counts": rule_status_counts,
        },
        "code_generation": {
            "converted_chunks": converted_chunks,
            "total_chunks": chunk_total,
        },
        "service_health": get_cached_service_health(run_id, project),
        "journey": journey,
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
@router.get("/{run_id}/config")
async def get_project_config(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_by_run_id(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    mode = project.ai_mode or project.llm_provider or "openrouter"
    return {
        "mode": mode,
        "provider": project.llm_provider or mode,
        "key": "",
        "has_api_key": bool(project.custom_api_key),
        "key_preview": mask_api_key(project.custom_api_key),
        "url": project.custom_api_base_url or ("http://localhost:11434" if mode == "local" else "https://openrouter.ai/api/v1"),
        "model": project.llm_model or ("llama3" if mode == "local" else settings.OPENROUTER_MODEL),
        "local_provider": project.local_provider or ("openai-compatible" if (project.custom_api_base_url or "").rstrip("/").endswith("/v1") else "ollama"),
        "lang": project.interaction_lang,
        "neo4j_uri": project.neo4j_uri or settings.NEO4J_URI or "",
        "neo4j_user": project.neo4j_user or settings.NEO4J_USER or "neo4j",
        "has_neo4j_password": bool(project.neo4j_password or settings.NEO4J_PASSWORD),
        "neo4j_password_preview": mask_secret(project.neo4j_password or settings.NEO4J_PASSWORD),
        "speed_profile": project.speed_profile,
        "reasoning_effort": project.reasoning_effort,
        "workers": project.parallel_workers,
    }


@router.get("/{run_id}/service-health")
async def get_project_service_health(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_by_run_id(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "ai_api": check_ai_api_status(project),
        "neo4j": check_neo4j_status(project),
    }
@router.get("/{run_id}/files")
async def list_project_files(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    if not repo.get_by_run_id(run_id):
        raise HTTPException(status_code=404, detail="Project not found")
    files = repo.get_files_by_run_id(run_id)
    return {"files": [serialize_file(project_file) for project_file in files]}


@router.get("/{run_id}/relations")
async def list_project_relations(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    if not repo.get_by_run_id(run_id):
        raise HTTPException(status_code=404, detail="Project not found")
    graph_refreshed = refresh_dependency_map(run_id, db)
    project = repo.get_by_run_id(run_id)
    neo4j_data = get_neo4j_discovery_data(run_id, project) if graph_refreshed else None
    if neo4j_data is not None:
        return {"relations": neo4j_data["relations"]}

    relations = db.query(FileRelation).filter(FileRelation.run_id == run_id).all()
    return {"relations": [serialize_relation(relation) for relation in relations]}


@router.get("/{run_id}/discovery-data")
async def get_project_discovery_data(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    if not repo.get_by_run_id(run_id):
        raise HTTPException(status_code=404, detail="Project not found")

    graph_refreshed = refresh_dependency_map(run_id, db)
    project = repo.get_by_run_id(run_id)
    neo4j_data = get_neo4j_discovery_data(run_id, project) if graph_refreshed else None
    if neo4j_data is not None:
        return neo4j_data

    files = repo.get_files_by_run_id(run_id)
    relations = db.query(FileRelation).filter(FileRelation.run_id == run_id).all()
    return {
        "files": [serialize_file(project_file) for project_file in files],
        "relations": [serialize_relation(relation) for relation in relations],
    }


@router.patch("/{run_id}/config")
async def update_project_config(run_id: str, updates: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    process = OnboardingProcess(db)
    success = process.update_config(run_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    SERVICE_HEALTH_CACHE.pop(run_id, None)
    background_tasks.add_task(refresh_service_health_cache, run_id)
    return {"status": "Configuration updated", "health_refresh": "queued"}

















