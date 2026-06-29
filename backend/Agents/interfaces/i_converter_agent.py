from abc import ABC, abstractmethod

class I_CONVERTER_AGENT(ABC):
    @abstractmethod
    def execute(self, data):
        pass
