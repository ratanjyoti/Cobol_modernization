import re
from Chunking.interfaces.i_chunker import IChunker

class CobolChunker(IChunker):
    def __init__(self, max_lines=1500, overlap=300):
        self.max_lines = max_lines
        self.overlap = overlap

    def split_code(self, content: str):
        lines = content.splitlines()
        chunks = []
        start = 0
        
        while start < len(lines):
            end = min(start + self.max_lines, len(lines))
            
            if end < len(lines):
                # Try to find a natural boundary in the last 200 lines of the chunk
                # Priority: Division > Section > Paragraph
                best_break = self._find_best_boundary(lines, start, end)
                if best_break != -1:
                    end = best_break

            # Extract content and overlap
            chunk_text = "\n".join(lines[start:end])
            
            # Calculate overlap from previous chunk
            overlap_start = max(0, start - self.overlap)
            overlap_text = "\n".join(lines[overlap_start:start])

            chunks.append((start + 1, end, chunk_text, overlap_text))
            start = end

        return chunks

    def _find_best_boundary(self, lines, start, end):
        # Look backwards from the 'end' for the best boundary
        # We search in a window to avoid making chunks too small
        search_window = lines[max(start, end-500):end]
        
        # 1. High Priority: Divisions
        for i in range(len(search_window)-1, -1, -1):
            if re.search(r"(IDENTIFICATION|ENVIRONMENT|DATA|PROCEDURE)\s+DIVISION", search_window[i], re.I):
                return max(start, end - (len(search_window) - i))

        # 2. Medium Priority: Sections
        for i in range(len(search_window)-1, -1, -1):
            if "SECTION" in search_window[i].upper():
                return max(start, end - (len(search_window) - i))

        # 3. Low Priority: Paragraphs (Looking for names ending with a dot)
        for i in range(len(search_window)-1, -1, -1):
            if re.match(r"^\s*[A-Z0-9-]+\.", search_window[i], re.I):
                return max(start, end - (len(search_window) - i))

        return -1 # No natural boundary found, do a hard cut
