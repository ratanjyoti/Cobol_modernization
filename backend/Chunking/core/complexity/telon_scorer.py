import re
from .base_scorer import BaseComplexityScorer


class TelonComplexityScorer(BaseComplexityScorer):
    def __init__(self):
        self.indicators = [
            ("Panels", r"\bPANEL\b", 3),
            ("Screens", r"\bSCREEN\b", 3),
            ("Fields", r"\bFIELD\b", 1),
            ("Maps", r"\bMAP\b", 2),
            ("Edits", r"\bEDIT\b", 2),
            ("Modules", r"\bMODULE\b", 2),
        ]

    def _code_lines(self, content: str) -> list[str]:
        return [
            line for line in content.splitlines()
            if not re.match(r"^\s*(\*|//\*)", line)
        ]

    def analyze(self, content: str) -> dict:
        code_lines = self._code_lines(content)
        clean_code = self._remove_noise("\n".join(code_lines))
        total_lines = max(len(code_lines), 1)
        calculation = []
        score = 0

        for label, pattern, weight in self.indicators:
            count = len(re.findall(pattern, clean_code, re.IGNORECASE))
            if count > 0:
                points = count * weight
                score += points
                calculation.append({"label": f"{label} ({count} x {weight})", "points": points})

        field_count = len(re.findall(r"\bFIELD\b", clean_code, re.IGNORECASE))
        if (field_count / total_lines) > 0.20:
            score += 3
            calculation.append({"label": "Field Density Bonus", "points": 3})

        tier, mode, multiplier = self.get_tier_and_mode(score)
        return {"score": score, "tier": tier, "mode": mode, "multiplier": multiplier, "calculation": calculation}
