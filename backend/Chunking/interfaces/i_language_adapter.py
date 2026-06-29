from abc import ABC, abstractmethod

class ILanguageAdapter(ABC):
    @abstractmethod
    def detect(self, content: str) -> bool:
        """Returns True if the content matches this language's signatures."""
        pass

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Returns the name of the language (e.g., 'COBOL')."""
        pass
