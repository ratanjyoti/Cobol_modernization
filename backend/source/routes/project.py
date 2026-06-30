# Implementation for project.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Processes.onboarding_process import OnboardingProcess
from Persistence.sqlite.project_repo import ProjectRepository
from Persistence.sqlite.session import get_db

router = APIRouter(prefix="/projects", tags=["Projects"])


def serialize_project(project):
    return {
        "run_id": project.run_id,
        "name": project.project_name,
        "status": "Running",
        "created_at": project.created_at.isoformat() if project.created_at else None,
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
    return [serialize_project(project) for project in repo.list_projects()]


@router.post("")
@router.post("/create")
async def create_project(config: dict, db: Session = Depends(get_db)):
    process = OnboardingProcess(db)
    result = process.create_new_project(config, user_id=1)
    return result


@router.get("/{run_id}")
async def get_project(run_id: str, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get_by_run_id(run_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return serialize_project(project)


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
