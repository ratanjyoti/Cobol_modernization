import os
import re
from typing import List, Tuple
from Chunking.interfaces.i_language_adapter import ILanguageAdapter
from Chunking.adapters.cobol_adapter import CobolAdapter
from Chunking.adapters.jcl_adapter import JclAdapter
from Chunking.adapters.telon_adapter import TelonAdapter
from Chunking.adapters.pli_adapter import PLIAdapter
from Chunking.adapters.fortran_adapter import FortranAdapter

class LanguageDetector:
    def __init__(self):
        self.adapters: List[ILanguageAdapter] = [
            CobolAdapter(), 
            JclAdapter(), 
            TelonAdapter(), 
            PLIAdapter(), 
            FortranAdapter()
        ]
        
        self.valid_extensions = {
            'COBOL': ['.cbl', '.cob', '.cpy'],
            'JCL': ['.jcl', '.jcll'],
            'TELON': ['.tln', '.tel', '.tlb', '.tlc'],
            'PLI': ['.pli', '.pl1'],
            'FORTRAN': ['.f', '.for', '.f90'],
            'VB.NET': ['.vb', '.bas', '.frm', '.cls', '.vbproj'],
            'C#': ['.cs', '.csproj'],
            'SOLUTION': ['.sln'],
            'XML': ['.xml', '.config'],
            'TEXT': ['.txt'],
            'SQL': ['.sql']
        }

    def _language_id(self, language_name: str) -> str:
        language_ids = {
            "COBOL": "cobol",
            "JCL": "jcl",
            "TELON": "telon",
            "PL/I": "pli",
            "Fortran": "fortran",
            "VB.NET": "vbnet",
            "C#": "csharp",
            "SOLUTION": "solution",
            "XML": "xml",
            "SQL": "sql",
        }
        return language_ids.get(language_name, language_name.lower())

    def validate_and_detect(self, file_path: str) -> Tuple[str, bool]:
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            # CRITICAL FIX 1: Read the file as a block, NOT using islice/join.
            # This preserves newlines (\n), which are required for JCL/COBOL regex.
            with open(file_path, 'r', errors='ignore') as f:
                content = f.read(20000) # Read first 20KB

            # PRIORITY 1: Explicit markers (Highest priority)
            explicit_match = re.search(r"LANGUAGE:\s*([A-Z]+)", content, re.IGNORECASE)
            if explicit_match:
                return explicit_match.group(1).upper(), True

            # PRIORITY 2: Content-based detection (The "Truth")
            # We check ALL adapters, even if the file is named .txt
            detected_lang = "UNKNOWN"
            for adapter in self.adapters:
                if adapter.detect(content):
                    # Logic for Telon classification (Batch vs Screen)
                    if adapter.language_name == "TELON" and hasattr(adapter, 'classify'):
                        detected_lang = adapter.classify(content)
                    # Logic for COBOL hybrids (Pure vs SQL vs CICS)
                    elif adapter.language_name == "COBOL":
                        has_sql = re.search(r"EXEC\s+SQL", content, re.IGNORECASE)
                        has_cics = re.search(r"EXEC\s+CICS", content, re.IGNORECASE)
                        if has_sql and has_cics: detected_lang = "cobol-sql-cics"
                        elif has_sql: detected_lang = "cobol-sql"
                        elif has_cics: detected_lang = "cobol-cics"
                        else: detected_lang = "cobol"
                    else:
                        detected_lang = self._language_id(adapter.language_name)
                    break

            # If a signature was found, the file is valid regardless of extension!
            if detected_lang != "UNKNOWN":
                return detected_lang, True

            # PRIORITY 3: Extension Fallback (Only if no content matches)
            is_supported_ext = any(ext in exts for lang, exts in self.valid_extensions.items())
            if is_supported_ext:
                for lang, exts in self.valid_extensions.items():
                    if ext in exts:
                        return self._language_id(lang), False # Extension matches, but content is ambiguous
            
            return "UNKNOWN", False

        except Exception as e:
            print(f"Error validating {file_path}: {e}")
            return "UNKNOWN", False

