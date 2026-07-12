import re
from Persistence.sqlite.models import SignatureRegistry, TypeMappingTable
from Chunking.core.settings import normalize_language
from Chunking.core.signature_registry import ConsistencyEngine
from Chunking.core.type_mapping_table import infer_target_type, to_camel_case


class SymbolExtractor:
    COBOL_PIC_RE = re.compile(r"^\s*(\d{2})\s+([A-Z0-9-]+)\s+PIC(?:TURE)?\s+([A-Z0-9S9XV(),.+-]+)", re.I | re.M)
    COBOL_PARAGRAPH_RE = re.compile(r"^\s*([A-Z0-9][A-Z0-9-]*)\.\s*$", re.I | re.M)
    JCL_STEP_RE = re.compile(r"^\s*//([^\s]+)\s+EXEC\b", re.I | re.M)
    PLI_PROC_RE = re.compile(r"^\s*([A-Z0-9_]+)\s*:\s*PROC(?:EDURE)?\b", re.I | re.M)
    FORTRAN_UNIT_RE = re.compile(r"^\s*(?:PROGRAM|SUBROUTINE|FUNCTION)\s+([A-Z0-9_]+)", re.I | re.M)
    TELON_UNIT_RE = re.compile(r"^\s*([A-Z0-9_-]+\s+(?:SECTION|SCREEN|MAP|PANEL))\b", re.I | re.M)

    def __init__(self, db_session):
        self.db = db_session
        self.consistency = ConsistencyEngine(db_session)

    def extract_and_lock(self, run_id: str, file_id: int | None, content: str, lang: str):
        normalized = normalize_language(lang)
        if normalized == "COBOL":
            self._extract_cobol(run_id, file_id, content)
        elif normalized == "JCL":
            self._lock_signatures(run_id, file_id, self.JCL_STEP_RE.findall(content))
        elif normalized == "PLI":
            self._lock_signatures(run_id, file_id, self.PLI_PROC_RE.findall(content))
        elif normalized == "FORTRAN":
            self._lock_signatures(run_id, file_id, self.FORTRAN_UNIT_RE.findall(content))
        elif normalized == "TELON":
            self._lock_signatures(run_id, file_id, self.TELON_UNIT_RE.findall(content))
        self.db.commit()

    def _extract_cobol(self, run_id: str, file_id: int | None, content: str):
        seen_variables = set()
        for _level, name, pic in self.COBOL_PIC_RE.findall(content):
            key = name.upper()
            if key in seen_variables:
                continue
            seen_variables.add(key)
            self.consistency.lock_variable(run_id, name, pic, file_id=file_id)

        seen_paragraphs = set()
        for paragraph in self.COBOL_PARAGRAPH_RE.findall(content):
            key = paragraph.upper()
            if paragraph.isdigit() or key in seen_paragraphs:
                continue
            seen_paragraphs.add(key)
            self.consistency.lock_signature(run_id, paragraph, file_id=file_id)

    def _lock_signatures(self, run_id: str, file_id: int | None, names):
        for raw_name in names:
            name = raw_name[0] if isinstance(raw_name, tuple) else raw_name
            if name:
                self.consistency.lock_signature(run_id, str(name).strip(), file_id=file_id)

    def upsert_type(self, run_id: str, file_id: int | None, legacy_variable: str, legacy_type: str, target_language: str = "java"):
        legacy_key = legacy_variable.upper()
        existing = self.db.query(TypeMappingTable).filter_by(
            run_id=run_id,
            file_id=file_id,
            legacy_variable=legacy_key,
        ).first()
        if existing:
            return existing
        mapping = TypeMappingTable(
            run_id=run_id,
            file_id=file_id,
            legacy_variable=legacy_key,
            legacy_type=legacy_type.upper(),
            target_type=infer_target_type(legacy_type, target_language),
            target_field_name=to_camel_case(legacy_key),
        )
        self.db.add(mapping)
        return mapping

    def upsert_signature(self, run_id: str, file_id: int | None, legacy_name: str):
        legacy_key = legacy_name.strip().rstrip(".").upper()
        existing = self.db.query(SignatureRegistry).filter_by(
            run_id=run_id,
            file_id=file_id,
            legacy_name=legacy_key,
        ).first()
        if existing:
            return existing
        method = to_camel_case(legacy_key)
        signature = SignatureRegistry(
            run_id=run_id,
            file_id=file_id,
            legacy_name=legacy_key,
            target_method_name=method,
            target_signature=f"void {method}()",
        )
        self.db.add(signature)
        return signature

