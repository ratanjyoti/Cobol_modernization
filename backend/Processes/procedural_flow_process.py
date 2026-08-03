from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from Agents.implementations.procedural_flow_extractor import ProceduralFlowExtractor
from Persistence.sqlite.models import ChunkAnalysis, FileChunk, Project, ProjectFile
from paths import UPLOADS_DIR


class ProceduralFlowProcess:
    """
    Owns procedural-flow orchestration.

    Loads project files, technical YAML, and raw source, then persists compact
    per-file JSON outputs under backend/output/procedural_flow/<run_id>.
    """

    SUPPORTED_EXTENSIONS = (
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
    SUPPORTED_LANGUAGES = {"cobol", "copybook", "jcl", "telon", "pli", "pl/i", "pl1", "sql", "db2"}

    def __init__(self, db_session: Session):
        self.db = db_session

    def extract_all(self, run_id: str) -> dict[str, Any]:
        project = self.db.query(Project).filter_by(run_id=run_id).first()
        if not project:
            raise ValueError(f"Project not found for run_id={run_id}")

        extractor = ProceduralFlowExtractor(llm_config=self._llm_config(project))
        files = (
            self.db.query(ProjectFile)
            .filter(ProjectFile.run_id == run_id)
            .order_by(ProjectFile.id)
            .all()
        )

        results = []
        completed = 0
        skipped = 0
        failed = 0

        for project_file in files:
            try:
                source_code = self._load_source_code_for_file(project_file)
                if not self._is_supported_source(project_file, source_code):
                    skipped += 1
                    results.append(
                        {
                            "file_id": project_file.id,
                            "file_name": self._file_name(project_file),
                            "detected_language": self._detected_language(project_file),
                            "status": "skipped",
                            "reason": "unsupported_or_empty_source",
                        }
                    )
                    continue

                flow = extractor.extract(
                    file_id=project_file.id,
                    file_name=self._file_name(project_file),
                    detected_language=self._detected_language(project_file),
                    technical_yaml=self._load_technical_yaml_for_file(run_id, project_file.id),
                    source_code=source_code,
                )
                self._write_flow(run_id, project_file.id, flow)
                completed += 1
                results.append(self._summary_item(flow, "completed"))
            except Exception as exc:
                failed += 1
                results.append(
                    {
                        "file_id": getattr(project_file, "id", None),
                        "file_name": self._file_name(project_file),
                        "detected_language": self._detected_language(project_file),
                        "status": "failed",
                        "error": str(exc),
                    }
                )

        summary = {
            "run_id": run_id,
            "total_files": len(files),
            "completed_files": completed,
            "skipped_files": skipped,
            "failed_files": failed,
            "results": results,
        }
        self._write_summary(run_id, summary)
        return summary

    def list_flows(self, run_id: str) -> dict[str, Any]:
        flow_dir = self._flow_dir(run_id)
        flows = []

        if not flow_dir.exists():
            return {"run_id": run_id, "flows": []}

        for path in sorted(flow_dir.glob("*.json"), key=lambda item: item.name):
            if path.name == "summary.json":
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                flows.append(self._summary_item(payload, "completed"))
            except Exception:
                continue

        return {"run_id": run_id, "flows": flows}

    def get_flow(self, run_id: str, file_id: int | str) -> dict[str, Any]:
        path = self._flow_dir(run_id) / f"{file_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Procedural flow not found for run_id={run_id}, file_id={file_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _summary_item(self, payload: dict[str, Any], status: str) -> dict[str, Any]:
        external_operations = payload.get("external_operations") or []
        external_calls = payload.get("external_calls") or []
        return {
            "file_id": payload.get("file_id"),
            "file_name": payload.get("file_name", ""),
            "detected_language": payload.get("detected_language", ""),
            "status": status,
            "entry_point": (payload.get("entry_point") or {}).get("name", ""),
            "execution_steps": len(payload.get("execution_flow") or []),
            "decision_count": len(payload.get("decision_branches") or []),
            "loop_count": len(payload.get("loops") or []),
            "data_movement_count": len(payload.get("data_movement") or []),
            "external_operation_count": len(payload.get("external_operations") or []),
            "external_call_count": len(payload.get("external_calls") or []),
            "external_operations": [
                str(item.get("operation_type") or item.get("name") or "")
                for item in external_operations
                if isinstance(item, dict)
            ],
            "external_calls": [
                str(item.get("program") or item.get("name") or "")
                for item in external_calls
                if isinstance(item, dict)
            ],
            "exit_path_count": len(payload.get("exit_paths") or []),
            "fallback_used": bool(payload.get("fallback_used", False)),
            "fallback_reason": payload.get("fallback_reason", ""),
        }

    def _llm_config(self, project: Project) -> dict[str, Any]:
        return {
            "mode": getattr(project, "ai_mode", None) or getattr(project, "llm_provider", None) or "local",
            "provider": getattr(project, "llm_provider", None) or getattr(project, "ai_mode", None) or "local",
            "model": getattr(project, "llm_model", None) or getattr(project, "model", None) or "llama3",
            "url": (
                getattr(project, "custom_api_base_url", None)
                or getattr(project, "api_base_url", None)
                or "http://127.0.0.1:11434"
            ),
            "key": getattr(project, "custom_api_key", None) or getattr(project, "api_key", None) or None,
            "timeout": 180,
        }

    def _load_technical_yaml_for_file(self, run_id: str, file_id: int) -> str:
        rows = (
            self.db.query(ChunkAnalysis, FileChunk)
            .join(FileChunk, ChunkAnalysis.chunk_id == FileChunk.id)
            .filter(ChunkAnalysis.run_id == run_id, FileChunk.file_id == file_id)
            .order_by(FileChunk.chunk_index)
            .all()
        )

        parts = []
        for analysis, chunk in rows:
            technical_yaml = getattr(analysis, "technical_yaml", "") or ""
            if technical_yaml.strip():
                parts.append(f"# chunk_id: {chunk.id}, chunk_index: {chunk.chunk_index}\n{technical_yaml}")

        return "\n\n---\n\n".join(parts)

    def _load_source_code_for_file(self, project_file: ProjectFile) -> str:
        rel = (project_file.filepath or project_file.filename or "").replace("\\", "/").strip("/")
        if rel and ".." not in rel.split("/"):
            candidates = [
                UPLOADS_DIR / project_file.run_id / rel,
                UPLOADS_DIR / project_file.run_id / "local_repo" / rel,
                UPLOADS_DIR / project_file.run_id / (project_file.filename or ""),
            ]

            for candidate in candidates:
                try:
                    if candidate.exists() and candidate.is_file():
                        return candidate.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

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

    def _is_supported_source(self, project_file: ProjectFile, source_code: str) -> bool:
        filename = (project_file.filepath or project_file.filename or "").lower()
        language = (project_file.detected_lang or "").lower()
        return bool(source_code and source_code.strip()) and (
            filename.endswith(self.SUPPORTED_EXTENSIONS)
            or language in self.SUPPORTED_LANGUAGES
            or language.startswith("cobol")
            or language.startswith("telon")
        )

    def _file_name(self, project_file: ProjectFile) -> str:
        return (
            getattr(project_file, "filename", None)
            or getattr(project_file, "file_name", None)
            or getattr(project_file, "relative_path", None)
            or f"file_{getattr(project_file, 'id', '')}"
        )

    def _detected_language(self, project_file: ProjectFile) -> str:
        return (
            getattr(project_file, "detected_language", None)
            or getattr(project_file, "detected_lang", None)
            or getattr(project_file, "language", None)
            or "unknown"
        )

    def _flow_dir(self, run_id: str) -> Path:
        return Path(__file__).resolve().parents[1] / "output" / "procedural_flow" / run_id

    def _write_flow(self, run_id: str, file_id: int | str, flow: dict[str, Any]) -> None:
        path = self._flow_dir(run_id) / f"{file_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(flow, indent=2), encoding="utf-8")

    def _write_summary(self, run_id: str, summary: dict[str, Any]) -> None:
        path = self._flow_dir(run_id) / "summary.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
