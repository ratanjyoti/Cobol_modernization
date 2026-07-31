import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from Processes.conversion_planning_process import ConversionPlanningProcess
from Processes.code_generation_process import CodeGenerationProcess
from Processes.method_body_repair_process import MethodBodyRepairProcess
from services.symbol_registry_service import SymbolRegistryService
from services.migration_report_service import MigrationReportService


class FullCodeGenerationPipeline:
    """
    Runs the complete code generation workflow behind one button.

    User-facing flow:
        Generate Working Code

    Internal flow:
        registry -> plan -> generate -> quality gate -> repair -> validate -> report
    """

    def __init__(self, db):
        self.db = db

    def run(
        self,
        run_id: str,
        target_language: str = "java",
        project_id: str | None = None,
        max_missing_rounds: int = 2,
        max_method_repair_rounds: int = 2,
    ) -> dict[str, Any]:
        target_language = (target_language or "java").lower().strip()
        project_id = project_id or run_id

        self._write_status(
            run_id,
            target_language,
            status="RUNNING",
            stage="Starting code generation pipeline",
            progress=1,
        )

        final_result: dict[str, Any] = {
            "run_id": run_id,
            "target_language": target_language,
            "status": "RUNNING",
            "download_allowed": False,
            "steps": [],
            "errors": [],
        }

        try:
            # 1. Registry
            self._stage(run_id, target_language, "Locking symbol registry", 5)
            registry = SymbolRegistryService(self.db).finalize_registry(
                run_id=run_id,
                target_language=target_language,
            )
            final_result["steps"].append(
                {
                    "step": "registry",
                    "type_mapping_count": registry.get("type_mapping_count", 0),
                    "signature_count": registry.get("signature_count", 0),
                }
            )

            # 2. Planning
            self._stage(run_id, target_language, "Creating conversion plans", 15)
            plan_result = ConversionPlanningProcess(self.db).create_plans(
                run_id=run_id,
                target_language=target_language,
                project_id=project_id,
            )
            final_result["steps"].append(
                {
                    "step": "planning",
                    "count": plan_result.get("count", 0),
                    "errors": plan_result.get("errors", []),
                }
            )

            # 3. Initial full generation
            self._stage(run_id, target_language, "Generating source files", 35)
            generation_process = CodeGenerationProcess(self.db)

            generate_result = generation_process.generate(
                run_id=run_id,
                target_language=target_language,
                file_id=None,
                project_id=project_id,
                clean_output=True,
            )

            final_result["steps"].append(
                {
                    "step": "generate",
                    "count": generate_result.get("count", 0),
                    "processed_source_file_count": generate_result.get(
                        "processed_source_file_count", 0
                    ),
                    "errors": generate_result.get("errors", []),
                }
            )

            quality = generate_result.get("quality_gate") or {}

            # 4. Regenerate missing planned files
            for round_index in range(max_missing_rounds):
                if quality.get("success"):
                    break

                missing = generation_process._extract_missing_planned_files(quality)

                if not missing:
                    break

                self._stage(
                    run_id,
                    target_language,
                    f"Regenerating missing files round {round_index + 1}",
                    50 + round_index * 5,
                )

                regen_result = generation_process.regenerate_missing_files(
                    run_id=run_id,
                    target_language=target_language,
                    project_id=project_id,
                    max_files=50,
                )

                final_result["steps"].append(
                    {
                        "step": f"regenerate_missing_round_{round_index + 1}",
                        "regenerated": regen_result.get("regenerated", 0),
                        "regenerated_file_ids": regen_result.get(
                            "regenerated_file_ids", []
                        ),
                        "unresolved_missing_files": regen_result.get(
                            "unresolved_missing_files", []
                        ),
                        "errors": regen_result.get("errors", []),
                    }
                )

                quality = regen_result.get("quality_gate") or quality

            # 5. Repair comment-only methods
            for round_index in range(max_method_repair_rounds):
                if quality.get("success"):
                    break

                method_quality = (
                    quality.get("method_quality")
                    or quality.get("checks", {}).get("method_quality")
                    or {}
                )

                bad_count = method_quality.get("count", 0)

                if not bad_count:
                    break

                self._stage(
                    run_id,
                    target_language,
                    f"Repairing comment-only methods round {round_index + 1}",
                    65 + round_index * 5,
                )

                repair_result = MethodBodyRepairProcess(
                    self.db
                ).repair_comment_only_methods(
                    run_id=run_id,
                    target_language=target_language,
                    max_methods=20,
                    project_id=project_id,
                )

                final_result["steps"].append(
                    {
                        "step": f"repair_comment_methods_round_{round_index + 1}",
                        "requested": repair_result.get("requested", 0),
                        "repaired": repair_result.get("repaired", 0),
                        "before_count": repair_result.get("before_count", 0),
                        "after_count": repair_result.get("after_count", 0),
                        "errors": repair_result.get("errors", []),
                    }
                )

                quality = generation_process.quality_service.run_quality_gate(
                    run_id=run_id,
                    target_language=target_language,
                )

            # 6. Final quality gate
            self._stage(run_id, target_language, "Running final quality gate", 80)

            quality = generation_process.quality_service.run_quality_gate(
                run_id=run_id,
                target_language=target_language,
            )

            final_result["quality_gate"] = quality

            if not quality.get("success"):
                final_result["status"] = "QUALITY_GATE_FAILED"
                final_result["download_allowed"] = False
                final_result["errors"].append(
                    {
                        "stage": "quality_gate",
                        "failures": quality.get("failures", []),
                    }
                )

                self._write_status(
                    run_id,
                    target_language,
                    status="QUALITY_GATE_FAILED",
                    stage="Quality gate failed",
                    progress=85,
                    download_allowed=False,
                    extra=final_result,
                )

                return final_result

            # 7. Compile validation
            self._stage(run_id, target_language, "Compiling generated project", 90)

            validation = generation_process.validate_generated_project(
                run_id=run_id,
                target_language=target_language,
            )

            final_result["validation"] = validation

            if not validation.get("success"):
                final_result["status"] = "VALIDATION_FAILED"
                final_result["download_allowed"] = False
                final_result["errors"].append(
                    {
                        "stage": "validation",
                        "status": validation.get("status"),
                        "stderr": validation.get("stderr", "")[:2000],
                    }
                )

                self._write_status(
                    run_id,
                    target_language,
                    status="VALIDATION_FAILED",
                    stage="Compile validation failed",
                    progress=92,
                    download_allowed=False,
                    extra=final_result,
                )

                return final_result

            # 8. Report
            self._stage(run_id, target_language, "Generating migration report", 96)

            report = MigrationReportService(self.db).generate_report(
                run_id=run_id,
                target_language=target_language,
            )

            final_result["report"] = report

            # 9. Done
            final_result["status"] = "COMPLETED"
            final_result["download_allowed"] = True

            self._write_status(
                run_id,
                target_language,
                status="COMPLETED",
                stage="Generated code is ready to download",
                progress=100,
                download_allowed=True,
                extra=final_result,
            )

            return final_result

        except Exception as exc:
            final_result["status"] = "FAILED"
            final_result["download_allowed"] = False
            final_result["errors"].append(
                {
                    "stage": "pipeline",
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )

            self._write_status(
                run_id,
                target_language,
                status="FAILED",
                stage=f"Pipeline failed: {exc}",
                progress=100,
                download_allowed=False,
                extra=final_result,
            )

            return final_result

    def get_status(
        self,
        run_id: str,
        target_language: str = "java",
    ) -> dict[str, Any]:
        path = self._status_path(run_id, target_language)

        if not path.exists():
            return {
                "run_id": run_id,
                "target_language": target_language,
                "status": "NOT_STARTED",
                "stage": "Code generation has not started.",
                "progress": 0,
                "download_allowed": False,
            }

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "run_id": run_id,
                "target_language": target_language,
                "status": "STATUS_READ_FAILED",
                "stage": "Could not read pipeline status.",
                "progress": 0,
                "download_allowed": False,
            }

    def _stage(
        self,
        run_id: str,
        target_language: str,
        stage: str,
        progress: int,
    ) -> None:
        self._write_status(
            run_id=run_id,
            target_language=target_language,
            status="RUNNING",
            stage=stage,
            progress=progress,
            download_allowed=False,
        )

    def _write_status(
        self,
        run_id: str,
        target_language: str,
        status: str,
        stage: str,
        progress: int,
        download_allowed: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "run_id": run_id,
            "target_language": target_language,
            "status": status,
            "stage": stage,
            "progress": max(0, min(100, int(progress))),
            "download_allowed": bool(download_allowed),
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

        if extra:
            payload.update(extra)

        path = self._status_path(run_id, target_language)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _status_path(
        self,
        run_id: str,
        target_language: str,
    ) -> Path:
        return (
            Path("output")
            / "generated_code"
            / run_id
            / "pipeline"
            / target_language
            / "status.json"
        )