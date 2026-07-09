import re
from Chunking.dependency_scanner.interfaces.i_scanner import IDependencyScanner


class TelonScanner(IDependencyScanner):
    def scan(self, content: str):
        relations = []

        modules = re.findall(r"\b(?:MODULE|PROGRAM)\s+(?:['\"])?([A-Z0-9#@$_-]+)(?:['\"])?", content, re.IGNORECASE)
        for target in modules:
            relations.append({"target": target, "type": "MAPS_TO"})

        return relations
