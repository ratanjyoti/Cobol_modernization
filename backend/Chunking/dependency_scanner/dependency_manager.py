from typing import Dict, List, Type

from Chunking.dependency_scanner.interfaces.cobol_scanner import CobolScanner
from Chunking.dependency_scanner.interfaces.i_scanner import IDependencyScanner
from Chunking.dependency_scanner.interfaces.jcl_scanner import JclScanner
from Persistence.sqlite.models import FileRelation


class DependencyManager:
    """Scans source content and stores discovered file relations."""

    def __init__(self, db_session):
        self.db = db_session
        self.scanners: Dict[str, Type[IDependencyScanner]] = {
            "cobol": CobolScanner,
            "cbl": CobolScanner,
            "cob": CobolScanner,
            "cpy": CobolScanner,
            "copybook": CobolScanner,
            "jcl": JclScanner,
        }

    def scan_and_store(self, run_id: str, source_file: str, content: str, lang: str) -> List[FileRelation]:
        scanner = self._scanner_for(lang, source_file)
        if scanner is None:
            return []

        saved_relations: List[FileRelation] = []
        seen = set()

        for relation in scanner.scan(content):
            target = (relation.get("target") or "").strip()
            relation_type = (relation.get("type") or "DEPENDS_ON").strip().upper()

            if not target:
                continue

            key = (source_file, target, relation_type)
            if key in seen:
                continue
            seen.add(key)

            file_relation = FileRelation(
                run_id=run_id,
                source_file=source_file,
                target_item=target,
                relation_type=relation_type,
            )
            self.db.add(file_relation)
            saved_relations.append(file_relation)

        self.db.flush()
        return saved_relations

    def _scanner_for(self, lang: str, source_file: str):
        normalized_lang = (lang or "").strip().lower()
        if normalized_lang in self.scanners:
            return self.scanners[normalized_lang]()

        suffix = source_file.rsplit(".", 1)[-1].lower() if "." in source_file else ""
        scanner_type = self.scanners.get(suffix)
        return scanner_type() if scanner_type else None
