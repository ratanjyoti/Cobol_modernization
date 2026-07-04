from abc import ABC, abstractmethod
from typing import List, Dict

class IDependencyScanner(ABC):
    @abstractmethod
    def scan(self, content: str) -> List[Dict[str, str]]:
        """
        Must return a list of dictionaries:
        [{ "target": "ITEM_NAME", "type": "RELATION_TYPE" }]
        """
        pass
