import re
from .base_scorer import BaseComplexityScorer


class JclComplexityScorer(BaseComplexityScorer):
    def __init__(self):
        self.indicators = [
            ("Job steps", r"^\s*//\S+\s+EXEC\b", 2),
            ("DD statements", r"^\s*//\S+\s+DD\b", 1),
            ("Include statements", r"^\s*//\S+\s+INCLUDE\b", 3),
            ("SYSOUT outputs", r"\bSYSOUT\b", 1),
            ("COND clauses", r"\bCOND\s*=", 3),
            ("Conditional blocks", r"\bIF\b|\bTHEN\b|\bELSE\b|\bENDIF\b", 2),
            ("Inline control cards", r"\b(SYSTSIN|SYSIN)\b", 2),
            ("Dataset disposition", r"\bDISP\s*=\s*\(?\s*(ALL|OLD|SHR)\b", 1),
        ]

    def _code_lines(self, content: str) -> list[str]:
        return [line for line in content.splitlines() if not line.lstrip().startswith("//*")]

    def analyze(self, content: str) -> dict:
        clean_code = self._remove_noise("\n".join(self._code_lines(content)))
        calculation = []
        score = 0

        for label, pattern, weight in self.indicators:
            count = len(re.findall(pattern, clean_code, re.IGNORECASE | re.MULTILINE))
            if count > 0:
                points = count * weight
                score += points
                calculation.append({"label": f"{label} ({count} x {weight})", "points": points})

        step_count = len(re.findall(r"^\s*//\S+\s+EXEC\b", clean_code, re.IGNORECASE | re.MULTILINE))
        if step_count > 10:
            score += 3
            calculation.append({"label": "High Step Density Bonus", "points": 3})

        tier, mode, multiplier = self.get_tier_and_mode(score)
        return {"score": score, "tier": tier, "mode": mode, "multiplier": multiplier, "calculation": calculation}
