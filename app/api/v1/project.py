from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from app.models.project import ProjectConfig
from app.database.sqlite_db import db
from app.core.security import decode_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Mapping Speed Profile to System Parameters
SPEED_PROFILES = {
    "Turbo": {"workers": 20, "effort": "Low", "overlap": 100},
    "Fast": {"workers": 10, "effort": "Medium", "overlap": 200},
    "Balanced": {"workers": 5, "effort": "Medium", "overlap": 300},
    "Thorough": {"workers": 2, "effort": "High", "overlap": 500},
}

@router.post("/setup")
async def setup_project(config: ProjectConfig, token: str = Depends(oauth2_scheme)):
    # 1. Validate User
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("user_id")

    # 2. Apply Speed Profile Logic
    profile_settings = SPEED_PROFILES.get(config.speed_profile, SPEED_PROFILES["Balanced"])
    
    # Override workers if the user provided a custom number, else use profile default
    final_workers = config.parallel_workers if config.parallel_workers else profile_settings["workers"]
    final_effort = config.reasoning_effort if config.reasoning_effort else profile_settings["effort"]

    # 3. Prepare data for SQLite
    project_data = {
        "user_id": user_id,
        "llm_provider": config.llm_provider,
        "interaction_lang": config.interaction_lang,
        "speed_profile": config.speed_profile,
        "reasoning_effort": final_effort,
        "parallel_workers": final_workers
    }

    # 4. Create project and get the Golden run_id
    run_id = db.create_project(project_data)

    return {
        "run_id": run_id,
        "config": {
            "parallel_workers": final_workers,
            "reasoning_effort": final_effort,
            "llm_provider": config.llm_provider,
            "interaction_lang": config.interaction_lang
        },
        "message": "Project initialized successfully. Use this run_id for all subsequent calls."
    }
