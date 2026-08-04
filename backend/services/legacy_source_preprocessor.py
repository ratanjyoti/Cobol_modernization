from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from Chunking.adapters.cobol_adapter import CobolAdapter


PSEUDO_PREFIX_RE = re.compile(
    r"==\s*([A-Z0-9-]+)\s*==(?=[A-Z0-9-])",
    re.IGNORECASE,
)


@dataclass
class LineMapEntry:
    normalized_line: int
    original_line: int
    original_text: str


@dataclass
class CobolStatement:
    text: str
    start_line: int
    end_line: int


@dataclass
class Paragraph:
    name: str
    start_line: int
    end_line: int
    statements: list[CobolStatement] = field(default_factory=list)


@dataclass
class LegacySourceProfile:
    source_code: str
    line_map: list[LineMapEntry]
    paragraphs: list[Paragraph]
    detected_language: str
    artifact_type: str
    file_role: str
    source_character_count: int


class LegacySourcePreprocessor:
    """Normalizes legacy source while keeping original-line traceability."""

    STATEMENT_START_RE = re.compile(
        r"^(IF|EVALUATE|WHEN|ELSE|END-IF|END-EVALUATE|PERFORM|ADD|SUBTRACT|"
        r"MULTIPLY|DIVIDE|COMPUTE|MOVE|SET|CALL|READ|WRITE|REWRITE|DELETE|"
        r"DISPLAY|INITIALIZE|EXEC)\b",
        re.IGNORECASE,
    )

    def prepare(
        self,
        source_code: str,
        file_name: str = "",
        detected_language: str = "",
    ) -> LegacySourceProfile:
        normalized_source, line_map = self.normalize_source(source_code)
        language = self.detect_language(normalized_source, file_name, detected_language)
        artifact_type = self.detect_artifact_type(normalized_source, file_name, language)
        file_role = self.detect_file_role(normalized_source, file_name)
        paragraphs = (
            self.assemble_cobol_paragraphs(normalized_source)
            if language in {"cobol", "copybook"}
            else []
        )

        return LegacySourceProfile(
            source_code=normalized_source,
            line_map=line_map,
            paragraphs=paragraphs,
            detected_language=language,
            artifact_type=artifact_type,
            file_role=file_role,
            source_character_count=len(source_code or ""),
        )

    def normalize_source(self, source_code: str) -> tuple[str, list[LineMapEntry]]:
        normalized_lines: list[str] = []
        line_map: list[LineMapEntry] = []

        for original_line, raw_line in enumerate((source_code or "").splitlines(), start=1):
            normalized = PSEUDO_PREFIX_RE.sub(
                lambda match: f"{match.group(1)}-",
                raw_line,
            )
            normalized_lines.append(normalized)
            line_map.append(
                LineMapEntry(
                    normalized_line=len(normalized_lines),
                    original_line=original_line,
                    original_text=raw_line,
                )
            )

        return "\n".join(normalized_lines), line_map

    def detect_language(
        self,
        source_code: str,
        file_name: str,
        detected_language: str = "",
    ) -> str:
        normalized = str(detected_language or "").lower().strip()
        if normalized in {"cobol", "copybook", "jcl", "sql", "db2", "telon", "pli", "pl/i", "pl1"}:
            return "pli" if normalized in {"pl/i", "pl1"} else normalized

        ext = Path(file_name or "").suffix.lower()
        upper = (source_code or "").upper()

        if ext in {".cob", ".cbl", ".cpy"}:
            return "copybook" if ext == ".cpy" else "cobol"
        if ext in {".jcl", ".job"}:
            return "jcl"
        if ext == ".sql" or "EXEC SQL" in upper:
            return "sql"
        if "IDENTIFICATION DIVISION" in upper or "PROCEDURE DIVISION" in upper:
            return "cobol"
        if re.search(r"(?im)^\s*(IF|EVALUATE|PERFORM|ADD|MOVE|CALL)\b", upper):
            return "cobol"
        if re.search(r"(?im)^\s*\d{2}\s+[A-Z0-9-]+\s+PIC\b", upper):
            return "copybook"

        return normalized or "unknown"

    def detect_artifact_type(self, source_code: str, file_name: str, language: str) -> str:
        ext = Path(file_name or "").suffix.lower()
        upper = (source_code or "").upper()

        if language == "jcl":
            return "jcl_job"
        if language == "sql":
            return "sql_script"
        if ext == ".cpy" or language == "copybook":
            if re.search(r"(?im)^\s*(IF|EVALUATE|PERFORM|ADD|MOVE|CALL|DISPLAY|SET)\b", upper):
                return "procedural_copybook"
            return "data_copybook"
        if language == "cobol":
            if "BATCH" in upper or re.search(r"(?im)^\s*ACCEPT\b", upper):
                return "batch_program"
            return "domain_program"
        return "technical_utility"

    def detect_file_role(self, source_code: str, file_name: str) -> str:
        text = f"{file_name}\n{source_code}".upper()
        name = Path(file_name or "").name.upper()

        if any(marker in text for marker in ("ASSERT", "MOCK", "TEST", "UNIT-TEST", "UT-")):
            return "test_support"
        if re.search(r"\b(CCHECK|CHECKPD|TEST|MOCK|ASSERT)\b", name):
            return "test_support"
        if any(marker in text for marker in ("SORT", "UTILITY", "ABEND", "LOGGING")):
            return "technical_utility"
        if " EXEC PGM=" in text or name.endswith((".JCL", ".JOB")):
            return "jcl_job"
        if " PIC " in text and not re.search(r"(?im)^\s*(IF|EVALUATE|PERFORM|ADD|MOVE|CALL)\b", text):
            return "data_copybook"
        if "BATCH" in text:
            return "batch_program"
        return "domain_program"

    def assemble_cobol_paragraphs(self, source_code: str) -> list[Paragraph]:
        lines = source_code.splitlines()
        units = [
            unit for unit in CobolAdapter().identify_structure(source_code)
            if unit.get("kind") in {"paragraph", "file"}
        ]
        if not units and lines:
            units = [{"name": "FILE", "kind": "file", "start_line": 1, "end_line": len(lines)}]

        paragraphs: list[Paragraph] = []
        for unit in units:
            start = int(unit.get("start_line") or 1)
            end = int(unit.get("end_line") or start)
            statements = self._assemble_statements(lines, start, end)
            paragraphs.append(
                Paragraph(
                    name=str(unit.get("name") or "FILE").upper(),
                    start_line=start,
                    end_line=end,
                    statements=statements,
                )
            )

        return paragraphs

    def to_technical_yaml(self, profile: LegacySourceProfile) -> str:
        paragraphs = []
        decisions = []
        calculations = []
        state_changes = []

        for paragraph in profile.paragraphs:
            calls = []
            for statement in paragraph.statements:
                text = statement.text
                upper = text.upper()
                calls.extend(re.findall(r"\b(?:PERFORM|CALL)\s+['\"]?([A-Z0-9-]+)", text, flags=re.IGNORECASE))
                if upper.startswith("IF "):
                    decisions.append(
                        {
                            "paragraph": paragraph.name,
                            "condition": self._statement_condition(text),
                            "start_line": statement.start_line,
                            "end_line": statement.end_line,
                        }
                    )
                elif upper.startswith("EVALUATE "):
                    decisions.append(
                        {
                            "paragraph": paragraph.name,
                            "condition": text,
                            "start_line": statement.start_line,
                            "end_line": statement.end_line,
                        }
                    )
                elif re.match(r"(?i)^(ADD|SUBTRACT|MULTIPLY|DIVIDE|COMPUTE)\b", text):
                    calculations.append(
                        {
                            "paragraph": paragraph.name,
                            "operation": upper.split()[0],
                            "statement": text,
                            "start_line": statement.start_line,
                            "end_line": statement.end_line,
                        }
                    )
                elif re.match(r"(?i)^(MOVE|SET|INITIALIZE)\b", text):
                    state_changes.append(
                        {
                            "paragraph": paragraph.name,
                            "statement": text,
                            "start_line": statement.start_line,
                            "end_line": statement.end_line,
                        }
                    )

            paragraphs.append(
                {
                    "name": paragraph.name,
                    "start_line": paragraph.start_line,
                    "end_line": paragraph.end_line,
                    "calls": sorted(set(calls)),
                }
            )

        payload = {
            "detected_language": profile.detected_language,
            "artifact_type": profile.artifact_type,
            "file_role": profile.file_role,
            "paragraphs": paragraphs,
            "decisions": decisions,
            "calculations": calculations,
            "state_changes": state_changes,
        }
        return self._dict_to_yaml(payload)

    def _assemble_statements(
        self,
        lines: list[str],
        start_line: int,
        end_line: int,
    ) -> list[CobolStatement]:
        statements: list[CobolStatement] = []
        buffer: list[str] = []
        statement_start = start_line

        for line_no in range(start_line, end_line + 1):
            clean = self._clean_cobol_line(lines[line_no - 1] if line_no - 1 < len(lines) else "")
            if not clean:
                continue
            if re.match(r"(?i)^[A-Z0-9][A-Z0-9-]*\.\s*$", clean):
                continue

            starts_new = bool(buffer and self.STATEMENT_START_RE.match(clean))
            if starts_new and not self._needs_continuation(buffer[-1]):
                self._flush_statement(statements, buffer, statement_start, line_no - 1)
                buffer = []

            if not buffer:
                statement_start = line_no
            buffer.append(clean.rstrip("."))

            if clean.rstrip().endswith("."):
                self._flush_statement(statements, buffer, statement_start, line_no)
                buffer = []

        if buffer:
            self._flush_statement(statements, buffer, statement_start, end_line)

        return statements

    def _flush_statement(
        self,
        statements: list[CobolStatement],
        buffer: list[str],
        start_line: int,
        end_line: int,
    ) -> None:
        text = re.sub(r"\s+", " ", " ".join(buffer)).strip().rstrip(".")
        if text:
            statements.append(CobolStatement(text=text, start_line=start_line, end_line=end_line))

    @staticmethod
    def _clean_cobol_line(line: str) -> str:
        text = str(line or "")
        if len(text) > 6 and text[6] in {"*", "/"}:
            return ""
        text = re.sub(r"^\d{5,6}\s*", "", text).strip()
        if text.startswith("*>") or text.startswith("*"):
            return ""
        return text

    @staticmethod
    def _needs_continuation(line: str) -> bool:
        return bool(re.search(r"\b(IS|TO|THAN|ALSO|AND|OR|NOT|=|>|<)\s*$", line, flags=re.IGNORECASE))

    @staticmethod
    def _statement_condition(statement: str) -> str:
        condition = re.sub(r"(?i)^\s*IF\s+", "", statement)
        condition = re.split(r"(?i)\bTHEN\b|\bPERFORM\b|\bMOVE\b|\bSET\b|\bDISPLAY\b", condition, maxsplit=1)[0]
        return condition.strip()

    def _dict_to_yaml(self, value: Any, indent: int = 0) -> str:
        pad = " " * indent
        if isinstance(value, dict):
            lines: list[str] = []
            for key, item in value.items():
                if isinstance(item, (dict, list)):
                    lines.append(f"{pad}{key}:")
                    lines.append(self._dict_to_yaml(item, indent + 2))
                else:
                    lines.append(f"{pad}{key}: {self._yaml_scalar(item)}")
            return "\n".join(lines)
        if isinstance(value, list):
            if not value:
                return f"{pad}[]"
            lines = []
            for item in value:
                if isinstance(item, dict):
                    first = True
                    for key, nested in item.items():
                        prefix = f"{pad}- " if first else f"{pad}  "
                        if isinstance(nested, (dict, list)):
                            lines.append(f"{prefix}{key}:")
                            lines.append(self._dict_to_yaml(nested, indent + 4))
                        else:
                            lines.append(f"{prefix}{key}: {self._yaml_scalar(nested)}")
                        first = False
                else:
                    lines.append(f"{pad}- {self._yaml_scalar(item)}")
            return "\n".join(lines)
        return f"{pad}{self._yaml_scalar(value)}"

    @staticmethod
    def _yaml_scalar(value: Any) -> str:
        text = str(value if value is not None else "")
        if not text or re.search(r"[:#\n\r]|^\s|\s$", text):
            return json_escape(text)
        return text


def json_escape(text: str) -> str:
    import json

    return json.dumps(str(text or ""))
