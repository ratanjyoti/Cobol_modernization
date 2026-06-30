# Implementation for project.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import os
import shutil
import stat
from Processes.onboarding_process import OnboardingProcess
from Persistence.sqlite.project_repo import ProjectRepository
from Persistence.sqlite.session import get_db

router = APIRouter(prefix="/projects", tags=["Projects"])


def remove_tree_sync(path: Path):
    def handle_remove_error(func, failed_path, _exc_info):
        os.chmod(failed_path, stat.S_IWRITE)
        func(failed_path)

    if path.exists():
        shutil.rmtree(path, onerror=handle_remove_error)


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


@router.get("")
async def list_projects(db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    return [serialize_project(project, repo.get_files_by_run_id(project.run_id)) for project in repo.list_projects()]


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
    clear_uploads_sync(Path("data/uploads"))
    return {"status": "Success", **result}


@router.delete("/{run_id}")
async def delete_run(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    if not repo.get_by_run_id(run_id):
        raise HTTPException(status_code=404, detail="Project not found")

    result = repo.delete_project(run_id)
    remove_tree_sync(Path("data/uploads") / run_id)
    return {"status": "Success", **result}


@router.delete("/{run_id}/files")
async def clear_project_files(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    if not repo.get_by_run_id(run_id):
        raise HTTPException(status_code=404, detail="Project not found")

    deleted_count = repo.delete_files_by_run_id(run_id)
    remove_tree_sync(Path("data/uploads") / run_id)
    return {"status": "Success", "files_deleted": deleted_count}


@router.get("/{run_id}")
async def get_project(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_by_run_id(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return serialize_project(project, repo.get_files_by_run_id(run_id))


@router.get("/{run_id}/files")
async def list_project_files(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    if not repo.get_by_run_id(run_id):
        raise HTTPException(status_code=404, detail="Project not found")
    files = repo.get_files_by_run_id(run_id)
    return {"files": [serialize_file(project_file) for project_file in files]}


@router.patch("/{run_id}/config")
async def update_project_config(run_id: str, updates: dict, db: Session = Depends(get_db)):
    process = OnboardingProcess(db)
    success = process.update_config(run_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "Configuration updated"}
