# Implementation for project_repo.py
from sqlalchemy.orm import Session
from Persistence.sqlite.models import FileChunk, FileComplexity, FileRelation, Project, ProjectComplexity, ProjectFile


class ProjectRepository:
    CONFIG_FIELD_MAP = {
        "mode": "ai_mode",
        "provider": "llm_provider",
        "key": "custom_api_key",
        "url": "custom_api_base_url",
        "model": "llm_model",
        "lang": "interaction_lang",
        "workers": "parallel_workers",
    }

    def __init__(self, session: Session):
        self.session = session

    def save(self, project: Project):
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def list_projects(self):
        return self.session.query(Project).order_by(Project.created_at.desc()).all()

    def get_by_run_id(self, run_id: str):
        return self.session.query(Project).filter(Project.run_id == run_id).first()

    def update_project(self, run_id: str, updates: dict):
        project = self.get_by_run_id(run_id)
        if not project:
            return False

        for key, value in updates.items():
            attr = self.CONFIG_FIELD_MAP.get(key, key)
            if hasattr(project, attr):
                setattr(project, attr, value)

        if updates.get("mode"):
            project.llm_provider = updates["mode"]
        if updates.get("model"):
            project.llm_model = updates["model"]

        self.session.commit()
        return True

    def get_files_by_run_id(self, run_id: str):
        return self.session.query(ProjectFile).filter(ProjectFile.run_id == run_id).all()

    def count_files_by_run_id(self, run_id: str):
        return self.session.query(ProjectFile).filter(ProjectFile.run_id == run_id).count()

    def save_file(self, project_file: ProjectFile):
        self.session.add(project_file)
        self.session.commit()
        self.session.refresh(project_file)
        return project_file

    def delete_files_by_run_id(self, run_id: str):
        self.session.query(FileChunk).filter(FileChunk.run_id == run_id).delete(synchronize_session=False)
        self.session.query(FileRelation).filter(FileRelation.run_id == run_id).delete(synchronize_session=False)
        self.session.query(FileComplexity).filter(FileComplexity.run_id == run_id).delete(synchronize_session=False)
        self.session.query(ProjectComplexity).filter(ProjectComplexity.run_id == run_id).delete(synchronize_session=False)
        count = self.session.query(ProjectFile).filter(ProjectFile.run_id == run_id).delete(synchronize_session=False)
        self.session.commit()
        return count

    def delete_project(self, run_id: str):
        self.session.query(FileChunk).filter(FileChunk.run_id == run_id).delete(synchronize_session=False)
        self.session.query(FileRelation).filter(FileRelation.run_id == run_id).delete(synchronize_session=False)
        self.session.query(FileComplexity).filter(FileComplexity.run_id == run_id).delete(synchronize_session=False)
        self.session.query(ProjectComplexity).filter(ProjectComplexity.run_id == run_id).delete(synchronize_session=False)
        file_count = self.session.query(ProjectFile).filter(ProjectFile.run_id == run_id).delete(synchronize_session=False)
        project_count = self.session.query(Project).filter(Project.run_id == run_id).delete(synchronize_session=False)
        self.session.commit()
        return {"projects_deleted": project_count, "files_deleted": file_count}

    def delete_all_projects(self):
        self.session.query(FileChunk).delete(synchronize_session=False)
        self.session.query(FileRelation).delete(synchronize_session=False)
        self.session.query(FileComplexity).delete(synchronize_session=False)
        self.session.query(ProjectComplexity).delete(synchronize_session=False)
        file_count = self.session.query(ProjectFile).delete(synchronize_session=False)
        project_count = self.session.query(Project).delete(synchronize_session=False)
        self.session.commit()
        return {"projects_deleted": project_count, "files_deleted": file_count}
