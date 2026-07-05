import re

class ComplexityScorer:
    def calculate_score(self, content: str) -> dict:
        patterns = {
            "if_count": r"\bIF\b",
            "perform_until_count": r"PERFORM\s+UNTIL",
            "perform_varying_count": r"PERFORM\s+VARYING",
            "evaluate_count": r"\bEVALUATE\b",
        }

        counts = {
            key: len(re.findall(pattern, content, re.IGNORECASE))
            for key, pattern in patterns.items()
        }
        logic_count = sum(counts.values())
        score = logic_count

        sql_blocks = re.findall(r"EXEC\s+SQL\s+.*?(?:FROM|INTO)\s+([A-Z0-9_ ]+)", content, re.IGNORECASE | re.DOTALL)
        unique_tables = set([table.strip().split(' ')[0] for table in sql_blocks if table.strip()])
        table_bonus = 5 if len(unique_tables) > 3 else 0
        score += table_bonus

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
            "logic_count": logic_count,
            "table_count": len(unique_tables),
            "table_bonus": table_bonus,
            "if_count": counts["if_count"],
            "perform_until_count": counts["perform_until_count"],
            "perform_varying_count": counts["perform_varying_count"],
            "evaluate_count": counts["evaluate_count"],
        }
