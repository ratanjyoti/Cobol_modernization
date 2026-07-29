import json
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from Agents.implementations.compile_fix_agent import CompileFixAgent
from Agents.infrastructure.codegen_context_builder import CodegenContextBuilder
from Agents.models.code_generation_models import TargetLanguage
from Config.llm_config import settings
from Persistence.sqlite.models import BusinessRule, ChunkAnalysis, Project


class CodeFixProcess:
    """
    Runs one compile-fix attempt.

    Current strategy:
    - Use latest validation error
    - Pick files likely related to error
    - Send each file to CompileFixAgent
    - Backup original file
    - Overwrite with fixed file
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.context_builder = CodegenContextBuilder(db_session)

    def fix_latest_validation_errors(
        self,
        run_id: str,
        target_language: str = "java",
        max_files: int = 3,
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        project = self.db.query(Project).filter(Project.run_id == run_id).first()

        if not project:
            raise ValueError(f"Project not found for run_id={run_id}")

        validation = self._load_latest_validation(run_id, target.value)
        error_text = self._validation_error_text(validation)

        if not error_text:
            return {
                "run_id": run_id,
                "target_language": target.value,
                "status": "SKIPPED",
                "message": "No validation error text found to fix.",
                "fixed_files": [],
            }

        project_dir = self._project_dir(run_id, target.value)
        candidate_files = self._find_candidate_files(
            project_dir=project_dir,
            target_language=target.value,
            error_text=error_text,
            max_files=max_files,
        )

        if not candidate_files:
            return {
                "run_id": run_id,
                "target_language": target.value,
                "status": "SKIPPED",
                "message": "No generated files matched the validation error.",
                "fixed_files": [],
                "error_text": error_text[:2000],
            }

        llm_config = self._project_ai_config(project)
        agent = CompileFixAgent(llm_config=llm_config)

        plans = self._load_plans(run_id, target.value)
        technical_yaml = self._load_technical_yaml(run_id)
        business_rules = self._load_business_rules(run_id)

        fixed_files = []
        errors = []

        fix_dir = self._output_root(run_id) / "fixes" / target.value
        fix_dir.mkdir(parents=True, exist_ok=True)

        for file_path in candidate_files:
            try:
                rel_path = file_path.relative_to(project_dir).as_posix()
                current_code = file_path.read_text(encoding="utf-8", errors="ignore")

                related_plan = self._select_related_plan(rel_path, plans)

                fix_result = agent.fix_file(
                    target_language=target.value,
                    project_id=run_id,
                    file_path=rel_path,
                    current_code=current_code,
                    error_text=error_text,
                    conversion_plan=related_plan,
                    technical_yaml=technical_yaml,
                    business_rules=business_rules,
                )

                backup_path = self._backup_file(run_id, target.value, file_path, project_dir)

                file_path.write_text(
                    fix_result["content"],
                    encoding="utf-8",
                    errors="ignore",
                )

                fixed_files.append({
                    "path": rel_path,
                    "backup_path": str(backup_path),
                    "fix_summary": fix_result.get("fix_summary", ""),
                    "warnings": fix_result.get("warnings", []),
                })

            except Exception as exc:
                errors.append({
                    "path": str(file_path),
                    "error": str(exc),
                })

        result = {
            "run_id": run_id,
            "target_language": target.value,
            "status": "FIXED" if fixed_files else "FAILED",
            "fixed_files": fixed_files,
            "errors": errors,
            "error_text": error_text[:4000],
        }

        result_path = fix_dir / "latest_fix.json"
        result_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return result

    def _find_candidate_files(
        self,
        project_dir: Path,
        target_language: str,
        error_text: str,
        max_files: int,
    ) -> list[Path]:
        extensions = {
            "java": [".java"],
            "python": [".py"],
            "csharp": [".cs"],
        }.get(target_language, [])

        all_files = [
            path
            for ext in extensions
            for path in project_dir.rglob(f"*{ext}")
            if path.is_file()
        ]

        if not all_files:
            return []

        error_lower = error_text.lower()
        scored: list[tuple[int, Path]] = []

        for path in all_files:
            rel = path.relative_to(project_dir).as_posix()
            score = 0

            if rel.lower() in error_lower:
                score += 100

            if path.name.lower() in error_lower:
                score += 80

            stem = path.stem.lower()
            if stem in error_lower:
                score += 50

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                class_or_func_score = self._content_match_score(content, error_lower)
                score += class_or_func_score
            except OSError:
                pass

            if score > 0:
                scored.append((score, path))

        if not scored:
            return all_files[:max_files]

        scored.sort(key=lambda item: item[0], reverse=True)
        return [path for _, path in scored[:max_files]]

    @staticmethod
    def _content_match_score(content: str, error_lower: str) -> int:
        score = 0

        for token in CodeFixProcess._important_tokens(error_lower):
            if token and token in content.lower():
                score += 3

        return min(score, 30)

    @staticmethod
    def _important_tokens(text: str) -> list[str]:
        raw_tokens = []
        current = []

        for char in text:
            if char.isalnum() or char in {"_", "."}:
                current.append(char)
            else:
                if current:
                    raw_tokens.append("".join(current))
                    current = []

        if current:
            raw_tokens.append("".join(current))

        return [
            token.lower()
            for token in raw_tokens
            if len(token) >= 5
            and token.lower()
            not in {
                "error",
                "failed",
                "compile",
                "compilation",
                "warning",
                "cannot",
                "symbol",
                "class",
                "method",
                "package",
            }
        ][:50]

    def _backup_file(
        self,
        run_id: str,
        target_language: str,
        file_path: Path,
        project_dir: Path,
    ) -> Path:
        rel_path = file_path.relative_to(project_dir)
        backup_root = self._output_root(run_id) / "backups" / target_language
        backup_path = backup_root / rel_path

        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, backup_path)

        return backup_path

    def _load_latest_validation(self, run_id: str, target_language: str) -> dict[str, Any]:
        path = (
            self._output_root(run_id)
            / "validation"
            / target_language
            / "latest_validation.json"
        )

        if not path.exists():
            raise FileNotFoundError(
                f"No validation result found. Run validation first for target={target_language}."
            )

        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _validation_error_text(validation: dict[str, Any]) -> str:
        return (
            str(validation.get("stderr") or "")
            + "\n\n"
            + str(validation.get("stdout") or "")
        ).strip()

    def _load_plans(self, run_id: str, target_language: str) -> list[dict[str, Any]]:
        plan_dir = self._output_root(run_id) / "plans" / target_language
        plans = []

        if not plan_dir.exists():
            return plans

        for path in sorted(plan_dir.glob("*.json")):
            try:
                plans.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue

        return plans

    @staticmethod
    def _select_related_plan(file_path: str, plans: list[dict[str, Any]]) -> dict[str, Any]:
        file_lower = file_path.lower()

        for plan in plans:
            for cls in plan.get("classes", []) or []:
                class_path = str(cls.get("file_path") or "").lower()
                class_name = str(cls.get("class_name") or "").lower()

                if class_path and class_path in file_lower:
                    return plan

                if class_name and class_name in file_lower:
                    return plan

        return plans[0] if plans else {}

    def _load_technical_yaml(self, run_id: str) -> str:
        rows = (
            self.db.query(ChunkAnalysis)
            .join(FileChunk, ChunkAnalysis.chunk_id == FileChunk.id)
            .filter(ChunkAnalysis.run_id == run_id)
            .order_by(FileChunk.file_id, FileChunk.chunk_index)
            .all()
        )

        blocks = []

        for row in rows:
            text = (
                getattr(row, "technical_yaml", None)
                or getattr(row, "analysis_yaml", None)
                or getattr(row, "yaml", None)
                or getattr(row, "technical_analysis", None)
                or getattr(row, "analysis_json", None)
                or getattr(row, "analysis_text", None)
                or ""
            )

            if text:
                chunk = self.db.query(FileChunk).filter(FileChunk.id == row.chunk_id).first()
                file_id = chunk.file_id if chunk else ""
                chunk_index = chunk.chunk_index if chunk else ""
                blocks.append(f"## File {file_id} Chunk {chunk_index}\n{text}")

        return "\n\n".join(blocks)[:80000]

    def _load_business_rules(self, run_id: str) -> list[dict[str, Any]]:
        rows = (
            self.db.query(BusinessRule)
            .filter(BusinessRule.run_id == run_id)
            .order_by(BusinessRule.id)
            .all()
        )

        return [
            {
                "rule_id": row.rule_id or str(row.id),
                "rule_text": row.rule_text or row.business_logic or "",
                "business_purpose": row.business_purpose or "",
                "functional_logic": row.functional_logic or row.business_logic or "",
                "technical_ref": row.technical_ref or row.technical_yaml or "",
                "file_id": row.file_id,
                "chunk_id": row.chunk_id,
            }
            for row in rows
        ]

    @staticmethod
    def _project_ai_config(project: Project) -> dict[str, Any]:
        mode = project.ai_mode or project.llm_provider or "openrouter"

        return {
            "mode": mode,
            "provider": project.llm_provider or mode,
            "key": project.custom_api_key or settings.OPENROUTER_API_KEY,
            "url": project.custom_api_base_url or settings.OPENROUTER_BASE_URL,
            "model": project.llm_model or settings.OPENROUTER_MODEL,
            "local_provider": getattr(project, "local_provider", None),
        }

    @staticmethod
    def _normalize_target(target_language: str) -> TargetLanguage:
        value = str(target_language or "java").strip().lower()

        aliases = {
            "java": TargetLanguage.JAVA,
            "quarkus": TargetLanguage.JAVA,
            "python": TargetLanguage.PYTHON,
            "py": TargetLanguage.PYTHON,
            "fastapi": TargetLanguage.PYTHON,
            "csharp": TargetLanguage.CSHARP,
            "c#": TargetLanguage.CSHARP,
            "cs": TargetLanguage.CSHARP,
            "aspnet": TargetLanguage.CSHARP,
            "dotnet": TargetLanguage.CSHARP,
        }

        if value not in aliases:
            raise ValueError(
                f"Unsupported target language '{target_language}'. Use java, python, or csharp."
            )

        return aliases[value]

    @staticmethod
    def _output_root(run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "generated_code" / run_id

    @staticmethod
    def _project_dir(run_id: str, target_language: str) -> Path:
        return (
            CodeFixProcess._output_root(run_id)
            / "project"
            / target_language
        )
