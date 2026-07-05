# Implementation for project_repo.py
from sqlalchemy.orm import Session
from Persistence.sqlite.models import FileChunk, FileComplexity, FileRelation, Project, ProjectComplexity, ProjectFile


class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, project: Project):
        """Saves a new project to the database."""
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def list_projects(self):
        """Fetches all projects, newest first."""
        return self.session.query(Project).order_by(Project.created_at.desc()).all()

    def get_by_run_id(self, run_id: str):
        """Fetches a project by its run_id."""
        return self.session.query(Project).filter(Project.run_id == run_id).first()

    def update_project(self, run_id: str, updates: dict):
        """Updates project configuration fields dynamically."""
        project = self.get_by_run_id(run_id)
        if project:
            for key, value in updates.items():
                if hasattr(project, key):
                    setattr(project, key, value)
            self.session.commit()
            return True
        return False

    def get_files_by_run_id(self, run_id: str):
        """Fetches all files associated with a specific run_id."""
        return self.session.query(ProjectFile).filter(ProjectFile.run_id == run_id).all()

    def count_files_by_run_id(self, run_id: str):
        """Counts all files associated with a specific run_id."""
        return self.session.query(ProjectFile).filter(ProjectFile.run_id == run_id).count()

    def save_file(self, project_file: ProjectFile):
        """Saves a detected file to the project_files table."""
        self.session.add(project_file)
        self.session.commit()
        self.session.refresh(project_file)
        return project_file

    def delete_files_by_run_id(self, run_id: str):
        """Deletes all file, chunk, relation, and complexity records for a project."""
        self.session.query(FileChunk).filter(FileChunk.run_id == run_id).delete(synchronize_session=False)
        self.session.query(FileRelation).filter(FileRelation.run_id == run_id).delete(synchronize_session=False)
        self.session.query(FileComplexity).filter(FileComplexity.run_id == run_id).delete(synchronize_session=False)
        self.session.query(ProjectComplexity).filter(ProjectComplexity.run_id == run_id).delete(synchronize_session=False)
        count = self.session.query(ProjectFile).filter(ProjectFile.run_id == run_id).delete(synchronize_session=False)
        self.session.commit()
        return count

    def delete_project(self, run_id: str):
        """Deletes one project and all data records owned by the run."""
        self.session.query(FileChunk).filter(FileChunk.run_id == run_id).delete(synchronize_session=False)
        self.session.query(FileRelation).filter(FileRelation.run_id == run_id).delete(synchronize_session=False)
        self.session.query(FileComplexity).filter(FileComplexity.run_id == run_id).delete(synchronize_session=False)
        self.session.query(ProjectComplexity).filter(ProjectComplexity.run_id == run_id).delete(synchronize_session=False)
        file_count = self.session.query(ProjectFile).filter(ProjectFile.run_id == run_id).delete(synchronize_session=False)
        project_count = self.session.query(Project).filter(Project.run_id == run_id).delete(synchronize_session=False)
        self.session.commit()
        return {"projects_deleted": project_count, "files_deleted": file_count}

    def delete_all_projects(self):
        """Deletes all projects and run-owned data records."""
        self.session.query(FileChunk).delete(synchronize_session=False)
        self.session.query(FileRelation).delete(synchronize_session=False)
        self.session.query(FileComplexity).delete(synchronize_session=False)
        self.session.query(ProjectComplexity).delete(synchronize_session=False)
        file_count = self.session.query(ProjectFile).delete(synchronize_session=False)
        project_count = self.session.query(Project).delete(synchronize_session=False)
        self.session.commit()
        return {"projects_deleted": project_count, "files_deleted": file_count}

