import re
from .base_scorer import BaseComplexityScorer


class CobolComplexityScorer(BaseComplexityScorer):
    def __init__(self):
        # Weighted indicators except CALL.
        # CALL is handled separately because END-CALL and paragraph names like 600-MAKE-CALL
        # should not be counted as executable CALL statements.
        self.indicators = [
            ("EXEC SQL", r"(?<![A-Z0-9_-])EXEC\s+SQL\b", 3),
            ("EXEC CICS", r"(?<![A-Z0-9_-])EXEC\s+CICS\b", 4),
            ("EXEC DLI", r"(?<![A-Z0-9_-])EXEC\s+DLI\b", 4),
            ("PERFORM VARYING", r"(?<![A-Z0-9_-])PERFORM\s+VARYING\b", 2),

            # Practical modernization scoring:
            # Count every EVALUATE, not only EVALUATE TRUE.
            # This counts EVALUATE VALUE-1 and EVALUATE VALUE-2 also.
            ("EVALUATE", r"(?<![A-Z0-9_-])EVALUATE\s+", 2),

            ("SEARCH ALL", r"(?<![A-Z0-9_-])SEARCH\s+ALL\b", 2),
            ("REDEFINES", r"(?<![A-Z0-9_-])REDEFINES\b", 2),
            ("OCCURS DEPENDING", r"(?<![A-Z0-9_-])OCCURS\s+DEPENDING\b", 3),
            ("UNSTRING", r"(?<![A-Z0-9_-])UNSTRING\b", 2),
            ("ALTER", r"(?<![A-Z0-9_-])ALTER\b", 3),
            ("GO TO DEPENDING", r"(?<![A-Z0-9_-])GO\s+TO\s+DEPENDING\b", 3),
        ]

    def _is_comment_line(self, line: str) -> bool:
        stripped = line.strip()

        if not stripped:
            return True

        # Fixed-format COBOL comment indicator in column 7.
        if len(line) > 6 and line[6] in {"*", "/"}:
            return True

        # Free-format COBOL comments.
        if stripped.startswith(("*", "//", "*>")):
            return True

        return False

    def _remove_inline_comment(self, line: str) -> str:
        """
        Removes inline COBOL comments beginning with *>.
        This is a simple safe cleanup for scoring purposes.
        """
        if "*>" in line:
            return line.split("*>", 1)[0]
        return line

    def _mask_string_literals_preserving_call_targets(self, line_upper: str) -> str:
        """
        Masks string literals so keywords inside strings are not counted.

        Example:
            DISPLAY "CALL ABC" should not count as CALL.

        But:
            CALL 'PROG1' should still count as a CALL statement.

        So string literals immediately after CALL are replaced with __CALL_TARGET__.
        Other strings are blanked out.
        """

        def string_replacer(match: re.Match) -> str:
            full_match = match.group(0)
            start_index = match.start()
            prefix = line_upper[:start_index].strip()

            # Preserve literal CALL target:
            # CALL 'PROG1'
            # ON EXCEPTION CALL 'PROGRAM2'
            if re.search(r"(?<![A-Z0-9_-])CALL\s*$", prefix):
                return "__CALL_TARGET__"

            return " " * len(full_match)

        return re.sub(r"'.*?'|\".*?\"", string_replacer, line_upper)

    def _clean_code_logic(self, content: str):
        """
        Cleans COBOL code for scoring:
        1. Removes blank/comment lines.
        2. Removes inline comments.
        3. Uppercases code.
        4. Masks string literals, while preserving literal CALL targets.
        """
        processed_lines = []

        for line in content.splitlines():
            if self._is_comment_line(line):
                continue

            line = self._remove_inline_comment(line)
            if not line.strip():
                continue

            line_upper = line.upper()
            line_upper = self._mask_string_literals_preserving_call_targets(line_upper)
            processed_lines.append(line_upper)

        clean_code = "\n".join(processed_lines)
        code_line_count = max(len(processed_lines), 1)

        return clean_code, code_line_count

    def _count_call_statements(self, clean_code: str) -> int:
        """
        Counts real executable CALL statements.

        Counts:
            CALL 'PROG1'
            CALL "PROG1"
            CALL VALUE-2
            ON EXCEPTION CALL 'PROGRAM2'

        Does not count:
            END-CALL
            600-MAKE-CALL
            610-CALL-VALUE-IN-STRUCTURE
            DISPLAY "CALL PROG1"
        """
        pattern = r"(?<![A-Z0-9_-])CALL\s+(__CALL_TARGET__|[A-Z0-9#@$_-]+)"
        return len(re.findall(pattern, clean_code))

    def analyze(self, content: str) -> dict:
        clean_code, code_line_count = self._clean_code_logic(content)

        calculation = []
        score = 0

        # 1. CALL scoring.
        call_count = self._count_call_statements(clean_code)
        if call_count > 0:
            points = call_count * 2
            score += points
            calculation.append({
                "label": f"CALL ({call_count}x2)",
                "points": points
            })

        # 2. Other weighted indicators.
        indicator_counts = {}

        for label, pattern, weight in self.indicators:
            count = len(re.findall(pattern, clean_code))
            indicator_counts[label] = count

            if count > 0:
                points = count * weight
                score += points
                calculation.append({
                    "label": f"{label} ({count}x{weight})",
                    "points": points
                })

        # 3. Conditional bonuses.

        # PIC Density Bonus:
        # If more than 15% of non-comment code lines contain PIC.
        pic_count = len(re.findall(r"(?<![A-Z0-9_-])PIC\b", clean_code))
        if (pic_count / code_line_count) > 0.15:
            score += 3
            calculation.append({
                "label": "PIC Density Bonus",
                "points": 3
            })

        # Level Density Bonus:
        # Counts COBOL level numbers like 01, 05, 10, 77, 88.
        level_count = len(
            re.findall(
                r"^\s*(01|05|10|15|20|25|30|35|40|45|49|66|77|88)\s+",
                clean_code,
                re.MULTILINE
            )
        )

        if (level_count / code_line_count) > 0.20:
            score += 2
            calculation.append({
                "label": "Level Density Bonus",
                "points": 2
            })

        # COPY near WORKING-STORAGE or LINKAGE bonus.
        if re.search(
            r"(WORKING-STORAGE|LINKAGE)\s+SECTION[\s\S]{0,500}?(?<![A-Z0-9_-])COPY\b",
            clean_code
        ):
            score += 3
            calculation.append({
                "label": "Copybook Proximity Bonus",
                "points": 3
            })

        # Database interaction bonus.
        if re.search(r"(?<![A-Z0-9_-])EXEC\s+(SQL|DLI)\b", clean_code):
            score += 4
            calculation.append({
                "label": "Database Interaction Bonus",
                "points": 4
            })

        tier, mode, multiplier = self.get_tier_and_mode(score)

        return {
            "score": score,
            "tier": tier,
            "mode": mode,
            "multiplier": multiplier,
            "calculation": calculation,
            "debug": {
                "code_lines": code_line_count,
                "call_count": call_count,
                "pic_count": pic_count,
                "level_count": level_count,
                "indicator_counts": indicator_counts
            }
        }