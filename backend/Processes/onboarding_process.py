# Implementation for onboarding_process.py
import uuid
from Persistence.sqlite.models import Project
from Persistence.sqlite.project_repo import ProjectRepository


class OnboardingProcess:
    def __init__(self, db_session):
        self.repo = ProjectRepository(db_session)

    def _next_run_name(self):
        used_numbers = []
        for project in self.repo.list_projects():
            name = project.project_name or ""
            if name.startswith("Run_") and name[4:].isdigit():
                used_numbers.append(int(name[4:]))
        next_number = max(used_numbers) + 1 if used_numbers else len(self.repo.list_projects()) + 1
        return f"Run_{next_number}"

    def create_new_project(self, config_data: dict, user_id: int):
        run_id = f"RUN_{uuid.uuid4().hex[:8].upper()}"
        project_name = config_data.get("project_name") or self._next_run_name()

        new_project = Project(
            run_id=run_id,
            user_id=user_id,
            project_name=project_name,
            llm_provider=config_data.get("provider") or config_data.get("mode"),
            ai_mode=config_data.get("mode") or config_data.get("provider"),
            custom_api_key=config_data.get("key") or config_data.get("custom_api_key"),
            custom_api_base_url=config_data.get("url") or config_data.get("custom_api_base_url"),
            llm_model=config_data.get("model"),
            interaction_lang=config_data.get("lang", "en"),
            speed_profile=config_data.get("speed_profile", "Balanced"),
            reasoning_effort=config_data.get("reasoning_effort", "Medium"),
            parallel_workers=int(config_data.get("workers", 4))
        )

        self.repo.save(new_project)
        return {"run_id": run_id, "name": project_name, "status": "Project Initialized"}

    def update_config(self, run_id: str, updates: dict):
        return self.repo.update_project(run_id, updates)
