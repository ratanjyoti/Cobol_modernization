import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter

class FortranAdapter(ILanguageAdapter):
    @property
    def language_name(self) -> str:
        return "Fortran"

    def detect(self, content: str) -> bool:
        signatures = [
            r"PROGRAM\s+[A-Z0-9_]+",
            r"SUBROUTINE\s+[A-Z0-9_]+",
            r"COMMON\s+/\s*[A-Z0-9_]+\s+/",
            r"WRITE\s*\(\s*\*",
            r"END\s+PROGRAM"
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in signatures)
