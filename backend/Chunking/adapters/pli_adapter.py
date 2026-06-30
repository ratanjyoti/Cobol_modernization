import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter

class PLIAdapter(ILanguageAdapter):
    @property
    def language_name(self) -> str:
        return "PL/I"

    def detect(self, content: str) -> bool:
        signatures = [
            r"PROCEDURE",
            r"DECLARE\s+([A-Z0-9_]+)\s+FIXED\s+BIN",
            r"DCL\s+([A-Z0-9_]+)\s+FIXED\s+BIN",
            r"ON\s+ERROR",
            r"CALL\s+([A-Z0-9_]+)\s*\("
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in signatures)
