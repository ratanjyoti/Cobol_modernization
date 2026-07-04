from abc import ABC, abstractmethod
from typing import List, Tuple

class IChunker(ABC):
    @abstractmethod
    def split_code(self, content: str) -> List[Tuple[int, int, str, str]]:
        """
        Returns tuples of: (start_line, end_line, chunk_content, overlap_content)
        """
        pass

