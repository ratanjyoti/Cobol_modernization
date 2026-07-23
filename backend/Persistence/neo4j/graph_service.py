import os
import re
from pathlib import Path
from typing import Any

try:
    from neo4j import GraphDatabase
except ModuleNotFoundError:  # pragma: no cover
    GraphDatabase = None


class GraphService:
    """
    Neo4j graph service for dependency discovery.

    Main improvements:
    1. Uses canonical aliases so filepath/filename/basename/stem can all resolve to the same node.
    2. Preserves unresolved targets instead of silently dropping missing relations.
    3. Normalizes relation names for the frontend:
       CALLS, INCLUDES, ACCESSES, READS, WRITES, READS_WRITES, EXECUTES, MAPS_TO, UNRESOLVED.
    4. Returns external/unresolved nodes so the frontend unresolved view works.
    """

    RELATION_ALIASES = {
        "CALL": "CALLS",
        "CALLS": "CALLS",

        "COPY": "INCLUDES",
        "INCLUDE": "INCLUDES",
        "INCLUDES": "INCLUDES",
        "IMPORT": "IMPORTS",
        "IMPORTS": "IMPORTS",

        "EXEC SQL": "ACCESSES",
        "SQL": "ACCESSES",
        "ACCESSES": "ACCESSES",

        "READ": "READS",
        "READS": "READS",

        "WRITE": "WRITES",
        "WRITES": "WRITES",
        "REWRITE": "WRITES",
        "DELETE": "WRITES",

        "READS_WRITES": "READS_WRITES",
        "READ_WRITE": "READS_WRITES",

        "EXEC CICS": "EXECUTES",
        "EXECUTES": "EXECUTES",
        "JCL_EXEC": "EXECUTES",

        "MAPS_TO": "MAPS_TO",
        "TELON_MAP": "MAPS_TO",

        "REFERENCE": "REFERENCES",
        "REFERENCES": "REFERENCES",

        "INHERIT": "INHERITS",
        "INHERITS": "INHERITS",

        "UNRESOLVED": "UNRESOLVED",
    }

    def __init__(self, uri=None, user=None, password=None):
        if GraphDatabase is None:
            raise RuntimeError("Neo4j Python driver is not installed")

        uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = user or os.getenv("NEO4J_USER", "neo4j")
        password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    @classmethod
    def for_project(cls, project=None):
        return cls(
            uri=getattr(project, "neo4j_uri", None),
            user=getattr(project, "neo4j_user", None),
            password=getattr(project, "neo4j_password", None),
        )

    def close(self):
        self.driver.close()

    def clear_run(self, run_id):
        with self.driver.session() as session:
            session.run(
                "MATCH (n:DependencyNode {run_id: $run_id}) DETACH DELETE n",
                run_id=run_id,
            )

    def create_project_file(self, run_id, file_record):
        """
        Creates or upgrades a resolved uploaded file node.

        Important:
        name = filepath if available, else filename.
        aliases contain filepath, filename, basename, and stem so later relations can resolve.
        """
        filename = file_record.filename or ""
        filepath = file_record.filepath or filename
        detected_lang = file_record.detected_lang or ""

        name = self._node_key(filepath=filepath, filename=filename)
        label = self._label_for_file(filename, detected_lang)
        safe_label = self._safe_cypher_token(label, "File")
        node_type = self._frontend_type_for_label(label)

        aliases = self._aliases_for_file(filename=filename, filepath=filepath)
        alias_lc = self._lower_aliases(aliases)

        with self.driver.session() as session:
            query = f"""
            MERGE (n:DependencyNode {{run_id: $run_id, name: $name}})
            REMOVE n:External
            SET n:{safe_label}
            SET n.id = $id,
                n.filename = $filename,
                n.filepath = $filepath,
                n.display_label = $filename,
                n.detected_lang = $detected_lang,
                n.status = $status,
                n.resolved = true,
                n.node_kind = 'file',
                n.node_type = $node_type,
                n.aliases = $aliases,
                n.alias_lc = $alias_lc
            """
            session.run(
                query,
                run_id=run_id,
                name=name,
                id=str(file_record.id),
                filename=filename,
                filepath=filepath,
                detected_lang=detected_lang,
                status=file_record.status.value if file_record.status else None,
                node_type=node_type,
                aliases=aliases,
                alias_lc=alias_lc,
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
            run_id=run_id,
            source=relation.source_file,
            target=relation.target_item,
            rel_type=relation.relation_type,
            context=getattr(relation, "context", "") or "",
            line_number=getattr(relation, "line_number", None),
        )

    def create_semantic_relation(
        self,
        run_id,
        source,
        target,
        rel_type,
        context: str = "",
        line_number: int | None = None,
    ):
        """
        Creates a graph relationship.

        If target is not uploaded/resolved, create an unresolved External node and
        connect using UNRESOLVED relation type. This prevents missing CALL/COPY/SQL
        targets from disappearing from the graph.
        """
        source = self._normalize_name(source)
        target = self._normalize_name(target)

        if not source or not target:
            return

        original_rel = self._normalize_relation_type(rel_type)
        source_node = self._find_node(run_id, source)

        if source_node is None:
            source_node = self._create_external_node(
                run_id=run_id,
                name=source,
                inferred_type="external",
                reason="Relation source was not found in uploaded files",
            )

        target_node = self._find_node(run_id, target)

        target_is_resolved = target_node is not None and bool(target_node.get("resolved"))

        if target_node is None:
            inferred_type = self._infer_external_type(target, original_rel)
            target_node = self._create_external_node(
                run_id=run_id,
                name=target,
                inferred_type=inferred_type,
                reason=f"Referenced by {source}",
            )

        final_rel = original_rel if target_is_resolved else "UNRESOLVED"
        safe_rel = self._safe_cypher_token(final_rel, "DEPENDS_ON")

        with self.driver.session() as session:
            query = f"""
            MATCH (s:DependencyNode {{run_id: $run_id, name: $source_name}})
            MATCH (t:DependencyNode {{run_id: $run_id, name: $target_name}})
            MERGE (s)-[r:{safe_rel}]->(t)
            SET r.run_id = $run_id,
                r.original_type = $original_rel,
                r.relation_type = $final_rel,
                r.context = $context,
                r.line_number = $line_number,
                r.resolved = $target_is_resolved
            SET r.original_types =
                CASE
                    WHEN r.original_types IS NULL THEN [$original_rel]
                    WHEN $original_rel IN r.original_types THEN r.original_types
                    ELSE r.original_types + $original_rel
                END
            """
            session.run(
                query,
                run_id=run_id,
                source_name=source_node["name"],
                target_name=target_node["name"],
                original_rel=original_rel,
                final_rel=final_rel,
                context=context or "",
                line_number=line_number,
                target_is_resolved=target_is_resolved,
            )

    def get_discovery_data(self, run_id):
        """
        Returns uploaded files plus all relations, including unresolved external targets.
        """
        with self.driver.session() as session:
            files = session.run(
                """
                MATCH (n:DependencyNode {run_id: $run_id})
                WHERE n.node_kind = 'file'
                RETURN n.id AS id,
                       n.filename AS filename,
                       n.filepath AS filepath,
                       n.detected_lang AS detected_lang,
                       n.status AS status,
                       n.name AS name,
                       n.resolved AS resolved
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
                       type(rel) AS relation_type,
                       rel.original_type AS original_relation_type,
                       rel.context AS context,
                       rel.line_number AS line_number,
                       coalesce(target.resolved, false) AS target_resolved
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
                        "name": record["name"],
                        "resolved": bool(record["resolved"]),
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
                        "original_relation_type": record["original_relation_type"],
                        "context": record["context"],
                        "line_number": record["line_number"],
                        "target_resolved": bool(record["target_resolved"]),
                    }
                    for record in relations
                ],
            }

    def get_graph(self, run_id):
        """
        Returns graph shape expected by frontend:
        {
          nodes: [{id, label, type, filepath, resolved}],
          edges: [{from, to, type}]
        }
        """
        with self.driver.session() as session:
            node_rows = session.run(
                """
                MATCH (n:DependencyNode {run_id: $run_id})
                RETURN n.name AS id,
                       coalesce(n.display_label, n.filename, n.name) AS label,
                       coalesce(n.node_type, 'file') AS node_type,
                       n.filepath AS filepath,
                       coalesce(n.resolved, false) AS resolved,
                       n.node_kind AS node_kind
                ORDER BY label
                """,
                run_id=run_id,
            )

            nodes_by_id = {}
            for record in node_rows:
                resolved = bool(record["resolved"])
                node_type = record["node_type"] or "file"

                nodes_by_id[record["id"]] = {
                    "id": record["id"],
                    "label": record["label"],
                    "type": node_type if resolved else "external",
                    "filepath": record["filepath"],
                    "resolved": resolved,
                }

            edge_rows = session.run(
                """
                MATCH (source:DependencyNode {run_id: $run_id})-[rel]->(target:DependencyNode {run_id: $run_id})
                RETURN elementId(rel) AS id,
                       source.name AS source,
                       target.name AS target,
                       type(rel) AS relation_type,
                       rel.original_type AS original_type,
                       rel.context AS context,
                       rel.line_number AS line_number
                ORDER BY source, relation_type, target
                """,
                run_id=run_id,
            )

            edges = []
            for record in edge_rows:
                source = record["source"]
                target = record["target"]

                if source not in nodes_by_id or target not in nodes_by_id:
                    continue

                edges.append({
                    "id": str(record["id"]),
                    "from": source,
                    "to": target,
                    "type": record["relation_type"],
                    "relationType": record["relation_type"],
                    "originalType": record["original_type"],
                    "context": record["context"],
                    "lineNumber": record["line_number"],
                })

            return {
                "nodes": list(nodes_by_id.values()),
                "edges": edges,
            }

    def get_impacted_programs(self, item_name, run_id=None):
        """
        Returns programs/jobs/modules that depend on a selected item.
        Includes UNRESOLVED relation also.
        """
        aliases = self._aliases_for_name(item_name)
        alias_lc = self._lower_aliases(aliases)

        with self.driver.session() as session:
            if run_id is not None:
                result = session.run(
                    """
                    MATCH (item:DependencyNode {run_id: $run_id})
                    WHERE toLower(item.name) IN $alias_lc
                       OR toLower(coalesce(item.filename, '')) IN $alias_lc
                       OR toLower(coalesce(item.filepath, '')) IN $alias_lc
                       OR any(alias IN coalesce(item.alias_lc, []) WHERE alias IN $alias_lc)
                    MATCH (p:DependencyNode {run_id: $run_id})-[:CALLS|INCLUDES|ACCESSES|READS|WRITES|READS_WRITES|EXECUTES|MAPS_TO|UNRESOLVED|IMPORTS|REFERENCES|INHERITS]->(item)
                    WHERE p.node_type IN ['program', 'job', 'telonmodule']
                       OR p:Program OR p:Job OR p:TelonModule
                    RETURN DISTINCT p.name AS name
                    ORDER BY name
                    """,
                    run_id=run_id,
                    alias_lc=alias_lc,
                )
            else:
                result = session.run(
                    """
                    MATCH (item:DependencyNode)
                    WHERE toLower(item.name) IN $alias_lc
                       OR toLower(coalesce(item.filename, '')) IN $alias_lc
                       OR toLower(coalesce(item.filepath, '')) IN $alias_lc
                       OR any(alias IN coalesce(item.alias_lc, []) WHERE alias IN $alias_lc)
                    MATCH (p:DependencyNode)-[:CALLS|INCLUDES|ACCESSES|READS|WRITES|READS_WRITES|EXECUTES|MAPS_TO|UNRESOLVED|IMPORTS|REFERENCES|INHERITS]->(item)
                    WHERE p.node_type IN ['program', 'job', 'telonmodule']
                       OR p:Program OR p:Job OR p:TelonModule
                    RETURN DISTINCT p.name AS name
                    ORDER BY name
                    """,
                    alias_lc=alias_lc,
                )

            return [record["name"] for record in result]

    def _find_node(self, run_id, value: str) -> dict[str, Any] | None:
        aliases = self._aliases_for_name(value)
        alias_lc = self._lower_aliases(aliases)

        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n:DependencyNode {run_id: $run_id})
                WHERE toLower(n.name) IN $alias_lc
                   OR toLower(coalesce(n.filename, '')) IN $alias_lc
                   OR toLower(coalesce(n.filepath, '')) IN $alias_lc
                   OR any(alias IN coalesce(n.alias_lc, []) WHERE alias IN $alias_lc)
                RETURN n.name AS name,
                       coalesce(n.resolved, false) AS resolved,
                       coalesce(n.node_type, 'file') AS node_type
                ORDER BY resolved DESC
                LIMIT 1
                """,
                run_id=run_id,
                alias_lc=alias_lc,
            )

            record = result.single()
            if not record:
                return None

            return {
                "name": record["name"],
                "resolved": bool(record["resolved"]),
                "node_type": record["node_type"],
            }

    def _create_external_node(self, run_id, name: str, inferred_type: str = "external", reason: str = ""):
        normalized_name = self._normalize_name(name)
        aliases = self._aliases_for_name(normalized_name)
        alias_lc = self._lower_aliases(aliases)

        display_label = Path(normalized_name.replace("\\", "/")).name or normalized_name

        with self.driver.session() as session:
            query = """
            MERGE (n:DependencyNode {run_id: $run_id, name: $name})
            SET n:External
            SET n.id = $name,
                n.filename = $display_label,
                n.filepath = $name,
                n.display_label = $display_label,
                n.detected_lang = $node_type,
                n.status = 'UNRESOLVED',
                n.resolved = false,
                n.node_kind = 'external',
                n.node_type = 'external',
                n.inferred_type = $node_type,
                n.reason = $reason,
                n.aliases = $aliases,
                n.alias_lc = $alias_lc
            RETURN n.name AS name,
                   n.resolved AS resolved,
                   n.node_type AS node_type
            """
            record = session.run(
                query,
                run_id=run_id,
                name=normalized_name,
                display_label=display_label,
                node_type=inferred_type,
                reason=reason,
                aliases=aliases,
                alias_lc=alias_lc,
            ).single()

            return {
                "name": record["name"],
                "resolved": bool(record["resolved"]),
                "node_type": record["node_type"],
            }

    @classmethod
    def _normalize_relation_type(cls, rel_type: str | None) -> str:
        value = str(rel_type or "DEPENDS_ON").strip().upper()
        value = re.sub(r"\s+", " ", value)
        return cls.RELATION_ALIASES.get(value, cls._safe_cypher_token(value, "DEPENDS_ON"))

    @staticmethod
    def _node_key(filepath: str | None, filename: str | None) -> str:
        return GraphService._normalize_name(filepath or filename or "")

    @staticmethod
    def _normalize_name(value: str | None) -> str:
        text = str(value or "").replace("\\", "/").strip()
        text = re.sub(r"/+", "/", text)
        return text.strip("/")

    @staticmethod
    def _aliases_for_file(filename: str | None, filepath: str | None) -> list[str]:
        aliases = set()

        for value in [filename, filepath]:
            normalized = GraphService._normalize_name(value)
            if not normalized:
                continue

            aliases.add(normalized)
            aliases.add(Path(normalized).name)

            suffix = Path(normalized).suffix
            if suffix:
                aliases.add(normalized[: -len(suffix)])
                aliases.add(Path(normalized).stem)

        return sorted(alias for alias in aliases if alias)

    @staticmethod
    def _aliases_for_name(value: str | None) -> list[str]:
        normalized = GraphService._normalize_name(value)
        if not normalized:
            return []

        aliases = set()
        aliases.add(normalized)
        aliases.add(Path(normalized).name)

        suffix = Path(normalized).suffix
        if suffix:
            aliases.add(normalized[: -len(suffix)])
            aliases.add(Path(normalized).stem)
        else:
            # Common legacy target guesses.
            aliases.add(f"{normalized}.cbl")
            aliases.add(f"{normalized}.cob")
            aliases.add(f"{normalized}.cpy")
            aliases.add(f"{normalized}.jcl")
            aliases.add(f"{normalized}.sql")

        return sorted(alias for alias in aliases if alias)

    @staticmethod
    def _lower_aliases(aliases: list[str]) -> list[str]:
        return sorted({str(alias).lower() for alias in aliases if alias})

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

    @staticmethod
    def _frontend_type_for_label(label: str) -> str:
        label = (label or "File").lower()
        mapping = {
            "program": "program",
            "copybook": "copybook",
            "table": "table",
            "job": "job",
            "telonmodule": "program",
            "file": "file",
        }
        return mapping.get(label, "file")

    @staticmethod
    def _infer_external_type(target: str, relation_type: str) -> str:
        name = (target or "").lower()

        if relation_type in {"CALLS", "EXECUTES"}:
            return "program"
        if relation_type == "INCLUDES" or name.endswith(".cpy"):
            return "copybook"
        if relation_type in {"ACCESSES", "READS", "WRITES", "READS_WRITES"}:
            if name.endswith((".sql", ".ddl")):
                return "table"
            return "file"
        if name.endswith(".jcl"):
            return "job"

        return "external"
