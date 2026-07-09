# Implementation for graph_service.py
import os
import re

try:
    from neo4j import GraphDatabase
except ModuleNotFoundError:  # pragma: no cover - depends on deployment environment
    GraphDatabase = None


class GraphService:
    _RELATION_LABELS = {
        "CALLS": "Program",
        "INCLUDES": "Copybook",
        "READS_WRITES": "Table",
        "DEPENDS_ON": "Element",
    }

    def __init__(self):
        if GraphDatabase is None:
            raise RuntimeError(
                "Neo4j Python driver is not installed. Install backend requirements or run: pip install neo4j==5.23.0"
            )

        uri = os.getenv("NEO4J_URI", "neo4j+s://4c42b9ee.databases.neo4j.io")
        user = os.getenv("NEO4J_USER", "4c42b9ee")
        password = os.getenv("NEO4J_PASSWORD", "Q0aeIgwykFSL2Imp0KZWsgTIku-uILzgEoC3MBCz_Dg")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_node(self, name, label, run_id=None, properties=None):
        safe_label = self._safe_cypher_token(label, "Element")
        with self.driver.session() as session:
            if run_id:
                query = f"""
                MERGE (n:DependencyNode:{safe_label} {{run_id: $run_id, name: $name}})
                SET n += $properties
                """
                session.run(query, run_id=run_id, name=name, properties=properties or {})
            else:
                query = f"MERGE (n:{safe_label} {{name: $name}})"
                session.run(query, name=name)

    def create_relationship(self, source_name, target_name, relation_type, run_id=None):
        """
        Creates nodes and a relationship between them.
        Determines the target node label based on the relation_type.
        """
        safe_relation_type = self._safe_cypher_token(relation_type, "DEPENDS_ON")
        target_label = self._RELATION_LABELS.get(safe_relation_type, "Element")

        with self.driver.session() as session:
            if run_id:
                session.execute_write(
                    self._create_run_link_tx,
                    run_id,
                    source_name,
                    target_name,
                    target_label,
                    safe_relation_type,
                )
            else:
                session.execute_write(
                    self._create_link_tx,
                    source_name,
                    target_name,
                    target_label,
                    safe_relation_type,
                )

    def create_project_file(self, run_id, file_record):
        label = self._label_for_file(file_record.filename, file_record.detected_lang)
        self.create_node(
            file_record.filename,
            label,
            run_id=run_id,
            properties={
                "id": str(file_record.id),
                "filename": file_record.filename,
                "filepath": file_record.filepath,
                "detected_lang": file_record.detected_lang,
                "status": file_record.status.value if file_record.status else None,
                "resolved": True,
                "node_kind": "file",
            },
        )

    def create_file_relation(self, run_id, relation):
        relation_type = self._safe_cypher_token(relation.relation_type, "DEPENDS_ON")
        target_label = self._RELATION_LABELS.get(relation_type, "Element")
        self.create_target_node(run_id, relation.target_item, target_label)
        self.create_relationship(
            relation.source_file,
            relation.target_item,
            relation_type,
            run_id=run_id,
        )

    def create_target_node(self, run_id, target_name, label):
        safe_label = self._safe_cypher_token(label, "Element")
        with self.driver.session() as session:
            query = f"""
            MERGE (n:DependencyNode:{safe_label} {{run_id: $run_id, name: $name}})
            ON CREATE SET n.filename = $name,
                          n.filepath = null,
                          n.detected_lang = $detected_lang,
                          n.status = null,
                          n.resolved = false,
                          n.node_kind = 'target'
            """
            session.run(query, run_id=run_id, name=target_name, detected_lang=safe_label.lower())

    def clear_run(self, run_id):
        with self.driver.session() as session:
            session.run("MATCH (n:DependencyNode {run_id: $run_id}) DETACH DELETE n", run_id=run_id)

    def get_discovery_data(self, run_id):
        with self.driver.session() as session:
            files = session.run(
                """
                MATCH (n:DependencyNode {run_id: $run_id, node_kind: 'file'})
                RETURN n.id AS id,
                       n.filename AS filename,
                       n.filepath AS filepath,
                       n.detected_lang AS detected_lang,
                       n.status AS status
                ORDER BY filename
                """,
                run_id=run_id,
            )
            relations = session.run(
                """
                MATCH (source:DependencyNode {run_id: $run_id})-[rel]->(target:DependencyNode {run_id: $run_id})
                RETURN elementId(rel) AS id,
                       source.name AS source_file,
                       target.name AS target_item,
                       type(rel) AS relation_type
                ORDER BY source_file, relation_type, target_item
                """,
                run_id=run_id,
            )
            return {
                "files": [
                    {
                        "id": record["id"],
                        "filename": record["filename"],
                        "filepath": record["filepath"],
                        "detected_lang": record["detected_lang"],
                        "status": record["status"],
                        "size": 0,
                    }
                    for record in files
                ],
                "relations": [
                    {
                        "id": str(record["id"]),
                        "source_file": record["source_file"],
                        "target_item": record["target_item"],
                        "relation_type": record["relation_type"],
                    }
                    for record in relations
                ],
            }
    def create_semantic_relation(self, source_name, target_name, relation_type):
        """
        Implements specific edges based on the detected relation type.
        """
        # Determine the Label for the target node
        label_map = {
            "CALLS": "Program",
            "MAPS_TO": "Program",
            "INCLUDES": "Copybook",
            "READS": "Table",
            "WRITES": "Table"
        }
        target_label = label_map.get(relation_type, "Element")

        with self.driver.session() as session:
            # 1. Create/Merge Nodes
            session.run(f"MERGE (s:Program {{name: $source}})", source=source_name)
            session.run(f"MERGE (t:{target_label} {{name: $target}})", target=target_name)

            # 2. Create the specific semantic relationship
            # Example: (p:Program)-[:READS]->(t:Table)
            query = f"MATCH (a:Program {{name: $source}}), (b:{target_label} {{name: $target}}) MERGE (a)-[:{relation_type}]->(b)"
            session.run(query, source=source_name, target=target_name)
    def get_graph(self, run_id):
        discovery_data = self.get_discovery_data(run_id)
        nodes_by_id = {}

        for file in discovery_data["files"]:
            nodes_by_id[file["filename"]] = {
                "id": file["filename"],
                "label": file["filename"],
                "type": file["detected_lang"] or "file",
                "filepath": file["filepath"],
                "resolved": True,
            }

        edges = []
        for relation in discovery_data["relations"]:
            target_id = relation["target_item"]
            if target_id not in nodes_by_id:
                nodes_by_id[target_id] = {
                    "id": target_id,
                    "label": target_id,
                    "type": relation["relation_type"],
                    "filepath": None,
                    "resolved": False,
                }
            edges.append({
                "from": relation["source_file"],
                "to": target_id,
                "type": relation["relation_type"],
            })

        return {"nodes": list(nodes_by_id.values()), "edges": edges}

    @staticmethod
    def _safe_cypher_token(value, fallback):
        token = re.sub(r"\W+", "_", str(value or "").upper()).strip("_")
        if not token or token[0].isdigit():
            return fallback
        return token

    @staticmethod
    def _create_link_tx(tx, source_name, target_name, target_label, relation_type):
        # Labels and relationship types cannot be parameterized in Cypher, so callers sanitize them first.
        query = (
            f"MERGE (s:Program {{name: $source}}) "
            f"MERGE (t:{target_label} {{name: $target}}) "
            f"MERGE (s)-[:{relation_type}]->(t)"
        )
        tx.run(query, source=source_name, target=target_name)

    @staticmethod
    def _create_run_link_tx(tx, run_id, source_name, target_name, target_label, relation_type):
        query = (
            "MERGE (s:DependencyNode:Program {run_id: $run_id, name: $source}) "
            f"MERGE (t:DependencyNode:{target_label} {{run_id: $run_id, name: $target}}) "
            f"MERGE (s)-[r:{relation_type}]->(t) "
            "SET r.run_id = $run_id"
        )
        tx.run(query, run_id=run_id, source=source_name, target=target_name)

    @staticmethod
    def _label_for_file(filename, detected_lang):
        lang = (detected_lang or "").lower()
        name = (filename or "").lower()
        if "jcl" in lang or name.endswith(".jcl"):
            return "Job"
        if "copy" in lang or name.endswith(".cpy"):
            return "Copybook"
        if "cobol" in lang or name.endswith((".cbl", ".cob")):
            return "Program"
        if name.endswith(".sql"):
            return "Table"
        return "File"

    def get_impacted_programs(self, item_name):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (p:Program)-[:INCLUDES|CALLS|READS_WRITES]->(item {name: $name}) RETURN p.name as name",
                name=item_name,
            )
            return [record["name"] for record in result]
