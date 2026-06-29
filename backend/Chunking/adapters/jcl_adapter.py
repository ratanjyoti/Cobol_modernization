# Implementation for jcl_adapter.py
import re
from Chunking.interfaces.i_language_adapter import ILanguageAdapter

class JclAdapter(ILanguageAdapter):
    @property
    def language_name(self) -> str:
        return "JCL"

    def detect(self, content: str) -> bool:
        signatures = [
            r"//JOB", 
            r"//EXEC", 
            r"//DD", 
            r"//STEPLIB"
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in signatures)
