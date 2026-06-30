import os
from itertools import islice
from typing import List, Tuple
from Chunking.interfaces.i_language_adapter import ILanguageAdapter
from Chunking.adapters.cobol_adapter import CobolAdapter
from Chunking.adapters.jcl_adapter import JclAdapter
from Chunking.adapters.telon_adapter import TelonAdapter

class LanguageDetector:
    def __init__(self):
        self.adapters: List[ILanguageAdapter] = [
            CobolAdapter(), JclAdapter(), TelonAdapter()
        ]
        # Supported extensions for initial filtering
        self.valid_extensions = {
            'COBOL': ['.cbl', '.cob', '.cpy'],
            'JCL': ['.jcl'],
            'TELON': ['.tln', '.tel'],
            'TEXT': ['.txt']
        }

    def validate_and_detect(self, file_path: str) -> Tuple[str, bool]:
        """
        Returns (detected_language, is_valid_code_file)
        """
        try:
            # 1. Extract extension
            ext = os.path.splitext(file_path)[1].lower()
            
            with open(file_path, 'r', errors='ignore') as f:
                content = "".join(islice(f, 100))

            # 2. Check for explicit markers (Highest Priority)
            import re
            explicit_match = re.search(r"LANGUAGE:\s*([A-Z]+)", content, re.IGNORECASE)
            if explicit_match:
                return explicit_match.group(1).upper(), True

            # 3. Content-based detection via Adapters
            detected_lang = "UNKNOWN"
            for adapter in self.adapters:
                if adapter.detect(content):
                    detected_lang = adapter.language_name
                    break

            # 4. Validation Logic: Extension vs Content
            # If we found a language in the content, it's definitely a valid code file
            if detected_lang != "UNKNOWN":
                return detected_lang, True

            # If content is empty/unknown, check if the extension is at least supported
            is_supported_ext = any(ext in exts for lang, exts in self.valid_extensions.items())
            
            if is_supported_ext:
                # It has a valid extension but no signatures in first 100 lines
                # We mark it as the language of the extension but maybe 'Invalid' or 'Review'
                for lang, exts in self.valid_extensions.items():
                    if ext in exts:
                        return lang, False # Valid extension, but content is suspicious
            
            return "UNKNOWN", False

        except Exception as e:
            print(f"Error validating {file_path}: {e}")
            return "UNKNOWN", False


