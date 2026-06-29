from abc import ABC, abstractmethod

class I_EXTRACTOR_AGENT(ABC):
    @abstractmethod
    def execute(self, data):
        pass
