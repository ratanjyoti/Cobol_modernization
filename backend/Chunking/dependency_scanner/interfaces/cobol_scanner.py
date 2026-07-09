import re
from Chunking.dependency_scanner.interfaces.i_scanner import IDependencyScanner


class CobolScanner(IDependencyScanner):
    def scan(self, content: str):
        relations = []
        source = self._strip_comments(content)

        calls = re.findall(r"\bCALL\s+(?:['\"])?([A-Z0-9#@$_-]+)(?:['\"])?", source, re.IGNORECASE)
        for target in calls:
            relations.append({"target": target, "type": "CALLS"})

        copies = re.findall(r"\bCOPY\s+(?:['\"])?([A-Z0-9#@$_-]+)(?:['\"])?", source, re.IGNORECASE)
        for target in copies:
            if target.upper() not in {"REPLACING", "SUPPRESS"}:
                relations.append({"target": target, "type": "INCLUDES"})

        read_tables = re.findall(r"\b(?:FROM|JOIN)\s+([A-Z0-9_.$#@-]+)", source, re.IGNORECASE)
        for target in read_tables:
            relations.append({"target": target.rstrip(",.;"), "type": "READS"})

        write_tables = re.findall(r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+([A-Z0-9_.$#@-]+)", source, re.IGNORECASE)
        for target in write_tables:
            relations.append({"target": target.rstrip(",.;"), "type": "WRITES"})

        return [relation for relation in relations if relation["target"]]

    @staticmethod
    def _strip_comments(content: str) -> str:
        lines = []
        for line in content.splitlines():
            if len(line) > 6 and line[6] in {"*", "/"}:
                continue
            stripped = line.lstrip()
            if stripped.startswith(("*", "*>")):
                continue
            lines.append(line)
        return "\n".join(lines)
