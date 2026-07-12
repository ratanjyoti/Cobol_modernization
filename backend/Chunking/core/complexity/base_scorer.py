import re
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseComplexityScorer(ABC):
    @abstractmethod
    def analyze(self, content: str) -> Dict[str, Any]:
        pass

    def get_tier_and_mode(self, score: int):
        if score < 5:
            return "Low", "Turbo", 1.5
        if score <= 14:
            return "Medium", "Balanced", 2.5
        return "High", "Thorough", 3.5

    def _strip_string_literals(self, line: str) -> str:
        result = []
        quote = None
        index = 0
        while index < len(line):
            char = line[index]
            if quote:
                if char == quote:
                    quote = None
                result.append(" ")
            elif char in {"'", '"'}:
                quote = char
                result.append(" ")
            else:
                result.append(char)
            index += 1
        return "".join(result)

    def _remove_noise(self, content: str, comment_regex: str = None) -> str:
        cleaned_lines = []
        for line in content.splitlines():
            if comment_regex and re.search(comment_regex, line):
                continue
            cleaned_lines.append(self._strip_string_literals(line).upper())
        return "\n".join(cleaned_lines)
