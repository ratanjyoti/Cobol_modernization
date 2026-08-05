import os
# Owns business logic extraction process orchestration and persistence. Do not put language-specific prompt text here.
import hashlib
import re
from typing import Any
import json
from sqlalchemy.orm import Session
from Chunking.chunking_orchestrator import ChunkingOrchestrator
from Chunking.context.chunk_context_manager import ChunkContextManager
from Persistence.sqlite.models import BusinessRule, ChunkAnalysis, FileChunk, FileRelation, FileStatus, ProjectFile
from paths import UPLOADS_DIR
from Agents.infrastructure.chat_client_factory import ChatClientFactory

from pathlib import Path

from Agents.implementations.agentic_business_logic_extractor import (
    AgenticBusinessLogicExtractor,
    BusinessLogicFileContext,
)
from services.business_logic_chunk_context_service import (
    BusinessLogicChunkSource,
    build_chunk_source,
    chunk_diagnostics,
    format_chunk_for_prompt,
    split_chunk_source_for_prompt_budget,
)
from services.business_logic_reconciler import BusinessLogicReconciler
from services.business_rule_quality_service import BusinessRuleQualityService
from services.legacy_source_preprocessor import LegacySourcePreprocessor

class LogicExtractionProcess:
    """
    Runs agentic business-rule extraction across supported legacy files.

    The process loads chunks and database context, while the LangGraph
    orchestrator selects the correct language prompt, performs technical
    analysis, extracts rules, validates the output and repairs invalid output.
    """

    LOGIC_RE = re.compile(
        r"\b("
        r"IF|EVALUATE|COMPUTE|ADD|SUBTRACT|MULTIPLY|DIVIDE|"
        r"CALL|EXEC\s+SQL|PERFORM|READ|WRITE|REWRITE|DELETE|"
        r"START|ACCEPT|DISPLAY|OPEN|CLOSE"
        r")\b",
        re.IGNORECASE,
    )
    EXTRACTOR_VERSION = "business-logic-v2"
    PROMPT_VERSION = "cobol-business-v3"
    TECHNICAL_ANALYSIS_VERSION = "technical-structure-v2"

    def __init__(
        self,
        db_session: Session,
        llm_provider: str | dict,
        api_key: str | None = None,
    ):
        self.db = db_session
        self.context_mgr = ChunkContextManager(db_session)
        self.preprocessor = LegacySourcePreprocessor()
        self.quality_service = BusinessRuleQualityService()
        self.reconciler = BusinessLogicReconciler()
        self.max_input_tokens = int(os.getenv("BUSINESS_LOGIC_MAX_INPUT_TOKENS", "5500"))

        self.config = (
            llm_provider
            if isinstance(llm_provider, dict)
            else {
                "mode": llm_provider,
                "provider": llm_provider,
                "key": api_key,
            }
        )

        self.llm_provider = (
            self.config.get("mode")
            or self.config.get("provider")
            or "local"
        ).lower()

        self.max_llm_chunks = int(
            os.getenv("OPENROUTER_MAX_RULE_CHUNKS", "12")
        )

        try:
            self.llm_client = ChatClientFactory.get_client(
                self.config
            )
        except Exception as exc:
            print(
                "Cloud/API client unavailable; "
                f"using local fallback: {exc}"
            )

            self.llm_provider = "local"

            self.llm_client = ChatClientFactory.get_client(
                {
                    "mode": "local",
                    "provider": "local",
                }
            )

    async def extract_all_rules(self, run_id: str, force: bool = False) -> dict:
        from Persistence.sqlite.models import Project, ProjectFile

        project = self.db.query(Project).filter_by(run_id=run_id).first()

        if not project:
            raise ValueError(f"Project not found for run_id={run_id}")

        extractor = self._build_agentic_extractor(project)

        files = [
            project_file
            for project_file in self.db.query(ProjectFile).filter(ProjectFile.run_id == run_id).all()
            if self._is_detected_or_confirmed(project_file)
        ]

        total = len(files)
        completed = 0
        cached = 0
        stale = 0
        failed = 0
        results = []
        processed = 0

        self._write_extraction_status(
            run_id,
            status="RUNNING",
            stage="Preparing business logic extraction",
            progress=1 if total else 100,
            total_files=total,
            completed_files=0,
            cached_files=0,
            stale_files=0,
            failed_files=0,
            processed_files=0,
            force=force,
        )

        for file_position, project_file in enumerate(files, start=1):
            try:
                source_code = self._load_source_code_for_file(project_file)
                source_hash = self._source_hash(source_code)
                source_profile = self.preprocessor.prepare(
                    source_code=source_code,
                    file_name=project_file.filename or project_file.filepath or "",
                    detected_language=getattr(project_file, "detected_lang", "") or "",
                )
                existing_rules_count = (
                    self.db.query(BusinessRule)
                    .filter(
                        BusinessRule.run_id == run_id,
                        BusinessRule.file_id == project_file.id,
                    )
                    .count()
                )

                cache_status = "new"
                self._write_extraction_status(
                    run_id,
                    status="RUNNING",
                    stage=f"Checking saved business rules for {project_file.filename}",
                    progress=self._file_progress(total, processed),
                    total_files=total,
                    completed_files=completed,
                    cached_files=cached,
                    stale_files=stale,
                    failed_files=failed,
                    processed_files=processed,
                    current_file_id=project_file.id,
                    current_file_name=project_file.filename,
                    current_file_index=file_position,
                    force=force,
                )
                if existing_rules_count and not force:
                    cached_entry = self._cached_metadata(run_id, project_file.id)
                    cache_status = self._cache_status(cached_entry, source_hash)
                    if cache_status != "fresh":
                        stale += 1
                        print(
                            f"Business Logic cache stale for run={run_id} file={project_file.id}: "
                            f"{cache_status}; preserving old rows until new result is reconciled."
                        )
                    else:
                        cached += 1
                        processed += 1
                        results.append(
                            {
                                **cached_entry,
                                "file_id": project_file.id,
                                "file_name": project_file.filename,
                                "detected_language": source_profile.detected_language,
                                "artifact_type": source_profile.artifact_type,
                                "file_role": source_profile.file_role,
                                "business_rules_count": existing_rules_count,
                                "status": "cached",
                                "cache_status": "fresh",
                                "source_hash": source_hash,
                                "extractor_version": self.EXTRACTOR_VERSION,
                                "prompt_version": self.PROMPT_VERSION,
                                "technical_analysis_version": self.TECHNICAL_ANALYSIS_VERSION,
                            }
                        )
                        self._write_extraction_status(
                            run_id,
                            status="RUNNING",
                            stage=f"Loaded saved business rules for {project_file.filename}",
                            progress=self._file_progress(total, processed),
                            total_files=total,
                            completed_files=completed,
                            cached_files=cached,
                            stale_files=stale,
                            failed_files=failed,
                            processed_files=processed,
                            current_file_id=project_file.id,
                            current_file_name=project_file.filename,
                            current_file_index=file_position,
                            force=force,
                        )
                        continue

                if existing_rules_count and force:
                    (
                        self.db.query(BusinessRule)
                        .filter(
                            BusinessRule.run_id == run_id,
                            BusinessRule.file_id == project_file.id,
                        )
                        .delete(synchronize_session=False)
                    )
                    self.db.commit()
                    self._clear_business_logic_chunk_outputs(run_id, project_file.id)

                if not self._is_legacy_source_chunk(project_file, source_profile.source_code):
                    results.append(
                        {
                            "file_id": project_file.id,
                            "file_name": project_file.filename,
                            "detected_language": source_profile.detected_language,
                            "artifact_type": source_profile.artifact_type,
                            "file_role": source_profile.file_role,
                            "status": "skipped",
                            "reason": "unsupported_or_empty_source",
                        }
                    )
                    processed += 1
                    continue

                dependency_context = self._build_dependency_context_for_file(
                    run_id=run_id,
                    file_id=project_file.id,
                )

                glossary_context = self._build_glossary_context(run_id)

                result = self._extract_file_from_stored_chunks(
                    run_id=run_id,
                    project_file=project_file,
                    source_profile=source_profile,
                    source_hash=source_hash,
                    extractor=extractor,
                    dependency_context=dependency_context,
                    glossary_context=glossary_context,
                    total_files=total,
                    processed_files=processed,
                    file_position=file_position,
                )
                result["source_hash"] = source_hash
                result["extractor_version"] = self.EXTRACTOR_VERSION
                result["prompt_version"] = self.PROMPT_VERSION
                result["technical_analysis_version"] = self.TECHNICAL_ANALYSIS_VERSION

                self._replace_business_rules_for_file(
                    run_id=run_id,
                    project_file=project_file,
                    result=result,
                )

                completed += 1
                processed += 1
                results.append(
                    {
                        "file_id": project_file.id,
                        "file_name": result.get("file_name") or project_file.filename,
                        "detected_language": result.get("detected_language") or source_profile.detected_language,
                        "artifact_type": result.get("artifact_type") or source_profile.artifact_type,
                        "file_role": result.get("file_role") or source_profile.file_role,
                        "selected_agent": result.get("selected_agent") or result.get("agent_name"),
                        "agent_name": result.get("agent_name"),
                        "agent_key": result.get("agent_key"),
                        "extraction_mode": result.get("extraction_mode"),
                        "processing_mode": result.get("processing_mode"),
                        "llm_called": result.get("llm_called", False),
                        "fallback_used": result.get("fallback_used", False),
                        "fallback_reason": result.get("fallback_reason", ""),
                        "model": result.get("model"),
                        "source_character_count": result.get("source_character_count"),
                        "source_hash": source_hash,
                        "cache_status": cache_status,
                        "extractor_version": self.EXTRACTOR_VERSION,
                        "prompt_version": self.PROMPT_VERSION,
                        "technical_analysis_version": self.TECHNICAL_ANALYSIS_VERSION,
                        "coverage": result.get("coverage") or {},
                        "chunk_execution": result.get("chunk_execution") or {},
                        "business_rules_count": len(result.get("business_rules") or []),
                        "status": "completed",
                    }
                )
                self._write_extraction_status(
                    run_id,
                    status="RUNNING",
                    stage=f"Completed business rules for {project_file.filename}",
                    progress=self._file_progress(total, processed),
                    total_files=total,
                    completed_files=completed,
                    cached_files=cached,
                    stale_files=stale,
                    failed_files=failed,
                    processed_files=processed,
                    current_file_id=project_file.id,
                    current_file_name=project_file.filename,
                    current_file_index=file_position,
                    force=force,
                )

            except Exception as exc:
                failed += 1
                processed += 1
                results.append(
                    {
                        "file_id": getattr(project_file, "id", None),
                        "file_name": getattr(project_file, "filename", ""),
                        "detected_language": getattr(project_file, "detected_language", ""),
                        "status": "failed",
                        "error": str(exc),
                    }
                )
                self._write_extraction_status(
                    run_id,
                    status="RUNNING",
                    stage=f"Failed extracting {getattr(project_file, 'filename', 'source file')}",
                    progress=self._file_progress(total, processed),
                    total_files=total,
                    completed_files=completed,
                    cached_files=cached,
                    stale_files=stale,
                    failed_files=failed,
                    processed_files=processed,
                    current_file_id=getattr(project_file, "id", None),
                    current_file_name=getattr(project_file, "filename", ""),
                    current_file_index=file_position,
                    error=str(exc),
                    force=force,
                )

        summary = {
            "run_id": run_id,
            "total_files": total,
            "completed_files": completed,
            "cached_files": cached,
            "stale_files": stale,
            "failed_files": failed,
            "results": results,
        }
        self._write_extraction_summary(run_id, summary)
        self._write_extraction_status(
            run_id,
            status="FAILED" if failed and not (completed or cached) else "COMPLETED",
            stage="Business logic extraction finished",
            progress=100,
            total_files=total,
            completed_files=completed,
            cached_files=cached,
            stale_files=stale,
            failed_files=failed,
            processed_files=processed,
            force=force,
        )
        return summary

    def extraction_status(self, run_id: str) -> dict[str, Any]:
        return self.extraction_status_for_run(run_id)

    @classmethod
    def extraction_status_for_run(cls, run_id: str) -> dict[str, Any]:
        path = cls._status_path(run_id)
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    payload.setdefault("run_id", run_id)
                    return payload
            except Exception:
                pass

        summary_path = cls._summary_path(run_id)
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
            if not isinstance(summary, dict):
                summary = {}
        except Exception:
            summary = {}
        if summary.get("results"):
            return {
                "run_id": run_id,
                "status": "COMPLETED",
                "stage": "Saved business rules loaded.",
                "progress": 100,
                "total_files": summary.get("total_files", 0),
                "completed_files": summary.get("completed_files", 0),
                "cached_files": summary.get("cached_files", 0),
                "stale_files": summary.get("stale_files", 0),
                "failed_files": summary.get("failed_files", 0),
                "processed_files": (
                    int(summary.get("completed_files") or 0)
                    + int(summary.get("cached_files") or 0)
                    + int(summary.get("failed_files") or 0)
                ),
            }

        return {
            "run_id": run_id,
            "status": "NOT_STARTED",
            "stage": "Business logic extraction has not started.",
            "progress": 0,
            "total_files": 0,
            "completed_files": 0,
            "cached_files": 0,
            "stale_files": 0,
            "failed_files": 0,
            "processed_files": 0,
        }

    def extraction_summary(self, run_id: str) -> dict[str, Any]:
        path = self._summary_path(run_id)
        if not path.exists():
            return {"run_id": run_id, "results": []}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        return {"run_id": run_id, "results": []}

    def _write_extraction_summary(self, run_id: str, payload: dict[str, Any]) -> None:
        path = self._summary_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _summary_path(run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "business_logic" / run_id / "summary.json"

    @staticmethod
    def _status_path(run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "business_logic" / run_id / "status.json"

    def _write_extraction_status(
        self,
        run_id: str,
        *,
        status: str,
        stage: str,
        progress: int | float,
        **extra: Any,
    ) -> None:
        payload = {
            "run_id": run_id,
            "status": status,
            "stage": stage,
            "progress": max(0, min(100, int(round(float(progress))))),
            **extra,
        }
        path = self._status_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _file_progress(total_files: int, processed_files: int, current_file_fraction: float = 0.0) -> int:
        if total_files <= 0:
            return 100
        bounded_fraction = max(0.0, min(1.0, current_file_fraction))
        return int(round(((processed_files + bounded_fraction) / total_files) * 100))

    def _cached_metadata(self, run_id: str, file_id: int | str) -> dict[str, Any]:
        summary = self.extraction_summary(run_id)
        for item in summary.get("results") or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("file_id")) == str(file_id):
                return dict(item)
        return {}

    def _cache_status(self, cached_entry: dict[str, Any], source_hash: str) -> str:
        if not cached_entry:
            return "missing_metadata"
        if cached_entry.get("source_hash") != source_hash:
            return "source_changed"
        if cached_entry.get("extractor_version") != self.EXTRACTOR_VERSION:
            return "extractor_version_changed"
        if cached_entry.get("prompt_version") != self.PROMPT_VERSION:
            return "prompt_version_changed"
        if cached_entry.get("technical_analysis_version") != self.TECHNICAL_ANALYSIS_VERSION:
            return "technical_analysis_version_changed"
        return "fresh"

    @staticmethod
    def _source_hash(source_code: str) -> str:
        digest = hashlib.sha256((source_code or "").encode("utf-8", errors="ignore")).hexdigest()
        return f"sha256:{digest}"

    def _extract_file_from_stored_chunks(
        self,
        *,
        run_id: str,
        project_file,
        source_profile: Any,
        source_hash: str,
        extractor: AgenticBusinessLogicExtractor,
        dependency_context: str,
        glossary_context: str,
        total_files: int,
        processed_files: int,
        file_position: int,
    ) -> dict[str, Any]:
        chunks = self._load_or_create_chunks_for_file(
            run_id=run_id,
            file_id=project_file.id,
            file_name=project_file.filename or project_file.filepath or "",
            source_code=source_profile.source_code,
            language=source_profile.detected_language,
        )
        diagnostics = chunk_diagnostics(chunks)
        print(f"Existing chunks found: {len(chunks)} for run={run_id} file={project_file.id}")
        print("Reusing stored FileChunk records")
        for item in diagnostics:
            print(
                "BL chunk file={file_id} index={chunk_index} primary={primary_start_line}-{primary_end_line} "
                "total_lines={total_lines} overlap_lines={overlap_lines} chars={chars} units={semantic_units}".format(
                    file_id=project_file.id,
                    **item,
                )
            )

        chunk_results: list[dict[str, Any]] = []
        stored_chunks = len(chunks)
        request_batches = 0
        llm_chunks = 0
        fallback_chunks = 0
        failed_chunks = 0
        overlap_lines = 0
        chunk_jobs: list[tuple[BusinessLogicChunkSource, str]] = []

        for chunk in chunks:
            chunk_source = self._normalized_chunk_source(build_chunk_source(chunk))
            overlap_lines += len((chunk_source.overlap_source or "").splitlines())
            chunk_yaml = self._load_technical_yaml_for_chunk(run_id, chunk)
            if not chunk_yaml.strip():
                chunk_profile = self.preprocessor.prepare(
                    chunk_source.primary_source,
                    file_name=project_file.filename or project_file.filepath or "",
                    detected_language=source_profile.detected_language,
                )
                chunk_yaml = self.preprocessor.to_technical_yaml(chunk_profile)

            batches = self._request_batches_for_chunk(
                chunk_source=chunk_source,
                technical_yaml=chunk_yaml,
                dependency_context=dependency_context,
                glossary_context=glossary_context,
            )
            for batch in batches:
                chunk_jobs.append((batch, chunk_yaml))

        request_batches = len(chunk_jobs)
        self._write_extraction_status(
            run_id,
            status="RUNNING",
            stage=f"Prepared {request_batches} extraction batch(es) for {project_file.filename}",
            progress=self._file_progress(total_files, processed_files, 0.05),
            total_files=total_files,
            processed_files=processed_files,
            current_file_id=project_file.id,
            current_file_name=project_file.filename,
            current_file_index=file_position,
            stored_chunks=stored_chunks,
            request_batches=request_batches,
            completed_batches=0,
            current_batch_index=0,
        )

        for batch_number, (batch, chunk_yaml) in enumerate(chunk_jobs, start=1):
                print(
                    f"Chunk {batch.chunk_index}/{stored_chunks} primary lines "
                    f"{batch.primary_start_line}-{batch.primary_end_line} "
                    f"overlap {len((batch.overlap_source or '').splitlines())}"
                )
                self._write_extraction_status(
                    run_id,
                    status="RUNNING",
                    stage=(
                        f"Extracting {project_file.filename}: batch {batch_number} of {request_batches} "
                        f"(lines {batch.primary_start_line}-{batch.primary_end_line})"
                    ),
                    progress=self._file_progress(
                        total_files,
                        processed_files,
                        (batch_number - 1) / request_batches if request_batches else 0.0,
                    ),
                    total_files=total_files,
                    processed_files=processed_files,
                    current_file_id=project_file.id,
                    current_file_name=project_file.filename,
                    current_file_index=file_position,
                    stored_chunks=stored_chunks,
                    request_batches=request_batches,
                    completed_batches=batch_number - 1,
                    current_batch_index=batch_number,
                    current_chunk_index=batch.chunk_index,
                    primary_start_line=batch.primary_start_line,
                    primary_end_line=batch.primary_end_line,
                    semantic_units=batch.semantic_units,
                )
                formatted_source = format_chunk_for_prompt(batch)
                chunk_profile = self.preprocessor.prepare(
                    batch.primary_source,
                    file_name=project_file.filename or project_file.filepath or "",
                    detected_language=source_profile.detected_language,
                )
                context = self._build_business_file_context(
                    project_file=project_file,
                    technical_yaml=self._chunk_prompt_yaml(
                        chunk_yaml=chunk_yaml,
                        batch=batch,
                        source_profile=source_profile,
                    ),
                    source_code=formatted_source,
                    dependency_context=dependency_context,
                    glossary_context=glossary_context,
                    source_profile=chunk_profile,
                )
                context.artifact_type = source_profile.artifact_type
                context.file_role = source_profile.file_role
                context.source_character_count = source_profile.source_character_count
                context.primary_start_line = batch.primary_start_line
                context.primary_end_line = batch.primary_end_line
                context.semantic_units = batch.semantic_units

                try:
                    chunk_result = extractor.extract_chunk(
                        context,
                        chunk_index=batch.chunk_index,
                        total_chunks=request_batches,
                        primary_start_line=batch.primary_start_line,
                        primary_end_line=batch.primary_end_line,
                        semantic_units=batch.semantic_units,
                    )
                    accepted_rules, rejected_rules = self.quality_service.filter_rules_for_primary_range(
                        chunk_result.get("business_rules") or [],
                        batch.primary_start_line,
                        batch.primary_end_line,
                    )
                    chunk_result["business_rules"] = accepted_rules
                    chunk_result["warnings"] = rejected_rules
                    chunk_result["status"] = "COMPLETED"
                    if chunk_result.get("llm_called"):
                        llm_chunks += 1
                    if chunk_result.get("fallback_used"):
                        fallback_chunks += 1
                    self._write_chunk_result(run_id, project_file.id, batch.chunk_index, chunk_result)
                    chunk_results.append(chunk_result)
                    self._write_extraction_status(
                        run_id,
                        status="RUNNING",
                        stage=f"Completed {project_file.filename}: batch {batch_number} of {request_batches}",
                        progress=self._file_progress(
                            total_files,
                            processed_files,
                            batch_number / request_batches if request_batches else 1.0,
                        ),
                        total_files=total_files,
                        processed_files=processed_files,
                        current_file_id=project_file.id,
                        current_file_name=project_file.filename,
                        current_file_index=file_position,
                        stored_chunks=stored_chunks,
                        request_batches=request_batches,
                        completed_batches=batch_number,
                        current_batch_index=batch_number,
                        current_chunk_index=batch.chunk_index,
                        primary_start_line=batch.primary_start_line,
                        primary_end_line=batch.primary_end_line,
                        semantic_units=batch.semantic_units,
                    )
                except Exception as exc:
                    failed_chunks += 1
                    failed = {
                        "chunk_index": batch.chunk_index,
                        "primary_start_line": batch.primary_start_line,
                        "primary_end_line": batch.primary_end_line,
                        "semantic_units": batch.semantic_units,
                        "status": "FAILED",
                        "error": str(exc),
                        "business_rules": [],
                        "warnings": [{"reason": "chunk_failed", "rule_text": str(exc)}],
                    }
                    self._write_chunk_result(run_id, project_file.id, batch.chunk_index, failed)
                    chunk_results.append(failed)

        successful_results = [item for item in chunk_results if item.get("status") == "COMPLETED"]
        file_metadata = {
            "file_id": project_file.id,
            "file_name": project_file.filename,
            "detected_language": source_profile.detected_language,
            "artifact_type": source_profile.artifact_type,
            "file_role": source_profile.file_role,
            "major_paragraphs": [getattr(paragraph, "name", "") for paragraph in source_profile.paragraphs[:20]],
        }
        final_result = self.reconciler.reconcile(successful_results, file_metadata)
        final_rules, rejected_final = self.quality_service.filter_rules(final_result.get("business_rules") or [])
        final_result["business_rules"] = final_rules
        final_result.setdefault("unresolved_items", [])
        final_result["unresolved_items"].extend(
            {
                "item": item.get("rule_text", ""),
                "reason": item.get("reason", "final_quality_rejected"),
                "technical_reference": project_file.filename,
            }
            for item in rejected_final
        )

        completed_chunks = len(successful_results)
        analysis_coverage = round(completed_chunks / request_batches, 4) if request_batches else 0.0
        processing_mode = "chunked_hybrid" if fallback_chunks else "chunked_llm"
        if llm_chunks == 0 and fallback_chunks:
            processing_mode = "chunked_deterministic"
        quality_status = "PASSED" if failed_chunks == 0 else "PARTIAL"
        chunk_execution = {
            "processing_mode": processing_mode,
            "stored_chunks": stored_chunks,
            "request_batches": request_batches,
            "completed_chunks": completed_chunks,
            "llm_chunks": llm_chunks,
            "fallback_chunks": fallback_chunks,
            "failed_chunks": failed_chunks,
            "overlap_lines": overlap_lines,
            "analysis_coverage": analysis_coverage,
            "quality_status": quality_status,
            "diagnostics": diagnostics,
        }

        final_result.update(
            {
                "file_id": project_file.id,
                "file_name": project_file.filename,
                "detected_language": source_profile.detected_language,
                "artifact_type": source_profile.artifact_type,
                "file_role": source_profile.file_role,
                "selected_agent": self._selected_agent_from_results(successful_results),
                "agent_name": self._selected_agent_from_results(successful_results),
                "agent_key": next((item.get("agent_key") for item in successful_results if item.get("agent_key")), ""),
                "extraction_mode": processing_mode,
                "processing_mode": processing_mode,
                "llm_called": llm_chunks > 0,
                "fallback_used": fallback_chunks > 0,
                "fallback_reason": self._fallback_reason(successful_results),
                "model": self._model_from_results(successful_results),
                "source_character_count": source_profile.source_character_count,
                "source_hash": source_hash,
                "extractor_version": self.EXTRACTOR_VERSION,
                "prompt_version": self.PROMPT_VERSION,
                "technical_analysis_version": self.TECHNICAL_ANALYSIS_VERSION,
                "technical_yaml": self._manifest_technical_yaml(chunk_execution),
                "coverage": {
                    "paragraphs_total": len(source_profile.paragraphs or []),
                    "paragraphs_analyzed": len(source_profile.paragraphs or []),
                    "paragraphs_with_rules": len({
                        str(rule.get("paragraph") or "").upper()
                        for rule in final_rules
                        if rule.get("paragraph")
                    }),
                    "paragraphs_without_business_rules": max(
                        0,
                        len(source_profile.paragraphs or [])
                        - len({
                            str(rule.get("paragraph") or "").upper()
                            for rule in final_rules
                            if rule.get("paragraph")
                        }),
                    ),
                    "source_coverage": analysis_coverage,
                },
                "chunk_execution": chunk_execution,
            }
        )

        self._write_chunk_manifest(
            run_id=run_id,
            file_id=project_file.id,
            manifest={
                "run_id": run_id,
                "file_id": project_file.id,
                "file_name": project_file.filename,
                "source_hash": source_hash,
                "extractor_version": self.EXTRACTOR_VERSION,
                "prompt_version": self.PROMPT_VERSION,
                "technical_analysis_version": self.TECHNICAL_ANALYSIS_VERSION,
                **chunk_execution,
            },
        )
        print("Chunk reconciliation completed")
        print("Final quality gate passed" if quality_status == "PASSED" else "Final quality gate partial")
        return final_result

    def _load_or_create_chunks_for_file(
        self,
        run_id: str,
        file_id: int,
        file_name: str,
        source_code: str,
        language: str,
    ) -> list[FileChunk]:
        chunks = (
            self.db.query(FileChunk)
            .filter_by(run_id=run_id, file_id=file_id)
            .order_by(FileChunk.chunk_index)
            .all()
        )

        if chunks:
            return chunks

        print(f"No FileChunk rows found for run={run_id} file={file_id}; creating them once.")
        orchestrator = ChunkingOrchestrator(self.db)
        orchestrator.process_file_pipeline(
            run_id=run_id,
            file_id=file_id,
            filename=file_name,
            content=source_code,
            lang=language,
        )

        return (
            self.db.query(FileChunk)
            .filter_by(run_id=run_id, file_id=file_id)
            .order_by(FileChunk.chunk_index)
            .all()
        )

    def _request_batches_for_chunk(
        self,
        *,
        chunk_source: BusinessLogicChunkSource,
        technical_yaml: str,
        dependency_context: str,
        glossary_context: str,
    ) -> list[BusinessLogicChunkSource]:
        if self._fits_business_logic_prompt(
            source_text=format_chunk_for_prompt(chunk_source),
            technical_yaml=technical_yaml,
            dependency_context=dependency_context,
            glossary_context=glossary_context,
            max_input_tokens=self.max_input_tokens,
        ):
            return [chunk_source]

        fixed_chars = len("\n".join([technical_yaml or "", dependency_context or "", glossary_context or ""]))
        max_primary_chars = max(1200, (self.max_input_tokens * 3) - fixed_chars - len(chunk_source.overlap_source or "") - 1200)
        return split_chunk_source_for_prompt_budget(chunk_source, max_primary_chars=max_primary_chars)

    @staticmethod
    def _fits_business_logic_prompt(
        source_text: str,
        technical_yaml: str,
        dependency_context: str,
        glossary_context: str,
        max_input_tokens: int,
    ) -> bool:
        combined = "\n".join(
            [
                source_text or "",
                technical_yaml or "",
                dependency_context or "",
                glossary_context or "",
            ]
        )
        estimated_tokens = max(1, len(combined) // 3)
        return estimated_tokens <= max_input_tokens

    def _normalized_chunk_source(self, chunk_source: BusinessLogicChunkSource) -> BusinessLogicChunkSource:
        overlap_source = self.preprocessor.normalize_source(chunk_source.overlap_source)[0] if chunk_source.overlap_source else ""
        primary_source = self.preprocessor.normalize_source(chunk_source.primary_source)[0] if chunk_source.primary_source else ""
        return BusinessLogicChunkSource(
            chunk_index=chunk_source.chunk_index,
            primary_start_line=chunk_source.primary_start_line,
            primary_end_line=chunk_source.primary_end_line,
            overlap_start_line=chunk_source.overlap_start_line,
            overlap_end_line=chunk_source.overlap_end_line,
            overlap_source=overlap_source,
            primary_source=primary_source,
            semantic_units=chunk_source.semantic_units,
            request_index=chunk_source.request_index,
            parent_chunk_index=chunk_source.parent_chunk_index,
        )

    def _load_technical_yaml_for_chunk(self, run_id: str, chunk: FileChunk) -> str:
        analysis = (
            self.db.query(ChunkAnalysis)
            .filter(
                ChunkAnalysis.run_id == run_id,
                ChunkAnalysis.chunk_id == chunk.id,
            )
            .first()
        )
        return str(getattr(analysis, "technical_yaml", "") or "") if analysis else ""

    @staticmethod
    def _chunk_prompt_yaml(
        *,
        chunk_yaml: str,
        batch: BusinessLogicChunkSource,
        source_profile: Any,
    ) -> str:
        semantic_units = ", ".join(batch.semantic_units) if batch.semantic_units else "file:FILE"
        return (
            f"file_role: {getattr(source_profile, 'file_role', 'unknown')}\n"
            f"artifact_type: {getattr(source_profile, 'artifact_type', 'unknown')}\n"
            f"chunk: {batch.chunk_index}\n"
            f"primary_start_line: {batch.primary_start_line}\n"
            f"primary_end_line: {batch.primary_end_line}\n"
            f"semantic_units: {semantic_units}\n"
            f"{chunk_yaml or ''}"
        )

    def _write_chunk_result(
        self,
        run_id: str,
        file_id: int | str,
        chunk_index: int | str,
        payload: dict[str, Any],
    ) -> None:
        path = self._chunk_result_dir(run_id, file_id) / f"{self._chunk_file_name(chunk_index)}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _write_chunk_manifest(
        self,
        run_id: str,
        file_id: int | str,
        manifest: dict[str, Any],
    ) -> None:
        path = self._business_logic_file_dir(run_id, file_id) / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    def _clear_business_logic_chunk_outputs(self, run_id: str, file_id: int | str) -> None:
        root = self._business_logic_file_dir(run_id, file_id)
        if not root.exists():
            return
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
        try:
            root.rmdir()
        except OSError:
            pass

    def _business_logic_file_dir(self, run_id: str, file_id: int | str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "business_logic" / run_id / str(file_id)

    def _chunk_result_dir(self, run_id: str, file_id: int | str) -> Path:
        return self._business_logic_file_dir(run_id, file_id) / "chunks"

    @staticmethod
    def _chunk_file_name(chunk_index: int | str) -> str:
        text = str(chunk_index)
        if text.isdigit():
            return f"{int(text):03d}"
        return text.replace(".", "_")

    @staticmethod
    def _selected_agent_from_results(results: list[dict[str, Any]]) -> str:
        return next(
            (
                item.get("selected_agent") or item.get("agent_name")
                for item in results
                if item.get("selected_agent") or item.get("agent_name")
            ),
            "GenericBusinessLogicAgent",
        )

    @staticmethod
    def _model_from_results(results: list[dict[str, Any]]) -> str:
        return next((item.get("model") for item in results if item.get("model")), "")

    @staticmethod
    def _fallback_reason(results: list[dict[str, Any]]) -> str:
        reasons = [
            str(item.get("fallback_reason") or "").strip()
            for item in results
            if item.get("fallback_used") and str(item.get("fallback_reason") or "").strip()
        ]
        return "; ".join(dict.fromkeys(reasons))

    @staticmethod
    def _manifest_technical_yaml(chunk_execution: dict[str, Any]) -> str:
        return "business_logic_chunk_execution:\n" + "\n".join(
            f"  {key}: {value}"
            for key, value in chunk_execution.items()
            if key != "diagnostics"
        )

    def _persist_agentic_business_logic_result(
        self,
        run_id: str,
        project_file,
        result: dict,
    ) -> None:
        """
        Store normalized business rules in your existing BusinessRule table.

        Adjust field names if your BusinessRule model uses different columns.
        """

        from Persistence.sqlite.models import BusinessRule

        file_id = getattr(project_file, "id", None)

        rules = result.get("business_rules") or []

        # Store purpose as a rule also, so existing UI can show something immediately.
        business_purpose = result.get("business_purpose") or ""
        functional_logic = self._format_functional_logic(
            result.get("functional_logic") or []
        )
        technical_yaml = result.get("technical_yaml") or ""

        if business_purpose.strip():
            purpose_rule = BusinessRule(
                run_id=run_id,
                file_id=file_id,
                rule_id=f"PURPOSE-{file_id}",
                rule_text=business_purpose,
                business_purpose=business_purpose,
                functional_logic=functional_logic,
                business_logic=functional_logic or business_purpose,
                technical_ref=result.get("file_name", ""),
                technical_yaml=technical_yaml,
                status="PENDING",
            )
            self.db.add(purpose_rule)

        for index, item in enumerate(rules, start=1):
            if not isinstance(item, dict):
                continue

            rule_text = (
                item.get("rule_text")
                or item.get("description")
                or item.get("business_meaning")
                or ""
            )

            if not str(rule_text).strip():
                continue

            rule = BusinessRule(
                run_id=run_id,
                file_id=file_id,
                rule_id=f"BR-{file_id}-{index}",
                rule_text=str(rule_text).strip(),
                technical_ref=str(
                    item.get("technical_reference")
                    or item.get("technical_ref")
                    or ""
                ),
                technical_yaml=technical_yaml,
                business_purpose=business_purpose,
                functional_logic=functional_logic,
                business_logic=str(rule_text).strip(),
                status="PENDING",
            )

            self.db.add(rule)

        self.db.flush()

    def _replace_business_rules_for_file(
        self,
        run_id: str,
        project_file,
        result: dict,
    ) -> None:
        file_id = getattr(project_file, "id", None)
        try:
            (
                self.db.query(BusinessRule)
                .filter(
                    BusinessRule.run_id == run_id,
                    BusinessRule.file_id == file_id,
                )
                .delete(synchronize_session=False)
            )
            self._persist_agentic_business_logic_result(
                run_id=run_id,
                project_file=project_file,
                result=result,
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _build_business_file_context(
        self,
        project_file,
        technical_yaml: str,
        source_code: str,
        dependency_context: str = "",
        glossary_context: str = "",
        source_profile: Any | None = None,
    ) -> BusinessLogicFileContext:
        detected_language = (
            getattr(project_file, "detected_language", None)
            or getattr(project_file, "detected_lang", None)
            or getattr(project_file, "language", None)
            or "unknown"
        )
        if source_profile is not None:
            detected_language = getattr(source_profile, "detected_language", detected_language)

        file_name = (
            getattr(project_file, "filename", None)
            or getattr(project_file, "file_name", None)
            or getattr(project_file, "relative_path", None)
            or f"file_{getattr(project_file, 'id', '')}"
        )

        return BusinessLogicFileContext(
            file_id=getattr(project_file, "id", ""),
            file_name=file_name,
            detected_language=detected_language,
            source_code=source_code or "",
            technical_yaml=technical_yaml or "",
            dependency_context=dependency_context or "",
            glossary_context=glossary_context or "",
            artifact_type=getattr(source_profile, "artifact_type", "") if source_profile is not None else "",
            file_role=getattr(source_profile, "file_role", "") if source_profile is not None else "",
            source_character_count=getattr(source_profile, "source_character_count", 0) if source_profile is not None else len(source_code or ""),
            line_map=getattr(source_profile, "line_map", None) if source_profile is not None else None,
            paragraphs=getattr(source_profile, "paragraphs", None) if source_profile is not None else None,
        )

    def _build_agentic_extractor(self, project) -> AgenticBusinessLogicExtractor:
        """Build LLM config from project settings.
        
                    This keeps the business logic orchestrator independent from DB/project models."""

        llm_config = {
            "mode": getattr(project, "ai_mode", None)
            or getattr(project, "llm_provider", None)
            or self.config.get("mode")
            or self.config.get("provider")
            or "local",
            "provider": getattr(project, "llm_provider", None)
            or getattr(project, "ai_mode", None)
            or self.config.get("provider")
            or self.config.get("mode")
            or "local",
            "model": getattr(project, "llm_model", None)
            or getattr(project, "model", None)
            or self.config.get("model")
            or "llama3",
            "url": getattr(project, "custom_api_base_url", None)
            or getattr(project, "api_base_url", None)
            or self.config.get("url")
            or self.config.get("base_url")
            or "http://127.0.0.1:11434",
            "key": getattr(project, "custom_api_key", None)
            or getattr(project, "api_key", None)
            or self.config.get("key")
            or self.config.get("api_key")
            or None,
            "timeout": self.config.get("timeout")
            or os.getenv("BUSINESS_LOGIC_LLM_TIMEOUT", "30"),
            "max_tokens": self.config.get("max_tokens") or 1600,
        }

        return AgenticBusinessLogicExtractor(llm_config=llm_config)

    def _load_source_code_for_file(self, project_file) -> str:
        content = self._read_project_file(project_file)
        if content:
            return content

        for attr_name in ("file_path", "path", "storage_path", "absolute_path"):
            item = getattr(project_file, attr_name, None)
            if not item:
                continue

            try:
                path = Path(item)
                if path.exists() and path.is_file():
                    return path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

        return str(getattr(project_file, "content", "") or "")

    def _load_technical_yaml_for_file(self, run_id: str, file_id: int) -> str:
        rows = (
            self.db.query(ChunkAnalysis, FileChunk)
            .join(FileChunk, ChunkAnalysis.chunk_id == FileChunk.id)
            .filter(
                ChunkAnalysis.run_id == run_id,
                FileChunk.file_id == file_id,
            )
            .order_by(FileChunk.chunk_index)
            .all()
        )

        yaml_parts = []
        for analysis, chunk in rows:
            technical_yaml = getattr(analysis, "technical_yaml", "") or ""
            if technical_yaml.strip():
                yaml_parts.append(
                    f"# chunk_id: {chunk.id}, chunk_index: {chunk.chunk_index}\n"
                    f"{technical_yaml}"
                )

        return "\n\n---\n\n".join(yaml_parts)

    def _build_dependency_context_for_file(self, run_id: str, file_id: int) -> str:
        project_file = self.db.query(ProjectFile).filter_by(id=file_id).first()
        if not project_file:
            return ""

        source_names = {
            item
            for item in (
                project_file.filename,
                project_file.filepath,
                (project_file.filepath or "").replace("\\", "/"),
            )
            if item
        }

        rows = (
            self.db.query(FileRelation)
            .filter(
                FileRelation.run_id == run_id,
                FileRelation.source_file.in_(source_names),
            )
            .limit(100)
            .all()
        )

        items = [
            {
                "source_file": row.source_file,
                "relation_type": row.relation_type,
                "target": row.target_item,
            }
            for row in rows
        ]

        return json.dumps(items, indent=2)

    def _build_glossary_context(self, run_id: str) -> str:
        return ""

    def _format_functional_logic(self, items: Any) -> str:
        if isinstance(items, str):
            return items.strip()

        if not isinstance(items, list):
            return ""

        parts = []
        for item in items:
            if isinstance(item, dict):
                title = str(item.get("title") or "").strip()
                description = str(item.get("description") or "").strip()
                text = f"{title}: {description}".strip(": ").strip()
            else:
                text = str(item or "").strip()

            if text:
                parts.append(text)

        return "\n".join(parts)

    def _replace_rules(self, run_id: str, prepared_rules: list[dict]) -> None:
        """
        Safely replaces all rules for a run.
        """
        try:
            self.db.query(BusinessRule).filter_by(run_id=run_id).delete(synchronize_session=False)

            for index, rule in enumerate(prepared_rules, start=1):
                rule_text = rule["rule_text"]
                functional_logic = rule.get("functional_logic") or ""

                self.db.add(BusinessRule(
                    run_id=run_id,
                    chunk_id=rule["chunk_id"],
                    file_id=rule["file_id"],
                    chunk_index=rule["chunk_index"],
                    rule_id=f"BR-{index:03d}",
                    rule_text=rule_text,
                    technical_ref=rule.get("technical_ref") or "",
                    technical_yaml=rule.get("technical_yaml") or "",
                    business_purpose=rule.get("business_purpose") or "",
                    functional_logic=functional_logic,
                    business_logic=functional_logic or rule_text,
                    status="PENDING",
                ))

            self.db.commit()

        except Exception:
            self.db.rollback()
            raise

    def _load_or_create_chunks(self, run_id: str) -> list[FileChunk]:
        chunks = (
            self.db.query(FileChunk)
            .filter_by(run_id=run_id)
            .order_by(FileChunk.file_id, FileChunk.chunk_index)
            .all()
        )
        if chunks:
            return chunks

        project_files = self.db.query(ProjectFile).filter_by(run_id=run_id).all()
        created = []

        for project_file in project_files:
            content = self._read_project_file(project_file)
            if not content or not self._is_legacy_source_chunk(project_file, content):
                continue

            chunk = FileChunk(
                run_id=run_id,
                file_id=project_file.id,
                chunk_index=0,
                content=content,
                start_line=1,
                end_line=content.count("\n") + (1 if content else 0),
                overlap_content="",
                semantic_units='["file:FILE"]',
                status="PENDING",
            )
            self.db.add(chunk)
            created.append(chunk)

        if created:
            self.db.commit()
            return (
                self.db.query(FileChunk)
                .filter_by(run_id=run_id)
                .order_by(FileChunk.file_id, FileChunk.chunk_index)
                .all()
            )

        return []

    def _read_project_file(self, project_file: ProjectFile) -> str:
        rel = (project_file.filepath or project_file.filename or "").replace("\\", "/").strip("/")
        if not rel or ".." in rel.split("/"):
            return ""

        candidates = [
            UPLOADS_DIR / project_file.run_id / rel,
            UPLOADS_DIR / project_file.run_id / "local_repo" / rel,
            UPLOADS_DIR / project_file.run_id / (project_file.filename or ""),
        ]

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate.read_text(errors="ignore")
            except OSError as exc:
                print(f"Could not read uploaded file {candidate}: {exc}")

        return ""

    def _prepare_agent_result(self, result: Any, chunk: FileChunk, technical_yaml: str) -> list[dict]:
        if isinstance(result, dict):
            purpose = result.get("business_purpose", "")
            functional_logic = result.get("functional_logic", "")
            rules = result.get("rules", [])
        elif isinstance(result, list):
            purpose = "Extracted from COBOL source."
            functional_logic = "Refer to technical evidence."
            rules = result
        else:
            purpose = "Extracted from COBOL source."
            functional_logic = "Refer to technical evidence."
            rules = []

        prepared = []

        for rule in rules:
            if isinstance(rule, dict):
                rule_text = (rule.get("rule_text") or rule.get("text") or rule.get("rule") or "").strip()
                technical_ref = (rule.get("technical_ref") or rule.get("source") or rule.get("reference") or "").strip()
                rule_type = (rule.get("rule_type") or "BUSINESS_DECISION").strip()
                confidence = (rule.get("confidence") or "MEDIUM").strip()
            else:
                rule_text = str(rule or "").strip()
                technical_ref = ""
                rule_type = "BUSINESS_DECISION"
                confidence = "MEDIUM"

            if not rule_text:
                continue

            decorated_ref = technical_ref
            if rule_type:
                decorated_ref = f"[{rule_type}] {decorated_ref}".strip()
            if confidence:
                decorated_ref = f"{decorated_ref} | Confidence: {confidence}".strip()

            prepared.append({
                "chunk_id": chunk.id,
                "file_id": chunk.file_id,
                "chunk_index": chunk.chunk_index,
                "business_purpose": purpose,
                "functional_logic": functional_logic,
                "rule_text": rule_text,
                "technical_ref": decorated_ref,
                "technical_yaml": technical_yaml,
            })

        return prepared

    def _is_legacy_source_chunk(
        self,
        project_file: ProjectFile | None,
        content: str | None,
    ) -> bool:
        if not project_file:
            return False

        filename = (
            project_file.filepath
            or project_file.filename
            or ""
        ).lower()

        language = (
            project_file.detected_lang
            or ""
        ).lower()

        supported_extensions = (
            ".cob",
            ".cbl",
            ".cpy",
            ".jcl",
            ".job",
            ".telon",
            ".tps",
            ".pli",
            ".pl1",
            ".sql",
            ".ddl",
        )

        supported_languages = {
            "cobol",
            "copybook",
            "jcl",
            "telon",
            "pli",
            "pl/i",
            "pl1",
            "sql",
            "db2",
        }

        has_supported_extension = filename.endswith(
            supported_extensions
        )

        has_supported_language = (
            language in supported_languages
            or language.startswith("cobol")
            or language.startswith("telon")
        )

        return (
            has_supported_extension
            or has_supported_language
        ) and bool(content and content.strip())

    @staticmethod
    def _is_detected_or_confirmed(project_file: ProjectFile | None) -> bool:
        if not project_file:
            return False
        if project_file.status == FileStatus.CONFIRMED:
            return True
        detected = str(project_file.detected_lang or "").strip().lower()
        return bool(detected and detected != "unknown")

    def _generate_local_yaml_from_source(self, source_code: str | None) -> str:
        profile = self.preprocessor.prepare(source_code or "")
        return self.preprocessor.to_technical_yaml(profile)

    def _is_logic_candidate(self, content: str | None) -> bool:
        return bool(content and self.LOGIC_RE.search(content))

    def _generate_local_yaml(self, chunk: FileChunk) -> str:
        blocks = []

        for line_no, raw_line in enumerate((chunk.content or "").splitlines(), start=1):
            line = self._strip_sequence_number(raw_line).strip()

            if not line:
                continue

            if line.upper().startswith(("*", "*>")):
                continue

            if not self.LOGIC_RE.search(line):
                continue

            safe_description = line.replace('"', "'")[:240]

            blocks.append(
                "    - name: \"line-{line_no}\"\n"
                "      type: \"BUSINESS_LOGIC\"\n"
                "      description: \"{description}\"\n"
                "      calls: []".format(
                    line_no=line_no,
                    description=safe_description,
                )
            )

        if not blocks:
            return "control_flow:\n  logic_blocks: []\n"

        return "control_flow:\n  logic_blocks:\n" + "\n".join(blocks) + "\n"

    @staticmethod
    def _strip_sequence_number(line: str) -> str:
        return re.sub(r"^\d{5,6}\s+", "", str(line or "").strip())
