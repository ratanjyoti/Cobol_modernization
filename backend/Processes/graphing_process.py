from Chunking.dependency_scanner.resolution_service import ResolutionService
from Persistence.neo4j.graph_service import GraphService
from Persistence.sqlite.models import FileRelation, Project, ProjectFile


class GraphingProcess:
    def __init__(self, db_session):
        self.db = db_session

    def build_full_graph(self, run_id: str):
        ResolutionService(self.db).resolve_run_relations(run_id)
        self.db.commit()

        graph_service = None
        try:
            project = self.db.query(Project).filter(Project.run_id == run_id).first()
            graph_service = GraphService.for_project(project)
        except Exception as exc:
            print(f"Neo4j graph build skipped for {run_id}: {exc}")
            return False

        try:
            files = self.db.query(ProjectFile).filter(ProjectFile.run_id == run_id).all()
            valid_names = {file_record.filepath or file_record.filename for file_record in files}
            relations = self.db.query(FileRelation).filter(FileRelation.run_id == run_id).all()
            relations = [
                relation for relation in relations
                if relation.source_file in valid_names and relation.target_item in valid_names
            ]

            graph_service.clear_run(run_id)

            for file_record in files:
                graph_service.create_project_file(run_id, file_record)

            for relation in relations:
                graph_service.create_file_relation(run_id, relation)

            return True
        finally:
            if graph_service is not None:
                graph_service.close()
