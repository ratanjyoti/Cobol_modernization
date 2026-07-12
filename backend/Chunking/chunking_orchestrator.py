import json
from Chunking.core.sizing_router import SizingRouter
from Chunking.core.symbol_extractor import SymbolExtractor
from Chunking.core.semantic_unit_chunker import SemanticUnitChunker
from Persistence.sqlite.models import FileChunk, SignatureRegistry, TypeMappingTable


class ChunkingOrchestrator:
    def __init__(self, db_session):
        self.db = db_session
        self.extractor = SymbolExtractor(db_session)
        self.slicer = SemanticUnitChunker()

    def process_file(self, run_id: str, file_id: int, filename: str, content: str, lang: str):
        return self.process_file_pipeline(run_id, file_id, filename, content, lang)

    def process_file_pipeline(self, run_id: str, file_id: int, filename: str, content: str, lang: str):
        self._clear_existing(run_id, file_id)

        if not SizingRouter.needs_chunking(content):
            self.extractor.extract_and_lock(run_id, file_id, content, lang)
            self._store_single_chunk(run_id, file_id, content)
            return [0]

        self.extractor.extract_and_lock(run_id, file_id, content, lang)
        slices = self.slicer.slice_content(content, lang)

        for idx, chunk_slice in enumerate(slices):
            effective_content = chunk_slice["content"]
            if chunk_slice.get("overlap"):
                effective_content = chunk_slice["overlap"] + "\n" + effective_content
            chunk = FileChunk(
                run_id=run_id,
                file_id=file_id,
                chunk_index=idx,
                content=effective_content,
                start_line=chunk_slice["start"],
                end_line=chunk_slice["end"],
                overlap_content=chunk_slice["overlap"],
                semantic_units=json.dumps(chunk_slice.get("semantic_units", [])),
                status="PENDING",
            )
            self.db.add(chunk)

        self.db.commit()
        return list(range(len(slices)))

    def _store_single_chunk(self, run_id, file_id, content):
        chunk = FileChunk(
            run_id=run_id,
            file_id=file_id,
            chunk_index=0,
            content=content,
            start_line=1,
            end_line=content.count("\n") + (1 if content else 0),
            overlap_content="",
            semantic_units=json.dumps(["file:FILE"]),
            status="PENDING",
        )
        self.db.add(chunk)
        self.db.commit()

    def _clear_existing(self, run_id: str, file_id: int):
        self.db.query(FileChunk).filter_by(run_id=run_id, file_id=file_id).delete(synchronize_session=False)
        self.db.query(TypeMappingTable).filter_by(run_id=run_id, file_id=file_id).delete(synchronize_session=False)
        self.db.query(SignatureRegistry).filter_by(run_id=run_id, file_id=file_id).delete(synchronize_session=False)
        self.db.flush()

