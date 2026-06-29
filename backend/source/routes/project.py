# Implementation for project.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from Processes.onboarding_process import OnboardingProcess
from Persistence.sqlite.session import get_db # Assume this exists

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("/create")
async def create_project(config: dict, db: Session = Depends(get_db)):
    process = OnboardingProcess(db)
    # In a real app, get user_id from JWT token
    result = process.create_new_project(config, user_id=1) 
    return result

@router.patch("/{run_id}/config")
async def update_project_config(run_id: str, updates: dict, db: Session = Depends(get_db)):
    process = OnboardingProcess(db)
    success = process.update_config(run_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "Configuration updated"}
