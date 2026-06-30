import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter

class TelonAdapter(ILanguageAdapter):
    @property
    def language_name(self) -> str:
        return "TELON"

    def detect(self, content: str) -> bool:
        # General Telon signatures
        signatures = [r"TELON", r"SCREEN\s+SECTION", r"MAP\s+SECTION", r"T2B", r"T2C"]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in signatures)

    def classify(self, content: str) -> str:
        """New method to distinguish between T2B and T2C"""
        if re.search(r"SCREEN\s+SECTION|MAP\s+SECTION", content, re.IGNORECASE):
            return "telon-screen"
        return "telon-batch"
