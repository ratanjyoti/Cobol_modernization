# Implementation for project.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from pathlib import Path
import os
import shutil
import stat
import requests
from Processes.graphing_process import GraphingProcess
from Processes.onboarding_process import OnboardingProcess
from Persistence.neo4j.graph_service import GraphService
from Chunking.dependency_scanner.resolution_service import ResolutionService
from Config.llm_config import settings
from Persistence.sqlite.models import FileRelation, ProjectFile
from Persistence.sqlite.project_repo import ProjectRepository
from Persistence.sqlite.session import get_db
from paths import UPLOADS_DIR

router = APIRouter(prefix="/projects", tags=["Projects"])


def mask_api_key(api_key: str | None):
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:5]}****{api_key[-4:]}"


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

def get_neo4j_discovery_data(run_id: str):
    graph_service = None
    try:
        graph_service = GraphService()
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
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=8)
            response.raise_for_status()
            return {
                "active": True,
                "provider": "local",
                "model": model,
                "detail": "Local model server responded.",
            }
        except Exception as exc:
            return {
                "active": False,
                "provider": "local",
                "model": model,
                "detail": str(exc)[:180],
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


def check_neo4j_status():
    graph_service = None
    try:
        graph_service = GraphService()
        graph_service.driver.verify_connectivity()
        return {"active": True, "detail": "Neo4j connection verified."}
    except Exception as exc:
        return {"active": False, "detail": str(exc)[:180]}
    finally:
        if graph_service is not None:
            graph_service.close()
def clear_neo4j_run(run_id: str):
    graph_service = None
    try:
        graph_service = GraphService()
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
async def create_project(config: dict, db: Session = Depends(get_db)):
    process = OnboardingProcess(db)
    result = process.create_new_project(config, user_id=1)
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
    if not repo.get_by_run_id(run_id):
        raise HTTPException(status_code=404, detail="Project not found")

    result = repo.delete_project(run_id)
    clear_neo4j_run(run_id)
    remove_tree_sync(UPLOADS_DIR / run_id)
    return {"status": "Success", **result}


@router.delete("/{run_id}/files")
async def clear_project_files(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    if not repo.get_by_run_id(run_id):
        raise HTTPException(status_code=404, detail="Project not found")

    deleted_count = repo.delete_files_by_run_id(run_id)
    clear_neo4j_run(run_id)
    remove_tree_sync(UPLOADS_DIR / run_id)
    return {"status": "Success", "files_deleted": deleted_count}


@router.get("/{run_id}")
async def get_project(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_by_run_id(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return serialize_project(project, repo.get_files_by_run_id(run_id))



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
        "lang": project.interaction_lang,
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
        "neo4j": check_neo4j_status(),
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
    neo4j_data = get_neo4j_discovery_data(run_id) if graph_refreshed else None
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
    neo4j_data = get_neo4j_discovery_data(run_id) if graph_refreshed else None
    if neo4j_data is not None:
        return neo4j_data

    files = repo.get_files_by_run_id(run_id)
    relations = db.query(FileRelation).filter(FileRelation.run_id == run_id).all()
    return {
        "files": [serialize_file(project_file) for project_file in files],
        "relations": [serialize_relation(relation) for relation in relations],
    }


@router.patch("/{run_id}/config")
async def update_project_config(run_id: str, updates: dict, db: Session = Depends(get_db)):
    process = OnboardingProcess(db)
    success = process.update_config(run_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "Configuration updated"}









