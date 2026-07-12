import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter


class TelonAdapter(ILanguageAdapter):
    SECTION_RE = re.compile(r"^\s*([A-Z0-9_-]+\s+(?:SECTION|SCREEN|MAP|PANEL))\b", re.I)

    @property
    def language_name(self) -> str:
        return "TELON"

    def detect(self, content: str) -> bool:
        signatures = [r"TELON", r"SCREEN\s+SECTION", r"MAP\s+SECTION", r"\bT2B\b", r"\bT2C\b"]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in signatures)

    def classify(self, content: str) -> str:
        if re.search(r"SCREEN\s+SECTION|MAP\s+SECTION", content, re.IGNORECASE):
            return "telon-screen"
        return "telon-batch"

    def identify_structure(self, content: str) -> list[dict]:
        units = []
        for index, line in enumerate(content.splitlines(), start=1):
            match = self.SECTION_RE.search(line)
            if match:
                units.append({"name": match.group(1).upper(), "kind": "section", "start_line": index})
        return _close_units(units, len(content.splitlines()))


def _close_units(units: list[dict], total_lines: int) -> list[dict]:
    if not units and total_lines:
        return [{"name": "FILE", "kind": "file", "start_line": 1, "end_line": total_lines}]
    for idx, unit in enumerate(units):
        next_start = units[idx + 1]["start_line"] if idx + 1 < len(units) else total_lines + 1
        unit["end_line"] = max(unit["start_line"], next_start - 1)
    return units
