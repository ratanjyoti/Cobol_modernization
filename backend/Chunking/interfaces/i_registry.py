from abc import ABC, abstractmethod

class I_REGISTRY(ABC):
    @abstractmethod
    def execute(self, data):
        pass
