import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter


class PLIAdapter(ILanguageAdapter):
    PROC_RE = re.compile(r"^\s*([A-Z0-9_]+)\s*:\s*PROC(?:EDURE)?\b|^\s*([A-Z0-9_]+)\s*:\s*PROCEDURE\b", re.I)

    @property
    def language_name(self) -> str:
        return "PL/I"

    def detect(self, content: str) -> bool:
        signatures = [
            r"\bPROCEDURE\b",
            r"\bDECLARE\s+([A-Z0-9_]+)\s+FIXED\s+BIN",
            r"\bDCL\s+([A-Z0-9_]+)\s+FIXED\s+BIN",
            r"\bON\s+ERROR\b",
            r"\bCALL\s+([A-Z0-9_]+)\s*\(",
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in signatures)

    def identify_structure(self, content: str) -> list[dict]:
        units = []
        for index, line in enumerate(content.splitlines(), start=1):
            match = self.PROC_RE.search(line)
            if match:
                name = match.group(1) or match.group(2)
                units.append({"name": name.upper(), "kind": "procedure", "start_line": index})
        return _close_units(units, len(content.splitlines()))


def _close_units(units: list[dict], total_lines: int) -> list[dict]:
    if not units and total_lines:
        return [{"name": "FILE", "kind": "file", "start_line": 1, "end_line": total_lines}]
    for idx, unit in enumerate(units):
        next_start = units[idx + 1]["start_line"] if idx + 1 < len(units) else total_lines + 1
        unit["end_line"] = max(unit["start_line"], next_start - 1)
    return units
