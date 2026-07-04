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

        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_node(self, name, label):
        safe_label = self._safe_cypher_token(label, "Element")
        with self.driver.session() as session:
            query = f"MERGE (n:{safe_label} {{name: $name}})"
            session.run(query, name=name)

    def create_relationship(self, source_name, target_name, relation_type):
        """
        Creates nodes and a relationship between them.
        Determines the target node label based on the relation_type.
        """
        safe_relation_type = self._safe_cypher_token(relation_type, "DEPENDS_ON")
        target_label = self._RELATION_LABELS.get(safe_relation_type, "Element")

        with self.driver.session() as session:
            session.execute_write(
                self._create_link_tx,
                source_name,
                target_name,
                target_label,
                safe_relation_type,
            )

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

    def get_impacted_programs(self, item_name):
        with self.driver.session() as session:
            result = session.run(
                "MATCH (p:Program)-[:INCLUDES|CALLS|READS_WRITES]->(item {name: $name}) RETURN p.name as name",
                name=item_name,
            )
            return [record["name"] for record in result]

