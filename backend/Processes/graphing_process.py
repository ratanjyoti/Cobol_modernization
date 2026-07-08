from Persistence.neo4j.graph_service import GraphService
from Persistence.sqlite.models import FileRelation, ProjectFile


class GraphingProcess:
    def __init__(self, db_session):
        self.db = db_session
        self.graph_service = GraphService()

    def build_full_graph(self, run_id: str):
        files = self.db.query(ProjectFile).filter(
            ProjectFile.run_id == run_id
        ).all()
        relations = self.db.query(FileRelation).filter(
            FileRelation.run_id == run_id
        ).all()

        self.graph_service.clear_run(run_id)

        for file_record in files:
            self.graph_service.create_project_file(run_id, file_record)

        for relation in relations:
            self.graph_service.create_file_relation(run_id, relation)

        self.graph_service.close()
        return True
