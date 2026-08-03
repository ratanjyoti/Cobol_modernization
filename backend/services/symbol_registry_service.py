import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from Persistence.sqlite.models import ChunkAnalysis, FileChunk, ProjectFile


class SymbolRegistryService:
    """
    Builds and locks:
    - TypeMappingTable: COBOL/Telon variables -> target language names/types
    - SignatureRegistry: COBOL/Telon paragraphs/sections -> target methods

    This prevents the AI from changing names across chunks.
    """

    COBOL_VAR_RE = re.compile(
        r"^\s*\d{2}\s+([A-Z0-9-]+)\s+(?:PIC|PICTURE)\s+([A-Z0-9\(\)VXS\+\-\.,]+)",
        re.IGNORECASE | re.MULTILINE,
    )

    COBOL_PARAGRAPH_RE = re.compile(
        r"^\s*([A-Z0-9][A-Z0-9-]{1,80})(?:\s+SECTION)?\.?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    def __init__(self, db_session: Session):
        self.db = db_session
        self._ensure_tables()

    def finalize_registry(
        self,
        run_id: str,
        target_language: str = "java",
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)

        project_files = (
            self.db.query(ProjectFile)
            .filter(ProjectFile.run_id == run_id)
            .order_by(ProjectFile.id)
            .all()
        )

        type_mappings = []
        signatures = []

        for project_file in project_files:
            raw_code = self._file_text(run_id, project_file)
            yaml_text = self._technical_yaml(run_id, project_file.id)

            if not self._is_convertible(project_file):
                continue

            type_mappings.extend(
                self._extract_type_mappings(
                    run_id=run_id,
                    file_id=project_file.id,
                    filename=project_file.filename,
                    raw_code=raw_code,
                    yaml_text=yaml_text,
                    target_language=target,
                )
            )

            signatures.extend(
                self._extract_signatures(
                    run_id=run_id,
                    file_id=project_file.id,
                    filename=project_file.filename,
                    raw_code=raw_code,
                    yaml_text=yaml_text,
                    target_language=target,
                )
            )

        self._replace_registry_rows(run_id, type_mappings, signatures)

        payload = {
            "run_id": run_id,
            "target_language": target,
            "locked": True,
            "type_mapping_count": len(type_mappings),
            "signature_count": len(signatures),
            "type_mappings": type_mappings,
            "signatures": signatures,
        }

        self._write_registry_json(run_id, target, payload)

        return payload

    def get_registry(
        self,
        run_id: str,
        target_language: str = "java",
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)

        type_rows = self.db.execute(
            text(
                """
                SELECT run_id, file_id, filename, source_name, target_name,
                       source_type, target_type, confidence, evidence, is_locked
                FROM type_mapping_table
                WHERE run_id = :run_id AND target_language = :target_language
                ORDER BY file_id, source_name
                """
            ),
            {"run_id": run_id, "target_language": target},
        ).mappings().all()

        signature_rows = self.db.execute(
            text(
                """
                SELECT run_id, file_id, filename, source_paragraph, target_method,
                       target_class, return_type, parameters, confidence, evidence, is_locked
                FROM signature_registry
                WHERE run_id = :run_id AND target_language = :target_language
                ORDER BY file_id, source_paragraph
                """
            ),
            {"run_id": run_id, "target_language": target},
        ).mappings().all()

        return {
            "run_id": run_id,
            "target_language": target,
            "locked": True,
            "type_mapping_count": len(type_rows),
            "signature_count": len(signature_rows),
            "type_mappings": [dict(row) for row in type_rows],
            "signatures": [dict(row) for row in signature_rows],
        }

    def registry_prompt_block(
        self,
        run_id: str,
        target_language: str = "java",
        file_id: int | None = None,
    ) -> str:
        registry = self.get_registry(run_id, target_language)
        type_mappings = registry["type_mappings"]
        signatures = registry["signatures"]

        if file_id is not None:
            type_mappings = [
                item for item in type_mappings
                if int(item.get("file_id") or -1) == int(file_id)
            ]
            signatures = [
                item for item in signatures
                if int(item.get("file_id") or -1) == int(file_id)
            ]

        return json.dumps(
            {
                "instruction": (
                    "These symbol and type mappings are LOCKED. "
                    "Do not rename target variables, methods, classes, or types. "
                    "Use these exact target names in generated code."
                ),
                "type_mappings": type_mappings,
                "signatures": signatures,
            },
            indent=2,
            ensure_ascii=False,
        )

    def _ensure_tables(self):
        self.db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS type_mapping_table (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    file_id INTEGER NOT NULL,
                    filename TEXT,
                    target_language TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    source_type TEXT,
                    target_type TEXT,
                    confidence REAL DEFAULT 0.75,
                    evidence TEXT,
                    is_locked INTEGER DEFAULT 1,
                    created_at TEXT,
                    UNIQUE(run_id, file_id, target_language, source_name)
                )
                """
            )
        )

        self._ensure_column("type_mapping_table", "filename", "TEXT")
        self._ensure_column("type_mapping_table", "target_language", "TEXT")
        self._ensure_column("type_mapping_table", "source_name", "TEXT")
        self._ensure_column("type_mapping_table", "target_name", "TEXT")
        self._ensure_column("type_mapping_table", "source_type", "TEXT")
        self._ensure_column("type_mapping_table", "confidence", "REAL DEFAULT 0.75")
        self._ensure_column("type_mapping_table", "evidence", "TEXT")
        self._ensure_column("type_mapping_table", "is_locked", "INTEGER DEFAULT 1")
        self._ensure_column("type_mapping_table", "created_at", "TEXT")

        self.db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS signature_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    file_id INTEGER NOT NULL,
                    filename TEXT,
                    target_language TEXT NOT NULL,
                    source_paragraph TEXT NOT NULL,
                    target_method TEXT NOT NULL,
                    target_class TEXT,
                    return_type TEXT,
                    parameters TEXT,
                    confidence REAL DEFAULT 0.75,
                    evidence TEXT,
                    is_locked INTEGER DEFAULT 1,
                    created_at TEXT,
                    UNIQUE(run_id, file_id, target_language, source_paragraph)
                )
                """
            )
        )

        self._ensure_column("signature_registry", "filename", "TEXT")
        self._ensure_column("signature_registry", "target_language", "TEXT")
        self._ensure_column("signature_registry", "source_paragraph", "TEXT")
        self._ensure_column("signature_registry", "target_class", "TEXT")
        self._ensure_column("signature_registry", "return_type", "TEXT")
        self._ensure_column("signature_registry", "parameters", "TEXT")
        self._ensure_column("signature_registry", "confidence", "REAL DEFAULT 0.75")
        self._ensure_column("signature_registry", "evidence", "TEXT")
        self._ensure_column("signature_registry", "is_locked", "INTEGER DEFAULT 1")
        self._ensure_column("signature_registry", "created_at", "TEXT")

        self.db.commit()

    def _ensure_column(self, table_name: str, column_name: str, column_type: str):
        columns = {
            row["name"]
            for row in self.db.execute(
                text(f"PRAGMA table_info({table_name})")
            ).mappings().all()
        }

        if column_name in columns:
            return

        self.db.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        )

    def _replace_registry_rows(
        self,
        run_id: str,
        type_mappings: list[dict[str, Any]],
        signatures: list[dict[str, Any]],
    ):
        self.db.execute(
            text("DELETE FROM type_mapping_table WHERE run_id = :run_id"),
            {"run_id": run_id},
        )

        self.db.execute(
            text("DELETE FROM signature_registry WHERE run_id = :run_id"),
            {"run_id": run_id},
        )

        for item in type_mappings:
            self.db.execute(
                text(
                    """
                    INSERT OR REPLACE INTO type_mapping_table (
                        run_id, file_id, filename, target_language,
                        source_name, target_name, source_type, target_type,
                        legacy_variable, legacy_type, target_field_name,
                        confidence, evidence, is_locked, created_at
                    )
                    VALUES (
                        :run_id, :file_id, :filename, :target_language,
                        :source_name, :target_name, :source_type, :target_type,
                        :source_name, :source_type, :target_name,
                        :confidence, :evidence, :is_locked, :created_at
                    )
                    """
                ),
                item,
            )

        for item in signatures:
            self.db.execute(
                text(
                    """
                    INSERT OR REPLACE INTO signature_registry (
                        run_id, file_id, filename, target_language,
                        source_paragraph, target_method, target_class,
                        return_type, parameters, confidence, evidence,
                        legacy_name, target_method_name, status,
                        is_locked, created_at
                    )
                    VALUES (
                        :run_id, :file_id, :filename, :target_language,
                        :source_paragraph, :target_method, :target_class,
                        :return_type, :parameters, :confidence, :evidence,
                        :source_paragraph, :target_method, 'LOCKED',
                        :is_locked, :created_at
                    )
                    """
                ),
                item,
            )

        self.db.commit()

    def _extract_type_mappings(
        self,
        run_id: str,
        file_id: int,
        filename: str,
        raw_code: str,
        yaml_text: str,
        target_language: str,
    ) -> list[dict[str, Any]]:
        mappings = []
        seen = set()
        created_at = datetime.utcnow().isoformat()
        normalized_code = self._normalize_cobol_check_symbols(raw_code or "")

        for match in self.COBOL_VAR_RE.finditer(normalized_code):
            source_name = match.group(1).upper()
            source_type = match.group(2).upper()

            if source_name == "FILLER":
                continue

            key = source_name
            if key in seen:
                continue

            seen.add(key)

            mappings.append(
                {
                    "run_id": run_id,
                    "file_id": file_id,
                    "filename": filename,
                    "target_language": target_language,
                    "source_name": source_name,
                    "target_name": self._target_variable_name(source_name, target_language),
                    "source_type": source_type,
                    "target_type": self._map_pic_to_target_type(source_type, target_language),
                    "confidence": 0.85,
                    "evidence": f"{source_name} PIC {source_type}",
                    "is_locked": 1,
                    "created_at": created_at,
                }
            )

        for source_name in self._extract_yaml_variable_names(yaml_text):
            source_name = source_name.upper()

            if source_name in seen:
                continue

            seen.add(source_name)

            mappings.append(
                {
                    "run_id": run_id,
                    "file_id": file_id,
                    "filename": filename,
                    "target_language": target_language,
                    "source_name": source_name,
                    "target_name": self._target_variable_name(source_name, target_language),
                    "source_type": "UNKNOWN",
                    "target_type": self._default_type(target_language),
                    "confidence": 0.55,
                    "evidence": "Extracted from technical YAML",
                    "is_locked": 1,
                    "created_at": created_at,
                }
            )

        return mappings

    def _extract_signatures(
        self,
        run_id: str,
        file_id: int,
        filename: str,
        raw_code: str,
        yaml_text: str,
        target_language: str,
    ) -> list[dict[str, Any]]:
        signatures = []
        seen = set()
        created_at = datetime.utcnow().isoformat()
        target_class = self._target_class_name(filename)
        normalized_code = self._normalize_cobol_check_symbols(raw_code or "")
        scan_text = self._signature_scan_text(filename, normalized_code)

        if not scan_text:
            return signatures

        for match in self.COBOL_PARAGRAPH_RE.finditer(scan_text):
            paragraph = match.group(1).upper()

            if (
                paragraph in self._ignored_paragraphs()
                or self._looks_like_data_name(paragraph)
                or self._looks_like_continuation_data_name(paragraph)
            ):
                continue

            if paragraph in seen:
                continue

            seen.add(paragraph)

            signatures.append(
                {
                    "run_id": run_id,
                    "file_id": file_id,
                    "filename": filename,
                    "target_language": target_language,
                    "source_paragraph": paragraph,
                    "target_method": self._target_method_name(paragraph),
                    "target_class": target_class,
                    "return_type": self._void_type(target_language),
                    "parameters": "[]",
                    "confidence": 0.8,
                    "evidence": f"COBOL paragraph: {paragraph}.",
                    "is_locked": 1,
                    "created_at": created_at,
                }
            )

        for paragraph in self._extract_yaml_paragraph_names(yaml_text if "PROCEDURE" in scan_text.upper() else ""):
            paragraph = paragraph.upper()

            if (
                paragraph in self._ignored_paragraphs()
                or self._looks_like_data_name(paragraph)
                or self._looks_like_continuation_data_name(paragraph)
            ):
                continue

            if paragraph in seen:
                continue

            seen.add(paragraph)

            signatures.append(
                {
                    "run_id": run_id,
                    "file_id": file_id,
                    "filename": filename,
                    "target_language": target_language,
                    "source_paragraph": paragraph,
                    "target_method": self._target_method_name(paragraph),
                    "target_class": target_class,
                    "return_type": self._void_type(target_language),
                    "parameters": "[]",
                    "confidence": 0.6,
                    "evidence": "Extracted from technical YAML",
                    "is_locked": 1,
                    "created_at": created_at,
                }
            )

        return signatures

    def _file_text(self, run_id: str, project_file: ProjectFile) -> str:
        chunks = (
            self.db.query(FileChunk)
            .filter(FileChunk.run_id == run_id, FileChunk.file_id == project_file.id)
            .order_by(FileChunk.chunk_index)
            .all()
        )

        texts = []
        for chunk in chunks:
            text_value = (
                getattr(chunk, "content", None)
                or getattr(chunk, "raw_code", None)
                or getattr(chunk, "chunk_text", None)
                or getattr(chunk, "text", None)
                or getattr(chunk, "source_code", None)
                or getattr(chunk, "code", None)
                or ""
            )
            if text_value:
                texts.append(str(text_value))

        return "\n\n".join(texts)

    def _technical_yaml(self, run_id: str, file_id: int) -> str:
        rows = (
            self.db.query(ChunkAnalysis)
            .join(FileChunk, ChunkAnalysis.chunk_id == FileChunk.id)
            .filter(ChunkAnalysis.run_id == run_id, FileChunk.file_id == file_id)
            .order_by(FileChunk.chunk_index)
            .all()
        )

        blocks = []

        for row in rows:
            text_value = (
                getattr(row, "technical_yaml", None)
                or getattr(row, "analysis_yaml", None)
                or getattr(row, "yaml", None)
                or getattr(row, "technical_analysis", None)
                or getattr(row, "analysis_json", None)
                or getattr(row, "analysis_text", None)
                or ""
            )
            if text_value:
                blocks.append(str(text_value))

        return "\n\n".join(blocks)

    @staticmethod
    def _extract_yaml_variable_names(yaml_text: str) -> list[str]:
        names = set()

        for match in re.finditer(r"\b([A-Z][A-Z0-9-]{2,})\b", yaml_text or ""):
            token = match.group(1).upper()
            if "-" in token and token not in SymbolRegistryService._ignored_paragraphs():
                names.add(token)

        return sorted(names)

    @staticmethod
    def _extract_yaml_paragraph_names(yaml_text: str) -> list[str]:
        names = set()

        for pattern in [
            r"paragraph\s*[:=]\s*['\"]?([A-Z0-9-]+)",
            r"section\s*[:=]\s*['\"]?([A-Z0-9-]+)",
            r"perform\s+([A-Z0-9-]+)",
        ]:
            for match in re.finditer(pattern, yaml_text or "", flags=re.IGNORECASE):
                names.add(match.group(1).upper())

        return sorted(names)

    @staticmethod
    def _target_variable_name(source_name: str, target_language: str) -> str:
        camel = SymbolRegistryService._to_camel(source_name)

        if target_language == "csharp":
            return camel[:1].upper() + camel[1:]

        return camel

    @staticmethod
    def _target_method_name(source_paragraph: str) -> str:
        value = source_paragraph or ""
        number = re.match(r"^(\d+)[-_]*(.*)$", value)
        if number:
            suffix = SymbolRegistryService._to_camel(number.group(2))
            method = f"p{number.group(1)}{suffix[:1].upper() + suffix[1:] if suffix else ''}"
        else:
            value = re.sub(r"^[A-Z]\d+[-_]*", "", value)
            method = SymbolRegistryService._to_camel(value)

        if not method:
            method = SymbolRegistryService._to_camel(source_paragraph)

        if method in {"class", "return", "public", "private", "def", "void", "switch"}:
            method = f"{method}Paragraph"

        return method

    @staticmethod
    def _target_class_name(filename: str) -> str:
        stem = Path(filename or "MigratedProgram").stem
        parts = re.split(r"[^A-Za-z0-9]+", stem)
        class_name = "".join(part[:1].upper() + part[1:].lower() for part in parts if part)

        if not class_name:
            class_name = "MigratedProgram"

        if not class_name.endswith(("Service", "Program", "Processor")):
            class_name += "Service"

        return class_name

    @staticmethod
    def _to_camel(value: str) -> str:
        parts = re.split(r"[^A-Za-z0-9]+", value.strip())
        parts = [part.lower() for part in parts if part]

        if not parts:
            return ""

        return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])

    @staticmethod
    def _map_pic_to_target_type(pic: str, target_language: str) -> str:
        pic_upper = (pic or "").upper()

        has_decimal = "V" in pic_upper or "." in pic_upper
        is_alpha = "X" in pic_upper or "A" in pic_upper
        digits = SymbolRegistryService._count_digits(pic_upper)

        if target_language == "java":
            if is_alpha:
                return "String"
            if has_decimal:
                return "BigDecimal"
            if digits > 9:
                return "long"
            return "int"

        if target_language == "python":
            if is_alpha:
                return "str"
            if has_decimal:
                return "Decimal"
            return "int"

        if target_language == "csharp":
            if is_alpha:
                return "string"
            if has_decimal:
                return "decimal"
            if digits > 9:
                return "long"
            return "int"

        return "string"

    @staticmethod
    def _count_digits(pic: str) -> int:
        total = 0

        for match in re.finditer(r"9\((\d+)\)", pic):
            total += int(match.group(1))

        total += len(re.findall(r"9", re.sub(r"9\(\d+\)", "", pic)))

        return total

    @staticmethod
    def _default_type(target_language: str) -> str:
        if target_language == "java":
            return "String"
        if target_language == "python":
            return "str"
        if target_language == "csharp":
            return "string"
        return "string"

    @staticmethod
    def _void_type(target_language: str) -> str:
        if target_language == "python":
            return "None"
        return "void"

    @staticmethod
    def _ignored_paragraphs() -> set[str]:
        return {
            "ACCEPT",
            "ACCESS",
            "CALL",
            "CLOSE",
            "IDENTIFICATION",
            "ENVIRONMENT",
            "DATA",
            "PROCEDURE",
            "DIVISION",
            "SECTION",
            "INPUT-OUTPUT",
            "WORKING-STORAGE",
            "FILE",
            "FILE-CONTROL",
            "END-IF",
            "END-EVALUATE",
            "END-PERFORM",
            "END-CALL",
            "EXIT",
            "CONTINUE",
            "GOBACK",
            "LINKAGE",
            "LOCAL-STORAGE",
            "MOVE",
            "OPEN",
            "READ",
            "REWRITE",
            "SELECT",
            "SPECIAL-NAMES",
            "STOP",
            "WRITE",
        }

    @staticmethod
    def _is_convertible(project_file: ProjectFile) -> bool:
        name = (project_file.filename or "").lower()
        lang = (project_file.detected_lang or "").lower()

        return (
            name.endswith((".cbl", ".cob", ".cpy", ".tel", ".tln"))
            or "telon" in lang
            or ("cobol" in lang and not name.endswith((".txt", ".md", ".json", ".xml")))
        )

    @staticmethod
    def _normalize_cobol_check_symbols(text_value: str) -> str:
        value = str(text_value or "")
        value = re.sub(r"==\s*UT\s*==", "", value, flags=re.IGNORECASE)
        value = value.replace("==", "")
        return value

    @staticmethod
    def _signature_scan_text(filename: str, raw_code: str) -> str:
        name = (filename or "").lower()
        upper = (raw_code or "").upper()

        procedure_match = re.search(
            r"\bPROCEDURE\s+DIVISION\b.*",
            raw_code or "",
            flags=re.IGNORECASE | re.DOTALL,
        )
        if procedure_match:
            return procedure_match.group(0)

        if name.endswith(".cpy"):
            has_pic_fields = bool(
                re.search(
                    r"^\s*\d{2}\s+[A-Z0-9-]+\s+(?:PIC|PICTURE)\b",
                    raw_code or "",
                    flags=re.IGNORECASE | re.MULTILINE,
                )
            )
            has_procedural_logic = bool(
                re.search(
                    r"^\s*(IF|EVALUATE|PERFORM|MOVE|DISPLAY|CALL|ADD|SUBTRACT|COMPUTE|SET)\b",
                    upper,
                    flags=re.MULTILINE,
                )
            )

            if has_procedural_logic and not has_pic_fields:
                return raw_code or ""

        return ""

    @staticmethod
    def _looks_like_data_name(name: str) -> bool:
        upper = (name or "").upper()
        data_markers = [
            "STATUS",
            "RECORD",
            "REC",
            "FIELD",
            "FILE",
            "FILLER",
            "AREA",
            "SQLCA",
            "OUTREC",
            "INPUT",
            "OUTPUT",
        ]
        behavior_markers = [
            "PROCESS",
            "VALIDATE",
            "VERIFY",
            "CHECK",
            "CALC",
            "UPDATE",
            "DISPLAY",
            "COMPARE",
            "ASSERT",
            "SET",
            "MAIN",
        ]
        return any(marker in upper for marker in data_markers) and not any(
            marker in upper for marker in behavior_markers
        )

    @staticmethod
    def _looks_like_continuation_data_name(name: str) -> bool:
        upper = (name or "").upper()
        return bool(
            re.match(r"^(VALUE|TEMP|OUTPUT|ACTION|BOOK)(?:-\d+|-VALUE)?$", upper)
        )

    @staticmethod
    def _normalize_target(target_language: str) -> str:
        value = str(target_language or "java").strip().lower()

        aliases = {
            "java": "java",
            "quarkus": "java",
            "python": "python",
            "py": "python",
            "fastapi": "python",
            "csharp": "csharp",
            "c#": "csharp",
            "cs": "csharp",
            "dotnet": "csharp",
            "aspnet": "csharp",
        }

        if value not in aliases:
            raise ValueError("Unsupported target language. Use java, python, or csharp.")

        return aliases[value]

    @staticmethod
    def _output_root(run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "generated_code" / run_id

    def _write_registry_json(
        self,
        run_id: str,
        target_language: str,
        payload: dict[str, Any],
    ):
        registry_dir = self._output_root(run_id) / "registry" / target_language
        registry_dir.mkdir(parents=True, exist_ok=True)

        path = registry_dir / "locked_registry.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
