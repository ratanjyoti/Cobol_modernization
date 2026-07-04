import re

class ComplexityScorer:
    def calculate_score(self, content: str) -> dict:
        # 1. Loop and Conditional Count
        # Sum IF, PERFORM UNTIL, PERFORM VARYING, and EVALUATE usage
        patterns = [
            r"\bIF\b", 
            r"PERFORM\s+UNTIL", 
            r"PERFORM\s+VARYING", 
            r"\bEVALUATE\b"
        ]
        
        score = 0
        for pattern in patterns:
            score += len(re.findall(pattern, content, re.IGNORECASE))

        # 2. Database Intensity
        # Scan EXEC SQL blocks for unique table names
        sql_blocks = re.findall(r"EXEC\s+SQL\s+.*?(?:FROM|INTO)\s+([A-Z0-9_ ]+)", content, re.IGNORECASE | re.DOTALL)
        unique_tables = set([table.strip().split(' ')[0] for table in sql_blocks])
        
        if len(unique_tables) > 3:
            score += 5 # High Complexity Bonus
            
        # 3. Final Tier Assignment
        if score < 5:
            tier = "Low"
            effort = "Turbo"
        elif 5 <= score < 15:
            tier = "Medium"
            effort = "Balanced"
        else:
            tier = "High"
            effort = "Thorough"

        return {
            "score": score,
            "tier": tier,
            "reasoning_effort": effort,
            "table_count": len(unique_tables)
        }

