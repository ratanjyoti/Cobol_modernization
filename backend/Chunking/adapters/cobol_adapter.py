import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter


class CobolAdapter(ILanguageAdapter):
    DIVISION_RE = re.compile(r"^\s*(IDENTIFICATION|DATA|PROCEDURE|ENVIRONMENT)\s+DIVISION\b", re.I)
    SECTION_RE = re.compile(r"^\s*(WORKING-STORAGE|FILE|LINKAGE|LOCAL-STORAGE|INPUT-OUTPUT)\s+SECTION\b", re.I)
    PARAGRAPH_RE = re.compile(r"^\s*([A-Z0-9][A-Z0-9-]*)\.\s*$", re.I)
    PIC_RE = re.compile(r"^\s*(\d{2})\s+([A-Z0-9-]+)\s+PIC(?:TURE)?\s+([A-Z0-9S9XV(),.+-]+)", re.I)

    @property
    def language_name(self) -> str:
        return "COBOL"

    def detect(self, content: str) -> bool:
        signatures = [
            r"IDENTIFICATION\s+DIVISION",
            r"PROCEDURE\s+DIVISION",
            r"DATA\s+DIVISION",
            r"WORKING-STORAGE\s+SECTION",
            r"EXEC\s+SQL",
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in signatures)

    def preprocess(self, content: str) -> str:
        cleaned_lines = []
        for line in content.splitlines():
            if len(line) > 6 and line[6] in {"*", "/"}:
                continue
            stripped = line.lstrip()
            if stripped.startswith("*>"):
                continue
            line = re.sub(r"'.*?'", " ", line)
            line = re.sub(r'".*?"', " ", line)
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def identify_structure(self, content: str) -> list[dict]:
        units = []
        for index, line in enumerate(content.splitlines(), start=1):
            division = self.DIVISION_RE.search(line)
            section = self.SECTION_RE.search(line)
            paragraph = self.PARAGRAPH_RE.search(line)
            if division:
                units.append({"name": division.group(1).upper(), "kind": "division", "start_line": index})
            elif section:
                units.append({"name": section.group(1).upper(), "kind": "section", "start_line": index})
            elif paragraph and not re.match(r"^\s*\d{2}\b", line):
                units.append({"name": paragraph.group(1).upper(), "kind": "paragraph", "start_line": index})
        return _close_units(units, len(content.splitlines()))


def _close_units(units: list[dict], total_lines: int) -> list[dict]:
    if not units and total_lines:
        return [{"name": "FILE", "kind": "file", "start_line": 1, "end_line": total_lines}]
    for idx, unit in enumerate(units):
        next_start = units[idx + 1]["start_line"] if idx + 1 < len(units) else total_lines + 1
        unit["end_line"] = max(unit["start_line"], next_start - 1)
    return units
