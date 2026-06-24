# Regex Patterns for COBOL/JCL
import re

class CodeScanner:
    PATTERNS = {
        "JCL": r"(//JOB|//EXEC)",
        "TELON": r"PANEL\s+TABLE",
        "COBOL": r"(IDENTIFICATION\s+DIVISION|PROGRAM-ID\.)"
    }

    @classmethod
    def detect_language(cls, content: str) -> str:
        # Only scan the first 100 lines for speed
        lines_to_test = "\n".join(content.splitlines()[:100])
        
        for lang, pattern in cls.PATTERNS.items():
            if re.search(pattern, lines_to_test, re.IGNORECASE):
                return lang
        return "UNKNOWN"

    @classmethod
    def extract_relationships(cls, content: str):
        # Program to Program calls
        calls = re.findall(r"CALL\s+['\"]([A-Z0-9-]+)['\"]", content)
        # Program to Copybook
        copies = re.findall(r"COPY\s+['\"]([A-Z0-9-]+)['\"]", content)
        # Program to Table (SQL)
        tables = re.findall(r"FROM\s+([A-Z0-9_ ]+)|INTO\s+([A-Z0-9_ ]+)", content)
        
        return {"calls": calls, "copies": copies, "tables": tables}
