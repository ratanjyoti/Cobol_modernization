from abc import ABC, abstractmethod

class I_REPOSITORY(ABC):
    @abstractmethod
    def execute(self, data):
        pass
