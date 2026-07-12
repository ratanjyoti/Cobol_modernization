import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter


class FortranAdapter(ILanguageAdapter):
    UNIT_RE = re.compile(r"^\s*(PROGRAM|SUBROUTINE|FUNCTION|MODULE)\s+([A-Z0-9_]+)", re.I)

    @property
    def language_name(self) -> str:
        return "Fortran"

    def detect(self, content: str) -> bool:
        signatures = [
            r"\bPROGRAM\s+[A-Z0-9_]+",
            r"\bSUBROUTINE\s+[A-Z0-9_]+",
            r"\bCOMMON\s*/\s*[A-Z0-9_]+\s*/",
            r"\bWRITE\s*\(\s*\*",
            r"\bEND\s+PROGRAM\b",
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in signatures)

    def identify_structure(self, content: str) -> list[dict]:
        units = []
        for index, line in enumerate(content.splitlines(), start=1):
            match = self.UNIT_RE.search(line)
            if match:
                units.append({"name": match.group(2).upper(), "kind": match.group(1).lower(), "start_line": index})
        return _close_units(units, len(content.splitlines()))


def _close_units(units: list[dict], total_lines: int) -> list[dict]:
    if not units and total_lines:
        return [{"name": "FILE", "kind": "file", "start_line": 1, "end_line": total_lines}]
    for idx, unit in enumerate(units):
        next_start = units[idx + 1]["start_line"] if idx + 1 < len(units) else total_lines + 1
        unit["end_line"] = max(unit["start_line"], next_start - 1)
    return units
