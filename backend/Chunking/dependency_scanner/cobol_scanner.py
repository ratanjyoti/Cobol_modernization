import re
from Chunking.dependency_scanner.interfaces.i_scanner import IDependencyScanner

class CobolScanner(IDependencyScanner):
    def scan(self, content: str):
        relations = []
        
        # 1. Program Calls (CALL 'PROG')
        calls = re.findall(r"CALL\s+['\"]([A-Z0-9-]+)['\"]", content, re.IGNORECASE)
        for target in calls:
            relations.append({"target": target, "type": "CALLS"})
            
        # 2. Copybooks (COPY 'NAME')
        copies = re.findall(r"COPY\s+['\"]([A-Z0-9-]+)['\"]", content, re.IGNORECASE)
        for target in copies:
            relations.append({"target": target, "type": "INCLUDES"})
            
        # 3. SQL READS (SELECT ... FROM Table)
        reads = re.findall(r"SELECT\s+.*?\s+FROM\s+([A-Z0-9_ ]+)", content, re.IGNORECASE | re.DOTALL)
        for target in reads:
            clean_table = target.strip().split(' ')[0].split(',')[0]
            relations.append({"target": clean_table, "type": "READS"})

        # 4. SQL WRITES (INSERT, UPDATE, DELETE)
        writes = re.findall(r"(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+([A-Z0-9_ ]+)", content, re.IGNORECASE)
        for target in writes:
            clean_table = target.strip().split(' ')[0].split(',')[0]
            relations.append({"target": clean_table, "type": "WRITES"})
            
        return relations
