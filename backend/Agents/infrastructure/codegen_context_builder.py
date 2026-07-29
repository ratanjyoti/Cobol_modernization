import json
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.orm import Session

from Agents.models.code_generation_models import (
    BusinessRuleContext,
    ChunkCodegenContext,
    DependencyContext,
    FileCodegenContext,
    SourceLanguage,
)
from Persistence.sqlite.models import (
    BusinessRule,
    ChunkAnalysis,
    FileChunk,
    FileRelation,
    ProjectFile,
)
from paths import UPLOADS_DIR


class CodegenContextBuilder:
    """
    Builds file-level context for conversion planning and code generation.

    Inputs come from:
    - ProjectFile: uploaded source file metadata
    - FileChunk: smart chunks
    - ChunkAnalysis: technical YAML
    - BusinessRule: extracted business rules
    - FileRelation: dependency graph edges
    - storage/projects or uploads folder: raw source code
    """

    def __init__(self, db: Session):
        self.db = db

    def build_file_contexts(self, run_id: str) -> list[FileCodegenContext]:
        files = (
            self.db.query(ProjectFile)
            .filter(ProjectFile.run_id == run_id)
            .order_by(ProjectFile.id)
            .all()
        )

        contexts: list[FileCodegenContext] = []

        for project_file in files:
            if not self._is_supported_source_file(project_file.filename):
                continue

            lang = self._source_language(project_file.detected_lang, project_file.filename)

            if lang not in {SourceLanguage.COBOL, SourceLanguage.TELON}:
                continue

            raw_code = self._read_raw_source(run_id, project_file)

            chunks = (
                self.db.query(FileChunk)
                .filter(
                    FileChunk.run_id == run_id,
                    FileChunk.file_id == project_file.id,
                )
                .order_by(FileChunk.chunk_index)
                .all()
            )

            chunk_contexts = [
                self._build_chunk_context(run_id, project_file, chunk)
                for chunk in chunks
            ]

            technical_yaml = self._collect_technical_yaml(run_id, project_file.id)
            business_rules = self._collect_business_rules(run_id, project_file.id)
            dependencies = self._collect_dependencies(run_id, project_file)

            contexts.append(
                FileCodegenContext(
                    run_id=run_id,
                    file_id=project_file.id,
                    filename=project_file.filename,
                    filepath=project_file.filepath or project_file.filename,
                    source_language=lang,
                    raw_code=raw_code,
                    technical_yaml=technical_yaml,
                    business_rules=business_rules,
                    dependencies=dependencies,
                    chunks=chunk_contexts,
                )
            )

        return contexts

    def build_single_file_context(self, run_id: str, file_id: int) -> FileCodegenContext:
        project_file = (
            self.db.query(ProjectFile)
            .filter(ProjectFile.run_id == run_id, ProjectFile.id == file_id)
            .first()
        )

        if not project_file:
            raise ValueError(f"File not found for run_id={run_id}, file_id={file_id}")

        contexts = self.build_file_contexts(run_id)
        for context in contexts:
            if context.file_id == file_id:
                return context

        raise ValueError(
            f"File {project_file.filename} is not supported for code generation. "
            "Only COBOL and Telon are supported in this stage."
        )

    def _build_chunk_context(
        self,
        run_id: str,
        project_file: ProjectFile,
        chunk: FileChunk,
    ) -> ChunkCodegenContext:
        technical_yaml = self._collect_chunk_technical_yaml(run_id, chunk.id)
        raw_code = self._chunk_text(chunk)

        return ChunkCodegenContext(
            chunk_id=chunk.id,
            file_id=project_file.id,
            chunk_index=chunk.chunk_index or 0,
            filename=project_file.filename,
            filepath=project_file.filepath or project_file.filename,
            source_language=self._source_language(project_file.detected_lang, project_file.filename),
            raw_code=raw_code,
            technical_yaml=technical_yaml,
            business_rules=self._collect_business_rules(run_id, project_file.id, chunk.id),
            dependencies=self._collect_dependencies(run_id, project_file),
            context_packet={},
        )

    def _collect_technical_yaml(self, run_id: str, file_id: int) -> str:
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

        blocks = []

        for row, chunk in rows:
            yaml_text = self._first_attr(
                row,
                [
                    "technical_yaml",
                    "analysis_yaml",
                    "yaml",
                    "technical_analysis",
                    "analysis_json",
                    "analysis_text",
                ],
            )

            if yaml_text:
                blocks.append(
                    f"## Chunk {chunk.chunk_index}\n{str(yaml_text).strip()}"
                )

        return "\n\n".join(blocks).strip()

    def _collect_chunk_technical_yaml(self, run_id: str, chunk_id: int) -> str:
        row = (
            self.db.query(ChunkAnalysis)
            .filter(
                ChunkAnalysis.run_id == run_id,
                ChunkAnalysis.chunk_id == chunk_id,
            )
            .first()
        )

        if not row:
            return ""

        return str(
            self._first_attr(
                row,
                [
                    "technical_yaml",
                    "analysis_yaml",
                    "yaml",
                    "technical_analysis",
                    "analysis_json",
                    "analysis_text",
                ],
            )
            or ""
        )

    def _collect_business_rules(
        self,
        run_id: str,
        file_id: int,
        chunk_id: int | None = None,
    ) -> list[BusinessRuleContext]:
        query = self.db.query(BusinessRule).filter(
            BusinessRule.run_id == run_id,
            BusinessRule.file_id == file_id,
        )

        if chunk_id is not None:
            query = query.filter(BusinessRule.chunk_id == chunk_id)

        rows = query.order_by(BusinessRule.id).all()

        contexts = []
        for row in rows:
            contexts.append(
                BusinessRuleContext(
                    rule_id=row.rule_id or str(row.id),
                    rule_text=row.rule_text or row.business_logic or "",
                    business_purpose=row.business_purpose or "",
                    functional_logic=row.functional_logic or row.business_logic or "",
                    technical_ref=row.technical_ref or row.technical_yaml or "",
                )
            )

        return contexts

    def _collect_dependencies(
        self,
        run_id: str,
        project_file: ProjectFile,
    ) -> list[DependencyContext]:
        source_candidates = {
            project_file.filename,
            project_file.filepath,
            (project_file.filepath or "").replace("\\", "/"),
        }
        source_candidates = {value for value in source_candidates if value}

        rows = (
            self.db.query(FileRelation)
            .filter(FileRelation.run_id == run_id)
            .all()
        )

        dependencies = []

        for row in rows:
            source_file = row.source_file or ""
            if source_file not in source_candidates:
                continue

            dependencies.append(
                DependencyContext(
                    source_file=source_file,
                    target_item=row.target_item or "",
                    relation_type=row.relation_type or "REFERENCES",
                    context=getattr(row, "context", "") or "",
                    resolved=bool(getattr(row, "resolved", True)),
                )
            )

        return dependencies

    def _read_raw_source(self, run_id: str, project_file: ProjectFile) -> str:
        candidates = self._source_candidates(run_id, project_file)

        for candidate in candidates:
            try:
                if candidate.exists() and candidate.is_file():
                    return candidate.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

        chunk_texts = [
            self._chunk_text(chunk)
            for chunk in (
                self.db.query(FileChunk)
                .filter(
                    FileChunk.run_id == run_id,
                    FileChunk.file_id == project_file.id,
                )
                .order_by(FileChunk.chunk_index)
                .all()
            )
        ]

        return "\n\n".join(text for text in chunk_texts if text).strip()

    def _source_candidates(self, run_id: str, project_file: ProjectFile) -> list[Path]:
        project_dir = UPLOADS_DIR / run_id
        candidates: list[Path] = []

        raw_values = [
            project_file.filepath,
            project_file.filename,
            f"local_repo/{project_file.filepath}" if project_file.filepath else "",
            f"local_repo/{project_file.filename}" if project_file.filename else "",
        ]

        for raw_value in raw_values:
            safe_path = self._safe_relative_path(raw_value)
            if safe_path:
                candidates.append(project_dir / safe_path)

        return candidates

    @staticmethod
    def _safe_relative_path(value: str | None) -> Path | None:
        normalized = (value or "").replace("\\", "/").strip("/")
        if not normalized:
            return None

        parts = [part for part in normalized.split("/") if part]
        if not parts or any(part in {".", ".."} for part in parts):
            return None

        path = Path(*parts)
        if path.is_absolute():
            return None

        return path

    @staticmethod
    def _is_supported_source_file(filename: str | None) -> bool:
        name = (filename or "").lower().strip()
        return name.endswith((".cbl", ".cob", ".cpy", ".tel", ".tln"))

    @staticmethod
    def _source_language(detected_lang: str | None, filename: str | None) -> SourceLanguage:
        lang = (detected_lang or "").lower().strip()
        name = (filename or "").lower().strip()

        if "telon" in lang or name.endswith((".tel", ".tln")):
            return SourceLanguage.TELON

        if "cobol" in lang or name.endswith((".cbl", ".cob", ".cpy")):
            return SourceLanguage.COBOL

        if "jcl" in lang or name.endswith(".jcl"):
            return SourceLanguage.JCL

        return SourceLanguage.UNKNOWN

    @staticmethod
    def _chunk_text(chunk: FileChunk) -> str:
        return str(
            CodegenContextBuilder._first_attr(
                chunk,
                [
                    "content",
                    "raw_code",
                    "chunk_text",
                    "text",
                    "source_code",
                    "code",
                ],
            )
            or ""
        )

    @staticmethod
    def _first_attr(obj: Any, names: Iterable[str]) -> Any:
        for name in names:
            if hasattr(obj, name):
                value = getattr(obj, name)
                if value not in (None, ""):
                    return value
        return None

    @staticmethod
    def to_jsonable(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        if isinstance(value, list):
            return [CodegenContextBuilder.to_jsonable(item) for item in value]
        if isinstance(value, dict):
            return {
                key: CodegenContextBuilder.to_jsonable(item)
                for key, item in value.items()
            }
        return value

    @staticmethod
    def to_pretty_json(value: Any) -> str:
        return json.dumps(CodegenContextBuilder.to_jsonable(value), indent=2, ensure_ascii=False)
