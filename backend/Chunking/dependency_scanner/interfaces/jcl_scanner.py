import re
from Chunking.dependency_scanner.interfaces.i_scanner import IDependencyScanner


class JclScanner(IDependencyScanner):
    def scan(self, content: str):
        relations = []

        # Find both //EXEC PGM=PROGRAM and //STEP EXEC PGM=PROGRAM forms.
        programs = re.findall(r"^//[^\s]*\s+EXEC\s+PGM=([A-Z0-9_-]+)", content, re.IGNORECASE | re.MULTILINE)
        for target in programs:
            relations.append({"target": target.upper(), "type": "CALLS"})

        return relations
