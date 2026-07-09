import os
import re

try:
    from neo4j import GraphDatabase
except ModuleNotFoundError:  # pragma: no cover
    GraphDatabase = None


class GraphService:
    def __init__(self):
        if GraphDatabase is None:
            raise RuntimeError("Neo4j Python driver is not installed")

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_run(self, run_id):
        with self.driver.session() as session:
            session.run("MATCH (n:DependencyNode {run_id: $run_id}) DETACH DELETE n", run_id=run_id)

    def create_project_file(self, run_id, file_record):
        label = self._label_for_file(file_record.filename, file_record.detected_lang)
        safe_label = self._safe_cypher_token(label, "File")
        with self.driver.session() as session:
            query = f"""
            MERGE (n:DependencyNode:{safe_label} {{run_id: $run_id, name: $name}})
            SET n.id = $id,
                n.filename = $filename,
                n.filepath = $filepath,
                n.detected_lang = $detected_lang,
                n.status = $status,
                n.resolved = true,
                n.node_kind = 'file'
            """
            session.run(
                query,
                run_id=run_id,
                name=file_record.filepath or file_record.filename,
                id=str(file_record.id),
                filename=file_record.filename,
                filepath=file_record.filepath,
                detected_lang=file_record.detected_lang,
                status=file_record.status.value if file_record.status else None,
            )

    def create_project_node(self, run_id, filename, lang):
        class ProjectNodeRecord:
            pass

        record = ProjectNodeRecord()
        record.id = filename
        record.filename = filename
        record.filepath = filename
        record.detected_lang = lang
        record.status = None
        self.create_project_file(run_id, record)

    def create_file_relation(self, run_id, relation):
        self.create_semantic_relation(
            run_id,
            relation.source_file,
            relation.target_item,
            relation.relation_type,
        )

    def create_semantic_relation(self, run_id, source, target, rel_type):
        safe_rel = self._safe_cypher_token(rel_type, "DEPENDS_ON")
        with self.driver.session() as session:
            query = f"""
            MATCH (s:DependencyNode {{run_id: $run_id, name: $source}})
            MATCH (t:DependencyNode {{run_id: $run_id, name: $target}})
            WHERE s.node_kind = 'file' AND t.node_kind = 'file'
            MERGE (s)-[r:{safe_rel}]->(t)
            SET r.run_id = $run_id
            """
            session.run(query, run_id=run_id, source=source, target=target)

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
                MATCH (source:DependencyNode {run_id: $run_id, node_kind: 'file'})-[rel]->(target:DependencyNode {run_id: $run_id, node_kind: 'file'})
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
                        "id": str(record["id"]),
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

    def get_graph(self, run_id):
        discovery_data = self.get_discovery_data(run_id)
        nodes_by_id = {}
        for file in discovery_data["files"]:
            node_id = file["filepath"] or file["filename"]
            nodes_by_id[node_id] = {
                "id": node_id,
                "label": file["filename"],
                "type": file["detected_lang"] or "file",
                "filepath": file["filepath"],
                "resolved": True,
            }

        edges = []
        for relation in discovery_data["relations"]:
            if relation["source_file"] not in nodes_by_id or relation["target_item"] not in nodes_by_id:
                continue
            edges.append({
                "from": relation["source_file"],
                "to": relation["target_item"],
                "type": relation["relation_type"],
            })

        return {"nodes": list(nodes_by_id.values()), "edges": edges}

    def get_impacted_programs(self, item_name):
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (p:DependencyNode)-[:CALLS|INCLUDES|ACCESSES|READS|WRITES|EXECUTES|MAPS_TO]->(item:DependencyNode)
                WHERE item.name = $name AND (p:Program OR p:Job OR p:TelonModule)
                RETURN DISTINCT p.name AS name
                ORDER BY name
                """,
                name=item_name,
            )
            return [record["name"] for record in result]

    @staticmethod
    def _safe_cypher_token(value, fallback):
        token = re.sub(r"\W+", "_", str(value or "").upper()).strip("_")
        if not token or token[0].isdigit():
            return fallback
        return token

    @staticmethod
    def _label_for_file(filename, detected_lang):
        lang = (detected_lang or "").lower()
        name = (filename or "").lower()
        if "jcl" in lang or name.endswith(".jcl"):
            return "Job"
        if "telon" in lang or name.endswith((".tln", ".tel")):
            return "TelonModule"
        if "copy" in lang or name.endswith(".cpy"):
            return "Copybook"
        if "cobol" in lang or name.endswith((".cbl", ".cob")):
            return "Program"
        if name.endswith((".sql", ".ddl")):
            return "Table"
        return "File"



