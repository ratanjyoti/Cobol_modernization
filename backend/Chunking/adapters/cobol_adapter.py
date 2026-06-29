# Implementation for cobol_adapter.py
import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter

class CobolAdapter(ILanguageAdapter):
    @property
    def language_name(self) -> str:
        return "COBOL"

    def detect(self, content: str) -> bool:
        signatures = [
            r"IDENTIFICATION\s+DIVISION",
            r"PROCEDURE\s+DIVISION",
            r"DATA\s+DIVISION",
            r"WORKING-STORAGE\s+SECTION"
        ]
        # Also detect COBOL SQL
        sql_signatures = [r"EXEC\s+SQL"]
        
        all_patterns = signatures + sql_signatures
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in all_patterns)
