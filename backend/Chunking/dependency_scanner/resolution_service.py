import os
import re


PROGRAM_EXTENSIONS = {".cbl", ".cob"}
COPYBOOK_EXTENSIONS = {".cpy"}
TABLE_EXTENSIONS = {".sql", ".ddl"}
JCL_EXTENSIONS = {".jcl"}
TELON_EXTENSIONS = {".tln", ".tel"}
KNOWN_EXTENSIONS = PROGRAM_EXTENSIONS | COPYBOOK_EXTENSIONS | TABLE_EXTENSIONS | JCL_EXTENSIONS | TELON_EXTENSIONS
class ResolutionService:
    """Resolve raw scanner hits into verified file-to-file relations."""

    def __init__(self, db_session):
        self.db = db_session
        self.phonebook = {}

    def build_phonebook(self, run_id: str):
        from Persistence.sqlite.models import ProjectFile

        self.phonebook = {}
        files = self.db.query(ProjectFile).filter_by(run_id=run_id).all()
        for project_file in files:
            metadata = {
                "id": project_file.id,
                "original_name": project_file.filename,
                "graph_name": project_file.filepath or project_file.filename,
                "filepath": project_file.filepath,
                "ext": os.path.splitext(project_file.filename)[1].lower(),
                "detected_lang": project_file.detected_lang,
            }
            self._add_alias(project_file.filename, metadata)
            self._add_alias(os.path.splitext(project_file.filename)[0], metadata)
            if project_file.filepath:
                self._add_full_alias(project_file.filepath, metadata)
                self._add_alias(project_file.filepath, metadata)
                self._add_alias(os.path.basename(project_file.filepath), metadata)
                self._add_alias(os.path.splitext(os.path.basename(project_file.filepath))[0], metadata)
        return self.phonebook

    def resolve(self, raw_name: str):
        return self.phonebook.get(self.clean_full_name(raw_name)) or self.phonebook.get(self.clean_name(raw_name))

    def resolve_run_relations(self, run_id: str):
        """
        Keep only relations whose source and target both exist in ProjectFile.
        This prevents random SQL words, unresolved CALL names, and missing copybooks
        from becoming graph nodes or edges.
        """
        from Persistence.sqlite.models import FileRelation

        self.build_phonebook(run_id)
        relations = self.db.query(FileRelation).filter_by(run_id=run_id).all()
        kept = []
        seen = set()

        for relation in relations:
            source = self.resolve(relation.source_file)
            target = self.resolve(relation.target_item)

            if not source or not target:
                self.db.delete(relation)
                continue

            relation.source_file = source["graph_name"]
            relation.target_item = target["graph_name"]
            relation.relation_type = self.relation_type_for_file(
                source_ext=source["ext"],
                target_ext=target["ext"],
                suggested_type=relation.relation_type,
            )

            key = (relation.source_file, relation.target_item, relation.relation_type)
            if key in seen:
                self.db.delete(relation)
                continue

            seen.add(key)
            kept.append(relation)

        self.db.flush()
        return kept

    def _add_alias(self, value: str, metadata: dict):
        clean = self.clean_name(value)
        if clean and clean not in self.phonebook:
            self.phonebook[clean] = metadata

    def _add_full_alias(self, value: str, metadata: dict):
        clean = self.clean_full_name(value)
        if clean and clean not in self.phonebook:
            self.phonebook[clean] = metadata

    @staticmethod
    def clean_full_name(value: str) -> str:
        raw = str(value or "").strip().strip("\'\"").replace("\\", "/")
        return re.sub(r"[^A-Za-z0-9#@$]", "", raw).upper()

    @staticmethod
    def clean_name(value: str) -> str:
        raw = str(value or "").strip().strip("'\"").replace("\\", "/")
        leaf = os.path.basename(raw)
        base, ext = os.path.splitext(leaf)
        if ext.lower() in KNOWN_EXTENSIONS:
            candidate = base
        elif "." in leaf:
            candidate = leaf.rsplit(".", 1)[-1]
        else:
            candidate = leaf
        return re.sub(r"[^A-Za-z0-9#@$]", "", candidate).upper()

    @staticmethod
    def clean_relation_type(value: str) -> str:
        return re.sub(r"\W+", "_", str(value or "").upper()).strip("_")

    @classmethod
    def relation_type_for_file(cls, source_ext: str, target_ext: str, suggested_type: str) -> str:
        suggested = cls.clean_relation_type(suggested_type)
        source_ext = (source_ext or "").lower()
        target_ext = (target_ext or "").lower()

        if target_ext in COPYBOOK_EXTENSIONS:
            return "INCLUDES"
        if target_ext in TABLE_EXTENSIONS:
            return cls.normalize_table_relation(suggested)
        if source_ext in JCL_EXTENSIONS and target_ext in PROGRAM_EXTENSIONS:
            return "EXECUTES"
        if source_ext in TELON_EXTENSIONS and target_ext in PROGRAM_EXTENSIONS:
            return "MAPS_TO"
        if target_ext in PROGRAM_EXTENSIONS:
            if suggested in {"EXECUTES", "MAPS_TO"}:
                return suggested
            return "CALLS"
        if target_ext in JCL_EXTENSIONS and suggested == "INCLUDES":
            return "INCLUDES"
        return suggested or "DEPENDS_ON"

    @staticmethod
    def normalize_table_relation(suggested_type: str) -> str:
        if suggested_type in {"READS", "WRITES"}:
            return suggested_type
        return "ACCESSES"




