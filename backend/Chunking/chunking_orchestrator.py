# Implementation for chunking_orchestrator.py
from Chunking.core.sizing_router import SizingRouter
from Chunking.interfaces.cobol_chunker import CobolChunker
from Chunking.interfaces.jcl_chunker import JclChunker
from Chunking.interfaces.telon_chunker import TelonChunker
from Persistence.sqlite.models import FileChunk

class ChunkingOrchestrator:
    def __init__(self, db_session):
        self.db = db_session
        self.chunkers = {
            "COBOL": CobolChunker(),
            "JCL": JclChunker(),
            "TELON": TelonChunker()
        }

    def process_file(self, run_id: str, file_id: int, filename: str, content: str, lang: str):
        # 1. Check if chunking is even needed
        if not SizingRouter.needs_chunking(content):
            # Store as a single chunk
            chunk = FileChunk(
                run_id=run_id,
                file_id=file_id,
                chunk_index=0,
                content=content,
                start_line=1,
                end_line=len(content.splitlines()),
                overlap_content=""
            )
            self.db.add(chunk)
            self.db.commit()
            return [0] # Single chunk index

        # 2. Select the correct language adapter
        chunker = self.chunkers.get(lang.upper())
        if not chunker:
            # Fallback to COBOL if unknown but needs chunking
            chunker = CobolChunker()

        # 3. Perform the semantic slice
        slices = chunker.split_code(content)

        # 4. Store each slice in SQLite
        for idx, (start, end, text, overlap) in enumerate(slices):
            chunk = FileChunk(
                run_id=run_id,
                file_id=file_id,
                chunk_index=idx,
                content=text,
                start_line=start,
                end_line=end,
                overlap_content=overlap
            )
            self.db.add(chunk)
        
        self.db.commit()
        return list(range(len(slices)))
