from abc import ABC, abstractmethod

class I_CHUNKER(ABC):
    @abstractmethod
    def execute(self, data):
        pass
