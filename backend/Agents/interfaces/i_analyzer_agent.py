from abc import ABC, abstractmethod

class I_ANALYZER_AGENT(ABC):
    @abstractmethod
    def execute(self, data):
        pass
