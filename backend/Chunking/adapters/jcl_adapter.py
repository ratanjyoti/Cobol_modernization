# Implementation for jcl_adapter.py
import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter

class JclAdapter(ILanguageAdapter):
    @property
    def language_name(self) -> str:
        return "JCL"

    def detect(self, content: str) -> bool:
        # We use ^\s* to allow for optional whitespace at the start of the line
        # We use re.MULTILINE so that ^ matches the start of every line, not just the start of the file
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

