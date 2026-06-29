from abc import ABC, abstractmethod

class LLM_API_CLIENT(ABC):
    @abstractmethod
    def execute(self, data):
        pass
