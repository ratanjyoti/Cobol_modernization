import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from Agents.implementations.conversion_planner_agent import ConversionPlannerAgent
from Agents.infrastructure.codegen_context_builder import CodegenContextBuilder
from Agents.models.code_generation_models import ConversionPlan, model_to_dict
from Config.llm_config import settings
from Persistence.sqlite.models import Project
from services.symbol_registry_service import SymbolRegistryService


class ConversionPlanningProcess:
    """
    Creates and stores conversion plans.

    Storage for this first version:
      backend/output/generated_code/{run_id}/plans/{target_language}/{file_id}.json

    Later we can also persist this to SQLite.
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.context_builder = CodegenContextBuilder(db_session)

    def create_plans(
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
        registry = SymbolRegistryService(self.db).get_registry(
            run_id=run_id,
            target_language=target_language,
        )

        if registry["type_mapping_count"] == 0 and registry["signature_count"] == 0:
            SymbolRegistryService(self.db).finalize_registry(
                run_id=run_id,
                target_language=target_language,
            )

        planner = ConversionPlannerAgent(llm_config=llm_config)

        if file_id is not None:
            file_contexts = [
                self.context_builder.build_single_file_context(run_id, file_id)
            ]
        else:
            file_contexts = self.context_builder.build_file_contexts(run_id)

        if not file_contexts:
            return {
                "run_id": run_id,
                "target_language": target_language,
                "count": 0,
                "plans": [],
                "warnings": [
                    "No COBOL or Telon files were found for conversion planning."
                ],
            }

        effective_project_id = project_id or run_id or "default"
        plans: list[ConversionPlan] = []
        errors: list[dict[str, Any]] = []

        for file_context in file_contexts:
            try:
                plan = planner.create_plan(
                    file_context=file_context,
                    target_language=target_language,
                    project_id=effective_project_id,
                )
                self._save_plan(plan)
                plans.append(plan)
            except Exception as exc:
                errors.append({
                    "file_id": file_context.file_id,
                    "filename": file_context.filename,
                    "error": str(exc),
                })

        return {
            "run_id": run_id,
            "target_language": target_language,
            "count": len(plans),
            "plans": [model_to_dict(plan) for plan in plans],
            "errors": errors,
        }

    def list_plans(
        self,
        run_id: str,
        target_language: str = "java",
    ) -> dict[str, Any]:
        plan_dir = self._plan_dir(run_id, target_language)

        plans = []
        if plan_dir.exists():
            for path in sorted(plan_dir.glob("*.json")):
                try:
                    plans.append(json.loads(path.read_text(encoding="utf-8")))
                except Exception:
                    continue

        return {
            "run_id": run_id,
            "target_language": target_language,
            "count": len(plans),
            "plans": plans,
        }

    def get_plan(
        self,
        run_id: str,
        file_id: int,
        target_language: str = "java",
    ) -> dict[str, Any]:
        path = self._plan_dir(run_id, target_language) / f"{file_id}.json"

        if not path.exists():
            raise FileNotFoundError(
                f"No conversion plan found for run_id={run_id}, file_id={file_id}, target={target_language}"
            )

        return json.loads(path.read_text(encoding="utf-8"))

    def _save_plan(self, plan: ConversionPlan):
        plan_dir = self._plan_dir(plan.run_id, plan.target_language.value)
        plan_dir.mkdir(parents=True, exist_ok=True)

        path = plan_dir / f"{plan.file_id}.json"
        payload = model_to_dict(plan)

        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _plan_dir(run_id: str, target_language: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return (
            backend_root
            / "output"
            / "generated_code"
            / run_id
            / "plans"
            / target_language
        )

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
