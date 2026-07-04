from Persistence.neo4j.graph_service import GraphService
from Persistence.sqlite.models import FileRelation

class GraphingProcess:
    def __init__(self, db_session):
        self.db = db_session
        self.graph_service = GraphService()

    def build_full_graph(self, run_id: str):
        # 1. Fetch all relations from SQLite
        relations = self.db.query(FileRelation).filter(
            FileRelation.run_id == run_id
        ).all()

        # To avoid redundant calls, keep track of created nodes
        created_nodes = set()

        for rel in relations:
            # A. Create Source Node (Always a Program)
            if rel.source_file not in created_nodes:
                self.graph_service.create_node(rel.source_file, "Program")
                created_nodes.add(rel.source_file)

            # B. Create Target Node (Based on relation type)
            label_map = {"CALLS": "Program", "INCLUDES": "Copybook", "READS_WRITES": "Table"}
            target_label = label_map.get(rel.relation_type, "Element")
            
            # We don't use a set for targets because target names might overlap 
            # across different labels, but MERGE handles it anyway.
            self.graph_service.create_node(rel.target_item, target_label)

            # C. Create the Relationship (MATCH a, b MERGE a->b)
            self.graph_service.create_relationship(
                rel.source_file, 
                rel.target_item, 
                rel.relation_type
            )

        self.graph_service.close()
        return True
