from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MigrationScopeDefinition:
    id: str
    title: str
    level: str
    static_token_range: str
    allowed_stages: tuple[str, ...]
    description: str


class MigrationScopeService:
    STAGE_LANGUAGE_DETECTION = "language_detection"
    STAGE_DEPENDENCY_MAPPING = "dependency_mapping"
    STAGE_GRAPH_BUILD = "graph_build"
    STAGE_CHUNKING = "chunking"
    STAGE_TECHNICAL_YAML = "technical_yaml"
    STAGE_PROCEDURAL_FLOW = "procedural_flow"
    STAGE_BUSINESS_LOGIC = "business_logic"
    STAGE_REVERSE_REPORT = "reverse_engineering_report"
    STAGE_DDD = "ddd_discovery"
    STAGE_CONVERSION_PLANNING = "conversion_planning"
    STAGE_CODE_GENERATION = "code_generation"
    STAGE_QUALITY_GATE = "quality_gate"
    STAGE_VALIDATION = "validation"
    STAGE_MIGRATION_REPORT = "migration_report"

    STAGES = (
        STAGE_LANGUAGE_DETECTION,
        STAGE_DEPENDENCY_MAPPING,
        STAGE_GRAPH_BUILD,
        STAGE_CHUNKING,
        STAGE_TECHNICAL_YAML,
        STAGE_PROCEDURAL_FLOW,
        STAGE_BUSINESS_LOGIC,
        STAGE_REVERSE_REPORT,
        STAGE_DDD,
        STAGE_CONVERSION_PLANNING,
        STAGE_CODE_GENERATION,
        STAGE_QUALITY_GATE,
        STAGE_VALIDATION,
        STAGE_MIGRATION_REPORT,
    )

    STAGE_LABELS = {
        STAGE_LANGUAGE_DETECTION: "Language Detection",
        STAGE_DEPENDENCY_MAPPING: "Dependency Mapping",
        STAGE_GRAPH_BUILD: "Graph Build",
        STAGE_CHUNKING: "Chunking",
        STAGE_TECHNICAL_YAML: "Technical YAML",
        STAGE_PROCEDURAL_FLOW: "Program Flow",
        STAGE_BUSINESS_LOGIC: "Business Logic",
        STAGE_REVERSE_REPORT: "Reverse Engineering Report",
        STAGE_DDD: "DDD Discovery",
        STAGE_CONVERSION_PLANNING: "Conversion Planning",
        STAGE_CODE_GENERATION: "Code Generation",
        STAGE_QUALITY_GATE: "Quality Gate",
        STAGE_VALIDATION: "Validation",
        STAGE_MIGRATION_REPORT: "Migration Report",
    }

    SCOPES = {
        "dependency_mapping": MigrationScopeDefinition(
            id="dependency_mapping",
            title="Dependency Mapping",
            level="Low",
            static_token_range="0 API Tokens",
            allowed_stages=(
                STAGE_LANGUAGE_DETECTION,
                STAGE_DEPENDENCY_MAPPING,
                STAGE_GRAPH_BUILD,
            ),
            description="Static graph of files, calls, copybooks, SQL, JCL, Telon, and unresolved references.",
        ),
        "program_logic": MigrationScopeDefinition(
            id="program_logic",
            title="Program Logic Extraction",
            level="Medium",
            static_token_range="20k - 70k Tokens",
            allowed_stages=(
                STAGE_LANGUAGE_DETECTION,
                STAGE_DEPENDENCY_MAPPING,
                STAGE_GRAPH_BUILD,
                STAGE_CHUNKING,
                STAGE_TECHNICAL_YAML,
                STAGE_PROCEDURAL_FLOW,
            ),
            description="AI explains procedural flow, branches, file I/O, calls, and execution paths.",
        ),
        "business_rules": MigrationScopeDefinition(
            id="business_rules",
            title="Business Rule Extraction",
            level="Medium",
            static_token_range="50k - 120k Tokens",
            allowed_stages=(
                STAGE_LANGUAGE_DETECTION,
                STAGE_DEPENDENCY_MAPPING,
                STAGE_GRAPH_BUILD,
                STAGE_CHUNKING,
                STAGE_TECHNICAL_YAML,
                STAGE_BUSINESS_LOGIC,
            ),
            description="AI extracts validations, calculations, decisions, workflows, and state changes.",
        ),
        "reverse_engineering": MigrationScopeDefinition(
            id="reverse_engineering",
            title="Full Reverse Engineering",
            level="High",
            static_token_range="80k - 180k Tokens",
            allowed_stages=(
                STAGE_LANGUAGE_DETECTION,
                STAGE_DEPENDENCY_MAPPING,
                STAGE_GRAPH_BUILD,
                STAGE_CHUNKING,
                STAGE_TECHNICAL_YAML,
                STAGE_PROCEDURAL_FLOW,
                STAGE_BUSINESS_LOGIC,
                STAGE_REVERSE_REPORT,
            ),
            description="AI-based legacy program analysis plus business logic extraction and reports.",
        ),
        "business_rules_ddd": MigrationScopeDefinition(
            id="business_rules_ddd",
            title="Business Rules (DDD)",
            level="High",
            static_token_range="150k - 300k Tokens",
            allowed_stages=(
                STAGE_LANGUAGE_DETECTION,
                STAGE_DEPENDENCY_MAPPING,
                STAGE_GRAPH_BUILD,
                STAGE_CHUNKING,
                STAGE_TECHNICAL_YAML,
                STAGE_BUSINESS_LOGIC,
                STAGE_DDD,
            ),
            description="Identifies domains, entities, bounded contexts, and service boundaries.",
        ),
        "full_migration_ddd": MigrationScopeDefinition(
            id="full_migration_ddd",
            title="Full Migration with DDD",
            level="Very High",
            static_token_range="250k - 600k+ Tokens",
            allowed_stages=(
                STAGE_LANGUAGE_DETECTION,
                STAGE_DEPENDENCY_MAPPING,
                STAGE_GRAPH_BUILD,
                STAGE_CHUNKING,
                STAGE_TECHNICAL_YAML,
                STAGE_PROCEDURAL_FLOW,
                STAGE_BUSINESS_LOGIC,
                STAGE_DDD,
                STAGE_CONVERSION_PLANNING,
                STAGE_CODE_GENERATION,
                STAGE_QUALITY_GATE,
                STAGE_VALIDATION,
                STAGE_MIGRATION_REPORT,
            ),
            description="End-to-end reverse engineering, DDD, code generation, validation, and report pipeline.",
        ),
    }

    def normalize_scope(self, scope: str | None) -> str:
        value = str(scope or "").strip().lower()
        return value if value in self.SCOPES else "reverse_engineering"

    def get_scope(self, scope: str | None) -> MigrationScopeDefinition:
        return self.SCOPES[self.normalize_scope(scope)]

    def is_stage_allowed(self, scope: str | None, stage: str) -> bool:
        return stage in self.get_scope(scope).allowed_stages

    def blocked_stages(self, scope: str | None) -> list[str]:
        definition = self.get_scope(scope)
        return [stage for stage in self.STAGES if stage not in definition.allowed_stages]

    def list_scopes(self) -> list[dict[str, Any]]:
        return [
            {
                "id": item.id,
                "title": item.title,
                "level": item.level,
                "token_range": item.static_token_range,
                "allowed_stages": list(item.allowed_stages),
                "description": item.description,
            }
            for item in self.SCOPES.values()
        ]

    def stage_labels(self) -> dict[str, str]:
        return dict(self.STAGE_LABELS)

    def estimate_tokens_for_run(self, db, run_id: str, scope: str | None) -> dict[str, Any]:
        from Persistence.sqlite.models import FileChunk, ProjectFile

        definition = self.get_scope(scope)
        files = db.query(ProjectFile).filter(ProjectFile.run_id == run_id).all()
        chunks = db.query(FileChunk).filter(FileChunk.run_id == run_id).all()

        source_chars = 0
        for file in files:
            size = getattr(file, "size", None) or 0
            if not size:
                size = self._source_file_size(run_id, getattr(file, "filepath", "") or getattr(file, "filename", ""))
            source_chars += int(size or 0)

        source_tokens = max(0, source_chars // 4)
        file_count = max(1, len(files))
        chunk_count = max(1, len(chunks) or len(files) or 1)
        stage_estimates: list[dict[str, Any]] = []

        def add(stage: str, prompt_overhead: int, output_tokens: int):
            if not self.is_stage_allowed(definition.id, stage):
                return
            per_unit_source = source_tokens // file_count
            estimated = (per_unit_source + prompt_overhead + output_tokens) * chunk_count
            stage_estimates.append(
                {
                    "stage": stage,
                    "label": self.STAGE_LABELS.get(stage, stage),
                    "estimated_tokens": int(estimated),
                    "prompt_overhead": prompt_overhead,
                    "expected_output_tokens": output_tokens,
                }
            )

        add(self.STAGE_TECHNICAL_YAML, 1200, 1200)
        add(self.STAGE_PROCEDURAL_FLOW, 1000, 1000)
        add(self.STAGE_BUSINESS_LOGIC, 1400, 1400)
        add(self.STAGE_DDD, 1800, 1800)
        add(self.STAGE_CONVERSION_PLANNING, 1800, 1200)
        add(self.STAGE_CODE_GENERATION, 2500, 2500)
        total = sum(item["estimated_tokens"] for item in stage_estimates)

        return {
            "run_id": run_id,
            "scope": definition.id,
            "title": definition.title,
            "level": definition.level,
            "static_token_range": definition.static_token_range,
            "allowed_stages": list(definition.allowed_stages),
            "blocked_stages": self.blocked_stages(definition.id),
            "stage_labels": self.stage_labels(),
            "file_count": len(files),
            "chunk_count": len(chunks),
            "estimated_total_tokens": total,
            "stage_estimates": stage_estimates,
            "is_static_only": total == 0,
        }

    def status_path(self, run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "status" / run_id / "scope_status.json"

    @staticmethod
    def _source_file_size(run_id: str, relative_path: str) -> int:
        if not relative_path or ".." in str(relative_path).replace("\\", "/").split("/"):
            return 0
        backend_root = Path(__file__).resolve().parents[1]
        candidate = backend_root / "data" / "uploads" / run_id / relative_path
        try:
            return candidate.stat().st_size if candidate.exists() else 0
        except OSError:
            return 0
