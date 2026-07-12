from abc import ABC, abstractmethod


class ILanguageAdapter(ABC):
    def preprocess(self, content: str) -> str:
        return content

    def identify_structure(self, content: str) -> list[dict]:
        lines = content.splitlines()
        return [{
            "name": "FILE",
            "kind": "file",
            "start_line": 1,
            "end_line": len(lines),
        }] if lines else []

    @property
    @abstractmethod
    def language_name(self) -> str:
        pass
