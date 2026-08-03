import json
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from Agents.implementations.agentic_code_conversion_orchestrator import (
    AgenticCodeConversionOrchestrator,
)
from Agents.implementations.code_generator_agent import CodeGeneratorAgent
from Agents.infrastructure.codegen_context_builder import CodegenContextBuilder
from Agents.infrastructure.constitution_loader import ConstitutionLoader
from Agents.models.code_generation_models import (
    CodeGenerationStatus,
    CodeGenerationResult,
    ConversionPlan,
    GeneratedFile,
    GeneratedFileType,
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

        quality_report = self.quality_service.run_quality_gate(
            run_id=run_id,
            target_language=target.value,
        )

        if not quality_report.get("success"):
            validation = {
                "success": False,
                "status": "QUALITY_GATE_FAILED",
                "target_language": target.value,
                "project_dir": str(project_dir),
                "command": ["generation quality gate"],
                "command_text": "generation quality gate",
                "stdout": "",
                "stderr": "\n".join(quality_report.get("failures", [])),
                "returncode": -1,
                "download_allowed": False,
                "quality_gate": quality_report,
            }
        else:
            validation = self.validation_service.validate(
                project_dir=project_dir,
                target_language=target.value,
            )
            validation["quality_gate"] = quality_report
            validation["download_allowed"] = bool(
                validation.get("success") and quality_report.get("success")
            )

        validation_path = (
            self._output_root(run_id)
            / "validation"
            / target.value
            / "latest_validation.json"
        )

        validation_path.parent.mkdir(parents=True, exist_ok=True)
        validation_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")

        return validation

    def _planned_file_ids(
        self,
        run_id: str,
        target_language: str,
    ) -> list[int]:
        plan_dir = self._output_root(run_id) / "plans" / target_language

        if not plan_dir.exists():
            return []

        file_ids: list[int] = []

        for path in sorted(plan_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                file_id = payload.get("file_id")

                if file_id is not None:
                    file_ids.append(int(file_id))
                    continue

                # fallback: filename itself is usually {file_id}.json
                file_ids.append(int(path.stem))
            except Exception:
                continue

        return sorted(set(file_ids))

    def generate(
        self,
        run_id: str,
        target_language: str = "java",
        file_id: int | None = None,
        project_id: str | None = None,
        clean_output: bool = True,
    ) -> dict[str, Any]:
        project = self.db.query(Project).filter(Project.run_id == run_id).first()

        if not project:
            raise ValueError(f"Project not found for run_id={run_id}")

        llm_config = self._project_ai_config(project)

        registry = SymbolRegistryService(self.db).get_registry(
            run_id=run_id,
            target_language=target_language,
        )

        if registry["type_mapping_count"] == 0 and registry["signature_count"] == 0:
            raise ValueError(
                "Symbol registry is empty. Finalize registry before code generation."
            )

        target = self._normalize_target(target_language)
        legacy_generator = CodeGeneratorAgent(llm_config=llm_config)
        orchestrator = self._build_agentic_code_orchestrator(project)

        if file_id is not None:
            file_contexts = [
                self.context_builder.build_single_file_context(run_id, file_id)
            ]
        else:
            planned_ids = self._planned_file_ids(run_id, target.value)

            if planned_ids:
                file_contexts = []
                for planned_file_id in planned_ids:
                    try:
                        file_contexts.append(
                            self.context_builder.build_single_file_context(
                                run_id,
                                planned_file_id,
                            )
                        )
                    except Exception:
                        continue
            else:
                file_contexts = self.context_builder.build_file_contexts(run_id)

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
        results: list[CodeGenerationResult] = []
        generated_files: list[GeneratedFile] = []
        errors: list[dict[str, Any]] = []
        processed_source_files: list[dict[str, Any]] = []

        if clean_output:
            self._clean_project_output(run_id, target.value)
            self._clean_result_output(run_id, target.value)

        project_dir = self._project_dir(run_id, target.value)
        project_dir.mkdir(parents=True, exist_ok=True)

        self.scaffold_service.ensure_scaffold(
            project_dir,
            target.value,
        )

        for file_context in file_contexts:
            processed_source_files.append(
                {
                    "file_id": file_context.file_id,
                    "filename": file_context.filename,
                }
            )

            try:
                plan = self._load_plan(run_id, file_context.file_id, target.value)
                result = self._generate_with_agentic_orchestrator(
                    run_id=run_id,
                    project=project,
                    file_context=file_context,
                    conversion_plan=plan,
                    target=target,
                    registry=registry,
                    orchestrator=orchestrator,
                    legacy_generator=legacy_generator,
                    project_id=effective_project_id,
                )

                self._save_result(run_id, target.value, file_context.file_id, result)

                for generated_file in result.generated_files:
                    self._write_generated_file(run_id, target.value, generated_file)
                    generated_files.append(generated_file)

                results.append(result)

            except Exception as exc:
                errors.append({
                    "file_id": file_context.file_id,
                    "filename": file_context.filename,
                    "error": str(exc),
                })

        manifest = self._write_manifest(
            run_id=run_id,
            target_language=target.value,
            results=results,
            generated_files=generated_files,
            errors=errors,
            processed_source_files=processed_source_files,
        )

        quality_report = self.quality_service.evaluate(
            run_id=run_id,
            target_language=target.value,
        )

        return {
            "run_id": run_id,
            "target_language": target.value,
            "count": len(generated_files),
            "processed_source_file_count": len(processed_source_files),
            "processed_source_files": processed_source_files,
            "project_dir": str(self._project_dir(run_id, target.value)),
            "manifest": manifest,
            "generated_files": [model_to_dict(file) for file in generated_files],
            "errors": errors,
            "quality_gate": quality_report,
        }

    def _build_agentic_code_orchestrator(
        self,
        project: Project,
    ) -> AgenticCodeConversionOrchestrator:
        llm_config = self._project_ai_config(project)
        return AgenticCodeConversionOrchestrator(llm_config=llm_config)

    def _generate_with_agentic_orchestrator(
        self,
        *,
        run_id: str,
        project: Project,
        file_context: Any,
        conversion_plan: ConversionPlan,
        target: TargetLanguage,
        registry: dict[str, Any],
        orchestrator: AgenticCodeConversionOrchestrator,
        legacy_generator: CodeGeneratorAgent,
        project_id: str,
    ) -> CodeGenerationResult:
        profile = ConstitutionLoader().load_profile(target)
        procedural_flow = self._load_procedural_flow_for_file(
            run_id=run_id,
            file_id=file_context.file_id,
        )
        conversion_context = self._build_agentic_conversion_context(
            project=project,
            file_context=file_context,
            conversion_plan=conversion_plan,
            target=target,
            target_framework=conversion_plan.target_framework or profile.framework,
            registry=registry,
            procedural_flow=procedural_flow,
            constitution_profile=profile,
        )

        agentic_result = orchestrator.convert(conversion_context)
        generated_files = self._agentic_conversion_to_generated_files(
            agentic_result=agentic_result,
            file_context=file_context,
            target=target,
            legacy_generator=legacy_generator,
        )

        if not generated_files:
            fallback_result = legacy_generator.generate_code(
                run_id=run_id,
                file_context=file_context,
                conversion_plan=conversion_plan,
                target=target,
                project_id=project_id,
                registry=registry,
            )
            fallback_result.warnings.append(
                "Agentic code conversion produced no files; legacy generator fallback was used."
            )
            return fallback_result

        warnings = [str(item) for item in agentic_result.get("warnings", []) if item]
        if agentic_result.get("fallback_used"):
            reason = agentic_result.get("fallback_reason") or "LLM conversion failed."
            warnings.append(f"Agentic conversion fallback used: {reason}")

        flow_used = bool(procedural_flow)
        notes = [
            f"Generated by {agentic_result.get('agent_name') or 'AgenticCodeConversionOrchestrator'}.",
            f"Procedural flow used: {flow_used}.",
            "Technical YAML, business rules, dependencies, and locked registry were supplied to the conversion agent.",
        ]
        for generated_file in generated_files:
            generated_file.notes.extend(notes)

        return CodeGenerationResult(
            run_id=run_id,
            target_language=target,
            target_framework=conversion_plan.target_framework or profile.framework,
            status=CodeGenerationStatus.GENERATED,
            summary=agentic_result.get("summary") or "Agentic code conversion completed.",
            generated_files=generated_files,
            unresolved_items=[
                str(item) for item in agentic_result.get("unresolved_items", []) if item
            ],
            warnings=warnings,
            errors=[],
        )

    def _build_agentic_conversion_context(
        self,
        *,
        project: Project,
        file_context: Any,
        conversion_plan: ConversionPlan,
        target: TargetLanguage,
        target_framework: str,
        registry: dict[str, Any],
        procedural_flow: dict[str, Any],
        constitution_profile: Any,
    ) -> dict[str, Any]:
        return {
            "run_id": file_context.run_id,
            "project_id": getattr(project, "project_id", None) or project.run_id,
            "file_id": file_context.file_id,
            "file_name": file_context.filename,
            "file_path": file_context.filepath,
            "source_language": self._enum_value(file_context.source_language),
            "target_language": target.value,
            "target_framework": target_framework,
            "conversion_plan": self._safe_model_dump(conversion_plan),
            "technical_yaml": file_context.technical_yaml,
            "business_rules": self._safe_model_dump(file_context.business_rules),
            "procedural_flow": procedural_flow,
            "dependencies": self._safe_model_dump(file_context.dependencies),
            "locked_symbols": registry,
            "source_code": file_context.raw_code,
            "constitution_profile": self._safe_model_dump(constitution_profile),
        }

    def _agentic_conversion_to_generated_files(
        self,
        *,
        agentic_result: dict[str, Any],
        file_context: Any,
        target: TargetLanguage,
        legacy_generator: CodeGeneratorAgent,
    ) -> list[GeneratedFile]:
        generated_files: list[GeneratedFile] = []
        seen_paths: set[str] = set()

        for item in agentic_result.get("files") or []:
            if not isinstance(item, dict):
                continue

            raw_path = str(item.get("file_path") or item.get("path") or "").strip()
            content = str(item.get("content") or "").strip()
            if not raw_path or not content:
                continue

            file_type = self._generated_file_type(item.get("file_type"))
            safe_path = legacy_generator.plan_sanitizer.sanitize_file_path_for_generated_file(
                path=raw_path,
                source_file=file_context.filename,
                target_language=target.value,
                file_type=file_type.value,
            )
            safe_path = self._normalize_generated_file_path(safe_path)

            if safe_path in seen_paths:
                continue
            seen_paths.add(safe_path)

            generated_files.append(
                GeneratedFile(
                    path=safe_path,
                    language=target,
                    file_type=file_type,
                    content=content.rstrip() + "\n",
                    source_file=file_context.filename,
                    notes=[
                        str(item.get("description") or "").strip(),
                        *[
                            f"Source reference: {ref}"
                            for ref in item.get("source_references", []) or []
                            if ref
                        ],
                    ],
                )
            )

        return generated_files

    def _load_procedural_flow_for_file(
        self,
        run_id: str,
        file_id: int,
    ) -> dict[str, Any]:
        backend_root = Path(__file__).resolve().parents[1]
        candidates = [
            backend_root / "output" / "procedural_flow" / run_id / f"{file_id}.json",
            backend_root / "output" / "program_flow" / run_id / f"{file_id}.json",
        ]

        for path in candidates:
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except Exception:
                continue

        return {}

    def _generated_file_type(self, value: Any) -> GeneratedFileType:
        text = str(value or "other").lower().strip()
        aliases = {
            "model": GeneratedFileType.DOMAIN,
            "domain": GeneratedFileType.DOMAIN,
            "entity": GeneratedFileType.DOMAIN,
            "service": GeneratedFileType.SERVICE,
            "controller": GeneratedFileType.CONTROLLER,
            "resource": GeneratedFileType.RESOURCE,
            "router": GeneratedFileType.ROUTER,
            "repository": GeneratedFileType.REPOSITORY,
            "dto": GeneratedFileType.DTO,
            "schema": GeneratedFileType.DTO,
            "config": GeneratedFileType.CONFIG,
            "test": GeneratedFileType.TEST,
            "exception": GeneratedFileType.EXCEPTION,
            "readme": GeneratedFileType.README,
        }
        return aliases.get(text, GeneratedFileType.OTHER)

    def _safe_model_dump(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._safe_model_dump(item) for item in value]
        if isinstance(value, dict):
            return {key: self._safe_model_dump(item) for key, item in value.items()}
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        if hasattr(value, "value"):
            return value.value
        return value

    @staticmethod
    def _enum_value(value: Any) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value or "")

    def _extract_missing_planned_files(
        self,
        quality_report: dict[str, Any] | None,
    ) -> list[str]:
        if not quality_report:
            return []

        missing = quality_report.get("missing_planned_files")

        if isinstance(missing, list):
            return [str(item).replace("\\", "/") for item in missing if item]

        failures = quality_report.get("failures") or []
        extracted: list[str] = []

        for failure in failures:
            text = str(failure)

            marker = "Generated project is missing planned class files:"
            if marker not in text:
                continue

            right = text.split(marker, 1)[1]
            for item in right.split(","):
                clean = item.strip().replace("\\", "/")
                if clean:
                    extracted.append(clean)

        return sorted(set(extracted))

    def _latest_quality_report(
        self,
        run_id: str,
        target_language: str,
    ) -> dict[str, Any]:
        path = (
            self._output_root(run_id)
            / "quality"
            / target_language
            / "latest_quality.json"
        )

        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def regenerate_missing_files(
        self,
        run_id: str,
        target_language: str = "java",
        missing_files: list[str] | None = None,
        project_id: str | None = None,
        max_files: int = 20,
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)

        latest_quality = self._latest_quality_report(run_id, target.value)
        missing = missing_files or self._extract_missing_planned_files(latest_quality)

        missing = [item.replace("\\", "/") for item in missing if item]
        missing = sorted(set(missing))

        if not missing:
            return {
                "run_id": run_id,
                "target_language": target.value,
                "regenerated": 0,
                "message": "No missing planned files found.",
                "missing_files": [],
            }

        plan_index = self._plan_index_by_expected_file(run_id, target.value)

        file_ids: list[int] = []
        unresolved_missing: list[str] = []

        for missing_file in missing:
            file_id = plan_index.get(missing_file)

            if file_id is None:
                unresolved_missing.append(missing_file)
                continue

            file_ids.append(file_id)

        file_ids = sorted(set(file_ids))[:max_files]

        regenerated_results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for file_id in file_ids:
            try:
                result = self.generate(
                    run_id=run_id,
                    target_language=target.value,
                    file_id=file_id,
                    project_id=project_id,
                    clean_output=False,
                )

                regenerated_results.append(
                    {
                        "file_id": file_id,
                        "generated_count": result.get("count", 0),
                        "errors": result.get("errors", []),
                    }
                )

            except Exception as exc:
                errors.append(
                    {
                        "file_id": file_id,
                        "error": str(exc),
                    }
                )

        quality_report = self.quality_service.run_quality_gate(
            run_id=run_id,
            target_language=target.value,
        )

        return {
            "run_id": run_id,
            "target_language": target.value,
            "requested_missing_files": missing,
            "unresolved_missing_files": unresolved_missing,
            "regenerated_file_ids": file_ids,
            "regenerated": len(regenerated_results),
            "results": regenerated_results,
            "errors": errors,
            "quality_gate": quality_report,
        }

    def _plan_index_by_expected_file(
        self,
        run_id: str,
        target_language: str,
    ) -> dict[str, int]:
        plan_dir = self._output_root(run_id) / "plans" / target_language

        if not plan_dir.exists():
            return {}

        index: dict[str, int] = {}

        for path in sorted(plan_dir.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                file_id = payload.get("file_id")

                if file_id is None:
                    file_id = int(path.stem)

                for cls in payload.get("classes", []) or []:
                    if not isinstance(cls, dict):
                        continue

                    expected = (
                        cls.get("file_path")
                        or cls.get("path")
                        or ""
                    )

                    expected = str(expected).replace("\\", "/").strip()

                    if expected:
                        index[expected] = int(file_id)

            except Exception:
                continue

        return index

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
        processed_source_files: list[dict[str, Any]] | None = None,
        quality_gate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        processed_source_files = processed_source_files or []

        manifest = {
            "run_id": run_id,
            "target_language": target_language,
            "generated_file_count": len(generated_files),
            "source_file_count": len(results),
            "processed_source_file_count": len(processed_source_files),
            "processed_source_files": processed_source_files,
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
