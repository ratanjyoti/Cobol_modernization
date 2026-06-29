# Implementation for onboarding_process.py
import uuid
from Persistence.sqlite.models import Project
from Persistence.sqlite.project_repo import ProjectRepository

class OnboardingProcess:
    def __init__(self, db_session):
        self.repo = ProjectRepository(db_session)

    def create_new_project(self, config_data: dict, user_id: int):
        # 1. Generate a unique run_id
        run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
        
        # 2. Create Project Object
        new_project = Project(
            run_id=run_id,
            user_id=user_id,
            project_name=config_data.get("project_name", "Unnamed Project"),
            llm_provider=config_data.get("provider"),
            llm_model=config_data.get("model"),
            interaction_lang=config_data.get("lang", "en"),
            speed_profile=config_data.get("speed_profile", "Balanced"),
            reasoning_effort=config_data.get("reasoning_effort", "Medium"),
            parallel_workers=int(config_data.get("workers", 4))
        )
        
        self.repo.save(new_project)
        return {"run_id": run_id, "status": "Project Initialized"}

    def update_config(self, run_id: str, updates: dict):
        return self.repo.update_project(run_id, updates)
