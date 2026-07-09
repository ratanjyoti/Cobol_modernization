import re
from Chunking.dependency_scanner.interfaces.i_scanner import IDependencyScanner


class JclScanner(IDependencyScanner):
    def scan(self, content: str):
        relations = []

        programs = re.findall(r"\bEXEC\s+PGM=([A-Z0-9#@$_.-]+)", content, re.IGNORECASE)
        for target in programs:
            relations.append({"target": target, "type": "EXECUTES"})

        includes = re.findall(r"\bINCLUDE\s+MEMBER=([A-Z0-9#@$_.-]+)", content, re.IGNORECASE)
        for target in includes:
            relations.append({"target": target, "type": "INCLUDES"})

        return relations
