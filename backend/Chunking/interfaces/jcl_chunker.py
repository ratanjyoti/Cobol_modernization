import re
from Chunking.interfaces.i_chunker import IChunker

class JclChunker(IChunker):
    def split_code(self, content: str):
        lines = content.splitlines()
        chunks = []
        start = 0
        
        while start < len(lines):
            end = min(start + 1500, len(lines))
            if end < len(lines):
                # Look for //JOB or //EXEC
                for i in range(end-1, max(start, end-500), -1):
                    if lines[i].startswith("//JOB") or lines[i].startswith("//EXEC"):
                        end = i
                        break
            
            chunk_text = "\n".join(lines[start:end])
            overlap_text = "\n".join(lines[max(0, start-300):start])
            chunks.append((start + 1, end, chunk_text, overlap_text))
            start = end
        return chunks
