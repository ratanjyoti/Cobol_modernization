import json
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from Agents.implementations.code_generator_agent import CodeGeneratorAgent
from Agents.infrastructure.codegen_context_builder import CodegenContextBuilder
from Agents.models.code_generation_models import (
    CodeGenerationResult,
    ConversionPlan,
    GeneratedFile,
    TargetLanguage,
    model_to_dict,
)
from Config.llm_config import settings
from Persistence.sqlite.models import Project
from services.project_scaffold_service import ProjectScaffoldService
from services.code_validation_service import CodeValidationService
from services.generation_quality_service import GenerationQualityService
from services.symbol_registry_service import SymbolRegistryService


class CodeGenerationProcess:
    """
    Generates modern code using saved conversion plans.

    Output folder:
      backend/output/generated_code/{run_id}/project/{target_language}/
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.context_builder = CodegenContextBuilder(db_session)
        self.scaffold_service = ProjectScaffoldService()
        self.validation_service = CodeValidationService()
        self.quality_service = GenerationQualityService(db_session)




    def validate_generated_project(
        self,
        run_id: str,
        target_language: str = "java",
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        project_dir = self._project_dir(run_id, target.value)

        self.scaffold_service.ensure_scaffold(project_dir, target.value)

        quality = self.quality_service.evaluate(
            run_id=run_id,
            target_language=target.value,
            project_dir=project_dir,
        )

        if not quality.get("success"):
            result = {
                "success": False,
                "status": "QUALITY_GATE_FAILED",
                "download_allowed": False,
                "target_language": target.value,
                "project_dir": str(project_dir),
                "command": "generation quality gate",
                "stdout": "",
                "stderr": "\n".join(quality.get("failures") or []),
                "returncode": 1,
                "quality_gate": quality,
            }

            validation_dir = self._output_root(run_id) / "validation" / target.value
            validation_dir.mkdir(parents=True, exist_ok=True)
            validation_path = validation_dir / "latest_validation.json"
            validation_path.write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return result

        result = self.validation_service.validate(project_dir, target.value)
        result["quality_gate"] = quality
        result["download_allowed"] = bool(result.get("success")) and bool(quality.get("success"))

        validation_dir = self._output_root(run_id) / "validation" / target.value
        validation_dir.mkdir(parents=True, exist_ok=True)

        validation_path = validation_dir / "latest_validation.json"
        validation_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return result

    def generate(
        self,
        run_id: str,
        target_language: str = "java",
        file_id: int | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        project = self.db.query(Project).filter(Project.run_id == run_id).first()

        if not project:
            raise ValueError(f"Project not found for run_id={run_id}")

        llm_config = self._project_ai_config(project)
        target = self._normalize_target(target_language)
        registry = SymbolRegistryService(self.db).get_registry(
            run_id=run_id,
            target_language=target.value,
        )

        if registry["type_mapping_count"] == 0 and registry["signature_count"] == 0:
            raise ValueError(
                "Symbol registry is empty. Finalize registry before code generation."
            )

        generator = CodeGeneratorAgent(llm_config=llm_config)

        file_contexts = (
            [self.context_builder.build_single_file_context(run_id, file_id)]
            if file_id is not None
            else self.context_builder.build_file_contexts(run_id)
        )

        if not file_contexts:
            return {
                "run_id": run_id,
                "target_language": target.value,
                "count": 0,
                "generated_files": [],
                "warnings": ["No COBOL or Telon files found for code generation."],
                "errors": [],
            }

        effective_project_id = project_id or run_id or "default"
        plan_warnings = self._ensure_conversion_plans(
            run_id=run_id,
            target_language=target.value,
            file_contexts=file_contexts,
            project_id=effective_project_id,
        )
        results: list[CodeGenerationResult] = []
        generated_files: list[GeneratedFile] = []
        errors: list[dict[str, Any]] = []

        if file_id is None:
            self._clean_project_output(run_id, target.value)
            self._clean_result_output(run_id, target.value)
        else:
            self._project_dir(run_id, target.value).mkdir(parents=True, exist_ok=True)

        self.scaffold_service.ensure_scaffold(
        self._project_dir(run_id, target.value),
        target.value,
    )

        for file_context in file_contexts:
            try:
                plan = self._load_plan(run_id, file_context.file_id, target.value)

                result = generator.generate_code(
                    file_context=file_context,
                    conversion_plan=plan,
                    project_id=effective_project_id,
                )

                self._save_result(run_id, target.value, file_context.file_id, result)

                for generated_file in result.generated_files:
                    self._write_generated_file(run_id, target.value, generated_file)
                    generated_files.append(generated_file)

                if result.status.value == "GENERATED" and not result.errors:
                    results.append(result)
                else:
                    errors.append({
                        "file_id": file_context.file_id,
                        "filename": file_context.filename,
                        "error": "; ".join(result.errors or ["Code generation failed."]),
                    })

            except Exception as exc:
                errors.append({
                    "file_id": file_context.file_id,
                    "filename": file_context.filename,
                    "error": str(exc),
                })

        all_results, all_generated_files = self._load_saved_generation_results(
            run_id=run_id,
            target_language=target.value,
        )
        if all_generated_files:
            self._clean_project_output(run_id, target.value)
            self._sync_project_from_generated_files(
                run_id=run_id,
                target_language=target.value,
                generated_files=all_generated_files,
            )
            results = all_results
            generated_files = all_generated_files

        manifest = self._write_manifest(
            run_id=run_id,
            target_language=target.value,
            results=results,
            generated_files=generated_files,
            errors=errors,
        )
        quality = self.quality_service.evaluate(
            run_id=run_id,
            target_language=target.value,
            project_dir=self._project_dir(run_id, target.value),
        )

        if not quality.get("success"):
            errors.append({
                "file_id": 0,
                "filename": "GENERATION_QUALITY_GATE",
                "error": "\n".join(quality.get("failures") or []),
            })
        manifest = self._write_manifest(
            run_id=run_id,
            target_language=target.value,
            results=results,
            generated_files=generated_files,
            errors=errors,
            quality_gate=quality,
        )

        return {
            "run_id": run_id,
            "target_language": target.value,
            "count": len(generated_files),
            "project_dir": str(self._project_dir(run_id, target.value)),
            "manifest": manifest,
            "generated_files": [model_to_dict(file) for file in generated_files],
            "warnings": plan_warnings,
            "quality_gate": quality,
            "errors": errors,
        }

    def _ensure_conversion_plans(
        self,
        run_id: str,
        target_language: str,
        file_contexts: list,
        project_id: str,
    ) -> list[str]:
        missing_contexts = [
            context
            for context in file_contexts
            if (
                not self._plan_exists(run_id, context.file_id, target_language)
                or self._plan_needs_regeneration(run_id, context.file_id, target_language)
            )
        ]

        if not missing_contexts:
            return []

        from Processes.conversion_planning_process import ConversionPlanningProcess

        planner = ConversionPlanningProcess(self.db)
        warnings = [
            f"Auto-created conversion plans for {len(missing_contexts)} file(s) before generation."
        ]

        for context in missing_contexts:
            self._delete_plan(run_id, context.file_id, target_language)
            response = planner.create_plans(
                run_id=run_id,
                target_language=target_language,
                file_id=context.file_id,
                project_id=project_id,
            )
            if response.get("errors"):
                warnings.append(
                    f"{context.filename}: {response.get('errors')}"
                )

        return warnings

    def _plan_exists(
        self,
        run_id: str,
        file_id: int,
        target_language: str,
    ) -> bool:
        return (
            self._output_root(run_id)
            / "plans"
            / target_language
            / f"{file_id}.json"
        ).exists()

    def _delete_plan(
        self,
        run_id: str,
        file_id: int,
        target_language: str,
    ) -> None:
        path = (
            self._output_root(run_id)
            / "plans"
            / target_language
            / f"{file_id}.json"
        )
        if path.exists():
            path.unlink()

    def _plan_needs_regeneration(
        self,
        run_id: str,
        file_id: int,
        target_language: str,
    ) -> bool:
        path = (
            self._output_root(run_id)
            / "plans"
            / target_language
            / f"{file_id}.json"
        )
        if not path.exists():
            return False

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return True

        summary = str(payload.get("summary") or "").lower()
        assumptions = " ".join(str(item).lower() for item in payload.get("assumptions") or [])
        if "data copybook" in summary:
            return False
        return "deterministic conversion plan" in summary or "fallback plan created" in assumptions

    def list_generated_files(
        self,
        run_id: str,
        target_language: str = "java",
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        project_dir = self._project_dir(run_id, target.value)

        files = []
        if project_dir.exists():
            for path in sorted(project_dir.rglob("*")):
                if path.is_file():
                    rel_path = path.relative_to(project_dir).as_posix()
                    files.append({
                        "path": rel_path,
                        "size": path.stat().st_size,
                    })

        return {
            "run_id": run_id,
            "target_language": target.value,
            "project_dir": str(project_dir),
            "count": len(files),
            "files": files,
        }

    def read_generated_file(
        self,
        run_id: str,
        target_language: str,
        path: str,
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        safe_path = self._safe_relative_path(path)
        project_dir = self._project_dir(run_id, target.value)
        file_path = project_dir / safe_path

        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"Generated file not found: {path}")

        return {
            "run_id": run_id,
            "target_language": target.value,
            "path": safe_path.as_posix(),
            "content": file_path.read_text(encoding="utf-8", errors="ignore"),
        }

    def create_zip(
        self,
        run_id: str,
        target_language: str = "java",
        require_valid: bool = True,
    ) -> Path:
        target = self._normalize_target(target_language)
        restored_project = self._restore_project_if_stale(run_id, target.value)
        project_dir = self._project_dir(run_id, target.value)

        if not project_dir.exists():
            raise FileNotFoundError(
                f"No generated project found for run_id={run_id}, target={target.value}"
            )

        if require_valid:
            if restored_project:
                raise ValueError(
                    "Generated project was rebuilt from saved generation results. "
                    "Validate the generated project again before downloading the verified ZIP."
                )

            validation = self._latest_validation(run_id, target.value)

            if not validation:
                raise ValueError(
                    "No validation result found. Validate the generated project before download."
                )

            if not validation.get("success"):
                raise ValueError(
                    "Generated project validation failed. Fix errors and validate again before download."
                )

            if not validation.get("download_allowed", validation.get("success")):
                raise ValueError(
                    "Generated project is not approved for download by the generation quality gate."
                )

            quality = self.quality_service.latest(run_id, target.value)
            if quality and not quality.get("success"):
                raise ValueError(
                    "Generated project quality gate failed. Regenerate code before download."
                )

        zip_base = self._output_root(run_id) / f"{target.value}_generated_code_only"
        zip_path = Path(
            shutil.make_archive(
                base_name=str(zip_base),
                format="zip",
                root_dir=str(project_dir),
            )
        )

        return zip_path

    def _restore_project_if_stale(self, run_id: str, target_language: str) -> bool:
        results, generated_files = self._load_saved_generation_results(run_id, target_language)
        if not generated_files:
            return False

        project_dir = self._project_dir(run_id, target_language)
        manifest_path = project_dir / "generation_manifest.json"
        manifest = self._load_json(manifest_path)
        expected_paths = {item.path for item in generated_files}
        existing_paths = {
            path.relative_to(project_dir).as_posix()
            for path in project_dir.rglob("*")
            if path.is_file()
        } if project_dir.exists() else set()

        stale = (
            not project_dir.exists()
            or not manifest
            or int(manifest.get("source_file_count") or 0) < len(results)
            or not expected_paths.issubset(existing_paths)
        )

        if not stale:
            return False

        self._clean_project_output(run_id, target_language)
        self._sync_project_from_generated_files(run_id, target_language, generated_files)
        self._write_manifest(run_id, target_language, results, generated_files, [])
        quality = self.quality_service.evaluate(run_id, target_language, project_dir)
        self._write_manifest(
            run_id,
            target_language,
            results,
            generated_files,
            [],
            quality_gate=quality,
        )
        return True

    def _latest_validation(
        self,
        run_id: str,
        target_language: str,
    ) -> dict[str, Any]:
        path = (
            self._output_root(run_id)
            / "validation"
            / target_language
            / "latest_validation.json"
        )

        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _load_plan(
        self,
        run_id: str,
        file_id: int,
        target_language: str,
    ) -> ConversionPlan:
        plan_path = (
            self._output_root(run_id)
            / "plans"
            / target_language
            / f"{file_id}.json"
        )

        if not plan_path.exists():
            raise FileNotFoundError(
                f"Missing conversion plan for file_id={file_id}. "
                f"Create plan first: POST /code-generation/{run_id}/plan?target_language={target_language}"
            )

        payload = json.loads(plan_path.read_text(encoding="utf-8"))

        return ConversionPlan(**payload)

    def _save_result(
        self,
        run_id: str,
        target_language: str,
        file_id: int,
        result: CodeGenerationResult,
    ):
        result_dir = self._output_root(run_id) / "results" / target_language
        result_dir.mkdir(parents=True, exist_ok=True)

        path = result_dir / f"{file_id}.json"
        path.write_text(
            json.dumps(model_to_dict(result), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_saved_generation_results(
        self,
        run_id: str,
        target_language: str,
    ) -> tuple[list[CodeGenerationResult], list[GeneratedFile]]:
        result_dir = self._output_root(run_id) / "results" / target_language
        if not result_dir.exists():
            return [], []

        results: list[CodeGenerationResult] = []
        generated_files: list[GeneratedFile] = []
        seen_paths: set[str] = set()

        for path in sorted(result_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                result = CodeGenerationResult(**payload)
            except Exception:
                continue

            if result.status.value != "GENERATED" or result.errors:
                continue

            results.append(result)
            for generated_file in result.generated_files:
                safe_path = self._normalize_generated_file_path(generated_file.path)
                if safe_path in seen_paths:
                    continue
                seen_paths.add(safe_path)
                generated_file.path = safe_path
                generated_files.append(generated_file)

        return results, generated_files

    def _sync_project_from_generated_files(
        self,
        run_id: str,
        target_language: str,
        generated_files: list[GeneratedFile],
    ) -> None:
        self.scaffold_service.ensure_scaffold(
            self._project_dir(run_id, target_language),
            target_language,
        )
        for generated_file in generated_files:
            self._write_generated_file(run_id, target_language, generated_file)

    def _write_generated_file(
        self,
        run_id: str,
        target_language: str,
        generated_file: GeneratedFile,
    ):
        project_dir = self._project_dir(run_id, target_language)
        safe_path = self._safe_relative_path(generated_file.path)
        full_path = project_dir / safe_path

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(
            generated_file.content,
            encoding="utf-8",
            errors="ignore",
        )

    def _write_manifest(
        self,
        run_id: str,
        target_language: str,
        results: list[CodeGenerationResult],
        generated_files: list[GeneratedFile],
        errors: list[dict[str, Any]],
        quality_gate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        manifest = {
            "run_id": run_id,
            "target_language": target_language,
            "generated_file_count": len(generated_files),
            "source_file_count": len(results),
            "files": [
                {
                    "path": item.path,
                    "language": item.language.value,
                    "file_type": item.file_type.value,
                    "source_file": item.source_file,
                }
                for item in generated_files
            ],
            "errors": errors,
            "quality_gate": quality_gate or {},
        }

        manifest_path = self._project_dir(run_id, target_language) / "generation_manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return manifest

    def _clean_project_output(self, run_id: str, target_language: str):
        project_dir = self._project_dir(run_id, target_language)

        if project_dir.exists():
            shutil.rmtree(project_dir)

        project_dir.mkdir(parents=True, exist_ok=True)

    def _clean_result_output(self, run_id: str, target_language: str):
        result_dir = self._output_root(run_id) / "results" / target_language

        if result_dir.exists():
            shutil.rmtree(result_dir)

        result_dir.mkdir(parents=True, exist_ok=True)

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
                f"Unsupported target language '{target_language}'. "
                "Use java, python, or csharp."
            )

        return aliases[value]

    @staticmethod
    def _output_root(run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "generated_code" / run_id

    @staticmethod
    def _project_dir(run_id: str, target_language: str) -> Path:
        return (
            CodeGenerationProcess._output_root(run_id)
            / "project"
            / target_language
        )

    @staticmethod
    def _safe_relative_path(path: str) -> Path:
        normalized = (path or "").replace("\\", "/").strip().lstrip("/")
        parts = [part for part in normalized.split("/") if part and part not in {".", ".."}]

        if not parts:
            raise ValueError("Generated file path is empty or unsafe.")

        return Path(*parts)

    @staticmethod
    def _normalize_generated_file_path(path: str) -> str:
        normalized = (path or "").replace("\\", "/").strip().lstrip("/")
        parts = [part for part in normalized.split("/") if part and part not in {".", ".."}]
        normalized = "/".join(parts)

        if normalized.endswith(".java") and not normalized.startswith("src/"):
            filename = Path(normalized).name
            package_path = ""

            if "/" in normalized:
                prefix = normalized.rsplit("/", 1)[0]
                package_path = prefix.replace(".", "/")

            if not package_path:
                package_path = "com/modernizer/migration"

            return f"src/main/java/{package_path}/{filename}"

        return normalized
