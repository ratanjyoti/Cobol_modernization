from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from services.migration_scope_service import MigrationScopeService


class ScopedMigrationProcess:
    """
    Runs only the stages allowed by the selected migration scope.

    Owns selected-scope execution, skip/completion status, and scope status JSON.
    """

    def __init__(self, db):
        self.db = db
        self.scope_service = MigrationScopeService()

    def update_scope(self, run_id: str, scope: str) -> str:
        from Persistence.sqlite.models import Project

        project = self.db.query(Project).filter(Project.run_id == run_id).first()
        if not project:
            raise ValueError(f"Project not found: {run_id}")

        normalized = self.scope_service.normalize_scope(scope)
        project.migration_scope = normalized
        self.db.commit()
        return normalized

    def run_selected_scope(self, run_id: str) -> dict[str, Any]:
        from Persistence.sqlite.models import Project

        project = self.db.query(Project).filter(Project.run_id == run_id).first()
        if not project:
            raise ValueError(f"Project not found: {run_id}")

        scope = self.scope_service.normalize_scope(getattr(project, "migration_scope", None))
        definition = self.scope_service.get_scope(scope)
        previously_completed = self._load_completed_stages(run_id)
        completed = self._completed_stages_for_scope(run_id, scope, previously_completed)
        skipped_completed: list[str] = []

        self._write_status(run_id, scope, "RUNNING", "start", completed, skipped_completed)

        for stage, runner in (
            (MigrationScopeService.STAGE_LANGUAGE_DETECTION, self._run_language_detection),
            (MigrationScopeService.STAGE_DEPENDENCY_MAPPING, self._run_dependency_mapping),
            (MigrationScopeService.STAGE_GRAPH_BUILD, self._run_graph_build),
            (MigrationScopeService.STAGE_CHUNKING, self._run_chunking),
            (MigrationScopeService.STAGE_TECHNICAL_YAML, self._run_technical_yaml),
            (MigrationScopeService.STAGE_PROCEDURAL_FLOW, self._run_procedural_flow),
            (MigrationScopeService.STAGE_BUSINESS_LOGIC, self._run_business_logic),
            (MigrationScopeService.STAGE_REVERSE_REPORT, self._run_reverse_report),
            (MigrationScopeService.STAGE_DDD, self._run_ddd),
            (MigrationScopeService.STAGE_CONVERSION_PLANNING, self._run_conversion_planning),
            (MigrationScopeService.STAGE_CODE_GENERATION, self._run_code_generation),
            (MigrationScopeService.STAGE_QUALITY_GATE, self._run_quality_gate),
            (MigrationScopeService.STAGE_VALIDATION, self._run_validation),
            (MigrationScopeService.STAGE_MIGRATION_REPORT, self._run_migration_report),
        ):
            if not self._allowed(scope, stage):
                continue
            if stage in completed:
                skipped_completed.append(stage)
                self._write_status(run_id, scope, "RUNNING", stage, completed, skipped_completed)
                continue
            self._write_status(run_id, scope, "RUNNING", stage, completed, skipped_completed)
            runner(run_id)
            completed.append(stage)
            self._write_status(run_id, scope, "RUNNING", stage, completed, skipped_completed)

        self._write_status(run_id, scope, "COMPLETED", "completed", completed, skipped_completed)

        return {
            "run_id": run_id,
            "scope": scope,
            "scope_title": definition.title,
            "completed_stages": completed,
            "pending_stages": self._pending_stages(scope, completed),
            "skipped_completed_stages": skipped_completed,
            "blocked_stages": self.scope_service.blocked_stages(scope),
        }

    def _allowed(self, scope: str, stage: str) -> bool:
        return self.scope_service.is_stage_allowed(scope, stage)

    def _run_dependency_mapping(self, run_id: str) -> None:
        from Chunking.dependency_scanner.resolution_service import ResolutionService

        ResolutionService(self.db).resolve_run_relations(run_id)
        self.db.commit()

    def _run_graph_build(self, run_id: str) -> None:
        from Processes.graphing_process import GraphingProcess

        try:
            GraphingProcess(self.db).build_full_graph(run_id)
        except Exception as exc:
            print(f"Scoped graph build skipped for {run_id}: {exc}")

    def _run_chunking(self, run_id: str) -> None:
        from Chunking.chunking_orchestrator import ChunkingOrchestrator
        from Persistence.sqlite.models import FileStatus, ProjectFile
        from paths import UPLOADS_DIR

        orchestrator = ChunkingOrchestrator(self.db)
        files = self.db.query(ProjectFile).filter(ProjectFile.run_id == run_id).all()

        for project_file in files:
            detected = str(project_file.detected_lang or "").strip().lower()
            if project_file.status != FileStatus.CONFIRMED and (not detected or detected == "unknown"):
                continue

            source_path = self._resolve_source_path(run_id, project_file)
            if not source_path:
                continue

            content = source_path.read_text(encoding="utf-8", errors="ignore")
            orchestrator.process_file(
                run_id=run_id,
                file_id=project_file.id,
                filename=project_file.filepath or project_file.filename,
                content=content,
                lang=project_file.detected_lang or "unknown",
            )

    def _run_language_detection(self, run_id: str) -> None:
        return None

    def _run_technical_yaml(self, run_id: str) -> None:
        from Processes.analysis_process import AnalysisProcess

        self._run_async(AnalysisProcess(self.db, self._llm_config(run_id)).analyze_project(run_id))

    def _run_procedural_flow(self, run_id: str) -> None:
        from Processes.procedural_flow_process import ProceduralFlowProcess

        ProceduralFlowProcess(self.db).extract_all(run_id)

    def _run_business_logic(self, run_id: str) -> None:
        from Processes.logic_extraction_process import LogicExtractionProcess

        self._run_async(
            LogicExtractionProcess(
                db_session=self.db,
                llm_provider=self._llm_config(run_id),
            ).extract_all_rules(run_id)
        )

    def _run_reverse_report(self, run_id: str) -> None:
        return None

    def _run_ddd(self, run_id: str) -> None:
        return None

    def _run_conversion_planning(self, run_id: str) -> None:
        from Processes.conversion_planning_process import ConversionPlanningProcess

        ConversionPlanningProcess(self.db).create_plans(
            run_id=run_id,
            target_language=self._target_language(run_id),
            project_id=run_id,
        )

    def _run_code_generation(self, run_id: str) -> None:
        from Processes.code_generation_process import CodeGenerationProcess

        CodeGenerationProcess(self.db).generate(
            run_id=run_id,
            target_language=self._target_language(run_id),
            project_id=run_id,
        )

    def _run_quality_gate(self, run_id: str) -> None:
        from Processes.code_generation_process import CodeGenerationProcess

        process = CodeGenerationProcess(self.db)
        target = self._target_language(run_id)
        process.quality_service.evaluate(
            run_id=run_id,
            target_language=target,
            project_dir=process._project_dir(run_id, target),
        )

    def _run_validation(self, run_id: str) -> None:
        from Processes.code_generation_process import CodeGenerationProcess

        CodeGenerationProcess(self.db).validate_generated_project(
            run_id=run_id,
            target_language=self._target_language(run_id),
        )

    def _run_migration_report(self, run_id: str) -> None:
        from services.migration_report_service import MigrationReportService

        MigrationReportService(self.db).generate_report(
            run_id=run_id,
            target_language=self._target_language(run_id),
        )

    def _write_status(
        self,
        run_id: str,
        scope: str,
        status: str,
        current_stage: str,
        completed_stages: list[str],
        skipped_completed_stages: list[str] | None = None,
    ) -> None:
        estimate = self.scope_service.estimate_tokens_for_run(self.db, run_id, scope)
        pending_stages = self._pending_stages(scope, completed_stages)
        path = self.scope_service.status_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "run_id": run_id,
            "scope": scope,
            "scope_title": self.scope_service.get_scope(scope).title,
            "status": status,
            "current_stage": current_stage,
            "completed_stages": list(completed_stages),
            "pending_stages": pending_stages,
            "skipped_completed_stages": list(skipped_completed_stages or []),
            "blocked_stages": self.scope_service.blocked_stages(scope),
            "estimated_total_tokens": estimate["estimated_total_tokens"],
            "static_token_range": estimate["static_token_range"],
            "actual_tokens_used": 0,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


    def _pending_stages(self, scope: str, completed_stages: list[str]) -> list[str]:
        completed = set(completed_stages)
        return [
            stage
            for stage in self.scope_service.get_scope(scope).allowed_stages
            if stage not in completed
        ]

    def _load_completed_stages(self, run_id: str) -> set[str]:
        path = self.scope_service.status_path(run_id)
        if not path.exists():
            return set()

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            return set()

        completed = payload.get("completed_stages") or []
        if not isinstance(completed, list):
            return set()

        aliases = {
            "technical": MigrationScopeService.STAGE_TECHNICAL_YAML,
            "program_flow": MigrationScopeService.STAGE_PROCEDURAL_FLOW,
            "procedural": MigrationScopeService.STAGE_PROCEDURAL_FLOW,
            "ddd": MigrationScopeService.STAGE_DDD,
            "planning": MigrationScopeService.STAGE_CONVERSION_PLANNING,
            "conversion_plan": MigrationScopeService.STAGE_CONVERSION_PLANNING,
            "reports": MigrationScopeService.STAGE_MIGRATION_REPORT,
            "report": MigrationScopeService.STAGE_MIGRATION_REPORT,
        }

        normalized = set()
        for stage in completed:
            key = str(stage).strip()
            if key:
                normalized.add(aliases.get(key, key))
        return normalized

    def _completed_stages_for_scope(
        self,
        run_id: str,
        scope: str,
        known_completed: set[str] | None = None,
    ) -> list[str]:
        known_completed = known_completed or set()
        completed = []

        for stage in self.scope_service.get_scope(scope).allowed_stages:
            if stage in known_completed or self._stage_has_artifact(run_id, stage):
                completed.append(stage)

        return completed

    def _stage_has_artifact(self, run_id: str, stage: str) -> bool:
        from sqlalchemy import func
        from Persistence.sqlite.models import BusinessRule, ChunkAnalysis, FileChunk, FileRelation, ProjectComplexity, ProjectFile

        if stage == MigrationScopeService.STAGE_LANGUAGE_DETECTION:
            total = self.db.query(func.count(ProjectFile.id)).filter(ProjectFile.run_id == run_id).scalar() or 0
            detected = self.db.query(func.count(ProjectFile.id)).filter(
                ProjectFile.run_id == run_id,
                ProjectFile.detected_lang.isnot(None),
                ProjectFile.detected_lang != "",
            ).scalar() or 0
            return total > 0 and detected >= total

        if stage == MigrationScopeService.STAGE_DEPENDENCY_MAPPING:
            return (self.db.query(func.count(FileRelation.id)).filter(FileRelation.run_id == run_id).scalar() or 0) > 0

        if stage == MigrationScopeService.STAGE_GRAPH_BUILD:
            return self.db.query(ProjectComplexity).filter(ProjectComplexity.run_id == run_id).first() is not None

        if stage == MigrationScopeService.STAGE_CHUNKING:
            return (self.db.query(func.count(FileChunk.id)).filter(FileChunk.run_id == run_id).scalar() or 0) > 0

        if stage == MigrationScopeService.STAGE_TECHNICAL_YAML:
            return (self.db.query(func.count(ChunkAnalysis.id)).filter(
                ChunkAnalysis.run_id == run_id,
                ChunkAnalysis.analysis_status == "COMPLETED",
            ).scalar() or 0) > 0

        if stage == MigrationScopeService.STAGE_BUSINESS_LOGIC:
            return (self.db.query(func.count(BusinessRule.id)).filter(BusinessRule.run_id == run_id).scalar() or 0) > 0

        if stage == MigrationScopeService.STAGE_CONVERSION_PLANNING:
            return self._has_files(self._output_root(run_id) / "plans" / self._target_language(run_id), "*.json")

        if stage == MigrationScopeService.STAGE_CODE_GENERATION:
            converted = self.db.query(func.count(FileChunk.id)).filter(
                FileChunk.run_id == run_id,
                FileChunk.converted_code.isnot(None),
                FileChunk.converted_code != "",
            ).scalar() or 0
            return converted > 0 or self._has_files(self._output_root(run_id) / "project" / self._target_language(run_id))

        if stage == MigrationScopeService.STAGE_QUALITY_GATE:
            return (self._output_root(run_id) / "quality" / self._target_language(run_id) / "latest_quality.json").exists()

        if stage == MigrationScopeService.STAGE_VALIDATION:
            return (self._output_root(run_id) / "validation" / self._target_language(run_id) / "latest_validation.json").exists()

        if stage == MigrationScopeService.STAGE_MIGRATION_REPORT:
            report_dir = self._output_root(run_id) / "reports" / self._target_language(run_id)
            return (report_dir / "migration_report.json").exists() or (report_dir / "MIGRATION_REPORT.md").exists()

        return stage in {
            MigrationScopeService.STAGE_PROCEDURAL_FLOW,
            MigrationScopeService.STAGE_REVERSE_REPORT,
            MigrationScopeService.STAGE_DDD,
        } and stage in self._load_completed_stages(run_id)

    @staticmethod
    def _output_root(run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "generated_code" / run_id

    @staticmethod
    def _has_files(path: Path, pattern: str = "*") -> bool:
        try:
            return path.exists() and any(item.is_file() for item in path.rglob(pattern))
        except OSError:
            return False

    def _llm_config(self, run_id: str) -> dict[str, Any]:
        from Persistence.sqlite.models import Project

        project = self.db.query(Project).filter(Project.run_id == run_id).first()
        if not project:
            return {"mode": "local", "provider": "local"}
        return {
            "mode": getattr(project, "ai_mode", None) or getattr(project, "llm_provider", None) or "local",
            "provider": getattr(project, "llm_provider", None) or getattr(project, "ai_mode", None) or "local",
            "model": getattr(project, "llm_model", None) or "llama3",
            "url": getattr(project, "custom_api_base_url", None) or "http://127.0.0.1:11434",
            "key": getattr(project, "custom_api_key", None) or None,
            "local_provider": getattr(project, "local_provider", None),
            "timeout": 30,
        }

    def _target_language(self, run_id: str) -> str:
        return "java"

    @staticmethod
    def _resolve_source_path(run_id: str, project_file) -> Any:
        from pathlib import Path

        from paths import UPLOADS_DIR

        relative = str(getattr(project_file, "filepath", "") or "").replace("\\", "/")
        filename = str(getattr(project_file, "filename", "") or "")
        candidates = []
        if relative and ".." not in Path(relative).parts:
            candidates.append(UPLOADS_DIR / run_id / relative)
            candidates.append(UPLOADS_DIR / run_id / "local_repo" / relative)
        if filename:
            candidates.append(UPLOADS_DIR / run_id / filename)

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _run_async(coro) -> Any:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        return loop.run_until_complete(coro)
