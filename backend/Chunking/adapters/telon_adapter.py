import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter

class TelonAdapter(ILanguageAdapter):
    @property
    def language_name(self) -> str:
        return "TELON"

    def detect(self, content: str) -> bool:
        signatures = [
            r"TELON", 
            r"SCREEN\s+SECTION", 
            r"MAP\s+SECTION"
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in signatures)
