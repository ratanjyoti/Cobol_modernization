import re
from Chunking.dependency_scanner.interfaces.i_scanner import IDependencyScanner


class CobolScanner(IDependencyScanner):
    def scan(self, content: str):
        relations = []

        # Find CALLs, including CALL 'PGM', CALL "PGM", and CALL PGM.
        calls = re.findall(r"\bCALL\s+(?:['\"])?([A-Z0-9_-]+)(?:['\"])?", content, re.IGNORECASE)
        for target in calls:
            relations.append({"target": target.upper(), "type": "CALLS"})

        # Find COPY statements, including quoted and unquoted copybook names.
        copies = re.findall(r"\bCOPY\s+(?:['\"])?([A-Z0-9_-]+)(?:['\"])?", content, re.IGNORECASE)
        for target in copies:
            relations.append({"target": target.upper(), "type": "INCLUDES"})

        # Find SQL tables after FROM, JOIN, UPDATE, or INTO.
        tables = re.findall(r"\b(?:FROM|JOIN|UPDATE|INTO)\s+([A-Z0-9_.$-]+)", content, re.IGNORECASE)
        for target in tables:
            clean_target = target.strip().rstrip(",.;")
            if clean_target:
                relations.append({"target": clean_target.upper(), "type": "READS_WRITES"})

        return relations
