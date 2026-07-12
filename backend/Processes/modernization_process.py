import asyncio
import time
from Persistence.sqlite.models import FileChunk
from Agents.implementations.java_converter_agent import JavaConverterAgent, ReasoningExhaustionError
from Chunking.context.chunk_context_manager import ChunkContextManager
from Chunking.core.settings import ChunkingSettings
from Chunking.execution.rate_limiter import RateLimiter
from Chunking.execution.response_parser import ConversionResponseParser


class ModernizationProcess:
    def __init__(self, db_session, llm_provider=None):
        self.db = db_session
        self.context_mgr = ChunkContextManager(db_session)
        self.rate_limiter = RateLimiter()
        self.agent = JavaConverterAgent()
        self.settings = ChunkingSettings()
        self.semaphore = asyncio.Semaphore(self.settings.max_parallel_chunks)

    async def convert_file(self, run_id, file_id):
        chunks = self.db.query(FileChunk).filter_by(
            run_id=run_id,
            file_id=file_id,
        ).order_by(FileChunk.chunk_index).all()
        await asyncio.gather(*(self.process_single_chunk(run_id, file_id, chunk) for chunk in chunks))

    async def process_single_chunk(self, run_id, file_id, chunk):
        async with self.semaphore:
            started = time.monotonic()
            context = self.context_mgr.build_context_for_chunk(run_id, file_id, chunk.chunk_index)
            estimated_tokens = max(2000, (len(chunk.content or "") + len(context.get("prompt", ""))) // 4)
            await self.rate_limiter.acquire_tokens(estimated_tokens)

            try:
                result = await self._convert_with_backoff(chunk, context)
                parsed = ConversionResponseParser.parse(result)
                self.context_mgr.record_result(
                    run_id,
                    file_id,
                    chunk.chunk_index,
                    parsed["code"],
                    parsed["summary"],
                    parsed["tokens"] or estimated_tokens,
                    processing_time=time.monotonic() - started,
                )
            except ReasoningExhaustionError as exc:
                await self._adaptive_rechunk_and_retry(run_id, file_id, chunk, exc)
            except Exception as exc:
                self.context_mgr.record_failure(run_id, file_id, chunk.chunk_index, exc)

    async def _convert_with_backoff(self, chunk, context):
        delay = 5
        for attempt in range(4):
            try:
                return await self.agent.convert(chunk.content, context)
            except Exception as exc:
                if self._is_rate_limit_error(exc) and attempt < 3:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                if self._is_reasoning_exhaustion(exc):
                    raise ReasoningExhaustionError(str(exc)) from exc
                raise

    @staticmethod
    def _is_rate_limit_error(exc: Exception) -> bool:
        status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
        response = getattr(exc, "response", None)
        response_status = getattr(response, "status_code", None) if response is not None else None
        return status == 429 or response_status == 429 or "429" in str(exc)

    @staticmethod
    def _is_reasoning_exhaustion(exc: Exception) -> bool:
        message = str(exc).lower()
        return "reasoning exhaustion" in message or "ran out of tokens" in message or "context length" in message

    async def _adaptive_rechunk_and_retry(self, run_id, file_id, chunk, exc):
        lines = (chunk.content or "").splitlines()
        if len(lines) < 4:
            self.context_mgr.record_failure(run_id, file_id, chunk.chunk_index, exc)
            return

        chunk.status = "RECHUNKED"
        chunk.error_message = str(exc)
        max_index = self.db.query(FileChunk).filter_by(run_id=run_id, file_id=file_id).count()
        midpoint = len(lines) // 2
        fragments = [lines[:midpoint], lines[max(0, midpoint - self.settings.overlap_lines):]]
        new_chunks = []
        for offset, fragment_lines in enumerate(fragments):
            new_chunk = FileChunk(
                run_id=run_id,
                file_id=file_id,
                chunk_index=max_index + offset,
                content="\n".join(fragment_lines),
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                overlap_content="",
                semantic_units=chunk.semantic_units,
                status="PENDING",
            )
            self.db.add(new_chunk)
            new_chunks.append(new_chunk)
        self.db.commit()

        for new_chunk in new_chunks:
            await self.process_single_chunk(run_id, file_id, new_chunk)
