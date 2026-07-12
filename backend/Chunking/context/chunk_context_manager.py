import re
from Persistence.sqlite.models import FileChunk, SignatureRegistry, TypeMappingTable


class ChunkContextManager:
    CALL_RE = re.compile(r"\b(?:PERFORM|CALL)\s+['\"]?([A-Z0-9_-]+)", re.I)

    def __init__(self, db_session):
        self.db = db_session

    def build_context_for_chunk(self, run_id: str, file_id: int, chunk_index: int):
        current_chunk = self.db.query(FileChunk).filter_by(
            run_id=run_id,
            file_id=file_id,
            chunk_index=chunk_index,
        ).first()

        types = self.db.query(TypeMappingTable).filter_by(run_id=run_id, file_id=file_id).all()
        signatures = self.db.query(SignatureRegistry).filter_by(run_id=run_id, file_id=file_id).all()

        type_context = "\n".join(
            f"{t.legacy_variable} -> {t.target_field_name} ({t.target_type})"
            for t in types
        )
        sig_context = "\n".join(
            f"{s.legacy_name} -> {s.target_method_name} :: {s.target_signature or ''}".strip()
            for s in signatures
        )

        recent_chunks = self.db.query(FileChunk).filter(
            FileChunk.run_id == run_id,
            FileChunk.file_id == file_id,
            FileChunk.chunk_index < chunk_index,
        ).order_by(FileChunk.chunk_index.desc()).limit(3).all()
        full_history = "\n\n".join(
            c.converted_code or ""
            for c in sorted(recent_chunks, key=lambda item: item.chunk_index)
            if c.converted_code
        )

        old_chunks = self.db.query(FileChunk).filter(
            FileChunk.run_id == run_id,
            FileChunk.file_id == file_id,
            FileChunk.chunk_index < max(0, chunk_index - 3),
        ).order_by(FileChunk.chunk_index.asc()).all()
        compressed_history = "\n".join(
            f"Chunk {c.chunk_index}: {c.summary}"
            for c in old_chunks
            if c.summary
        )

        forward_refs = self._detect_forward_references(current_chunk, signatures, chunk_index)

        return {
            "global_types": type_context,
            "global_signatures": sig_context,
            "recent_code": full_history,
            "summary_history": compressed_history,
            "forward_references": forward_refs,
            "current_cobol_chunk": current_chunk.content if current_chunk else "",
            "current_chunk_index": chunk_index,
            "prompt": self.assemble_prompt(type_context, sig_context, compressed_history, full_history, forward_refs, current_chunk.content if current_chunk else ""),
        }

    def _detect_forward_references(self, chunk: FileChunk | None, signatures: list[SignatureRegistry], chunk_index: int) -> list[str]:
        if not chunk:
            return []
        registry = {sig.legacy_name.upper(): sig for sig in signatures}
        pending = []
        for target in self.CALL_RE.findall(chunk.content or ""):
            key = target.strip().rstrip(".").upper()
            signature = registry.get(key)
            if signature and (
                signature.converted_chunk_index is None
                or signature.converted_chunk_index > chunk_index
            ):
                pending.append(f"Paragraph {key} is called here but will be converted in a later chunk.")
        return sorted(set(pending))

    @staticmethod
    def assemble_prompt(global_types: str, global_signatures: str, compressed_history: str, recent_code: str, forward_refs: list[str], current_chunk: str) -> str:
        return "\n\n".join([
            "[Global Types]\n" + (global_types or "None"),
            "[Global Signatures]\n" + (global_signatures or "None"),
            "[Compressed History]\n" + (compressed_history or "None"),
            "[Full Recent Code]\n" + (recent_code or "None"),
            "[Forward Refs]\n" + ("\n".join(forward_refs) if forward_refs else "None"),
            "[Current COBOL Chunk]\n" + (current_chunk or ""),
        ])

    def record_result(self, run_id, file_id, chunk_index, code, summary, tokens, processing_time=0, status="COMPLETED"):
        chunk = self.db.query(FileChunk).filter_by(
            run_id=run_id,
            file_id=file_id,
            chunk_index=chunk_index,
        ).first()
        if not chunk:
            return None
        chunk.converted_code = code
        chunk.summary = summary
        chunk.tokens_used = tokens or 0
        chunk.processing_time = processing_time or 0
        chunk.status = status
        self._mark_signatures_converted(run_id, file_id, chunk_index, code or "")
        self.db.commit()
        return chunk

    def record_failure(self, run_id, file_id, chunk_index, error_message):
        chunk = self.db.query(FileChunk).filter_by(
            run_id=run_id,
            file_id=file_id,
            chunk_index=chunk_index,
        ).first()
        if chunk:
            chunk.status = "FAILED"
            chunk.error_message = str(error_message)
            self.db.commit()
        return chunk

    def _mark_signatures_converted(self, run_id: str, file_id: int, chunk_index: int, code: str):
        signatures = self.db.query(SignatureRegistry).filter_by(run_id=run_id, file_id=file_id).all()
        for signature in signatures:
            method = signature.target_method_name
            if method and re.search(rf"\b{re.escape(method)}\s*\(", code):
                signature.converted_chunk_index = chunk_index
