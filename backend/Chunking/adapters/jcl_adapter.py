import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter


class JclAdapter(ILanguageAdapter):
    STEP_RE = re.compile(r"^\s*//([^\s]+)\s+EXEC\b", re.I)
    JOB_RE = re.compile(r"^\s*//([^\s]+)\s+JOB\b", re.I)

    @property
    def language_name(self) -> str:
        return "JCL"

    def detect(self, content: str) -> bool:
        signatures = [
            r"^\s*//[^\s]+\s+JOB\b",
            r"^\s*//[^\s]+\s+EXEC\b",
            r"^\s*//[^\s]+\s+DD\b",
            r"^\s*//\s*JOB\b",
            r"^\s*//\s*EXEC\b",
            r"^\s*//\s*DD\b",
            r"\bDSN=",
            r"\bDISP=",
            r"\bSYSOUT=",
        ]
        return any(re.search(pattern, content, re.IGNORECASE | re.MULTILINE) for pattern in signatures)

    def preprocess(self, content: str) -> str:
        return "\n".join(line for line in content.splitlines() if not line.lstrip().startswith("//*"))

    def identify_structure(self, content: str) -> list[dict]:
        units = []
        for index, line in enumerate(content.splitlines(), start=1):
            job = self.JOB_RE.search(line)
            step = self.STEP_RE.search(line)
            if job:
                units.append({"name": job.group(1).upper(), "kind": "job", "start_line": index})
            elif step:
                units.append({"name": step.group(1).upper(), "kind": "step", "start_line": index})
        return _close_units(units, len(content.splitlines()))


def _close_units(units: list[dict], total_lines: int) -> list[dict]:
    if not units and total_lines:
        return [{"name": "FILE", "kind": "file", "start_line": 1, "end_line": total_lines}]
    for idx, unit in enumerate(units):
        next_start = units[idx + 1]["start_line"] if idx + 1 < len(units) else total_lines + 1
        unit["end_line"] = max(unit["start_line"], next_start - 1)
    return units
