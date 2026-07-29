import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from Persistence.sqlite.models import BusinessRule, FileRelation, Project, ProjectFile


class MigrationReportService:
    """
    Builds a final migration report from:
    - project metadata
    - source files
    - conversion plans
    - generated files
    - validation result
    - fix result
    - business rules
    - dependencies
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def generate_report(
        self,
        run_id: str,
        target_language: str = "java",
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        project = self.db.query(Project).filter(Project.run_id == run_id).first()

        if not project:
            raise ValueError(f"Project not found for run_id={run_id}")

        output_root = self._output_root(run_id)
        project_dir = self._project_dir(run_id, target)
        report_dir = output_root / "reports" / target
        report_dir.mkdir(parents=True, exist_ok=True)

        source_files = self._source_files(run_id)
        business_rules = self._business_rules(run_id)
        dependencies = self._dependencies(run_id)
        plans = self._plans(run_id, target)
        generated_files = self._generated_files(project_dir)
        validation = self._latest_json(output_root / "validation" / target / "latest_validation.json")
        quality = self._latest_json(output_root / "quality" / target / "latest_quality.json")
        fix_result = self._latest_json(output_root / "fixes" / target / "latest_fix.json")

        report = {
            "run_id": run_id,
            "project_name": project.project_name,
            "target_language": target,
            "target_framework": self._framework_for(target),
            "source_file_count": len(source_files),
            "business_rule_count": len(business_rules),
            "dependency_count": len(dependencies),
            "conversion_plan_count": len(plans),
            "generated_file_count": len(generated_files),
            "validation_success": validation.get("success") if validation else None,
            "quality_gate_success": quality.get("success") if quality else None,
            "fix_status": fix_result.get("status") if fix_result else None,
            "source_files": source_files,
            "conversion_plans": plans,
            "generated_files": generated_files,
            "business_rules": business_rules,
            "dependencies": dependencies,
            "validation": validation,
            "quality_gate": quality,
            "fix_result": fix_result,
        }

        json_path = report_dir / "migration_report.json"
        md_path = report_dir / "MIGRATION_REPORT.md"

        json_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        md_path.write_text(
            self._to_markdown(report),
            encoding="utf-8",
        )

        return {
            "run_id": run_id,
            "target_language": target,
            "json_report": str(json_path),
            "markdown_report": str(md_path),
            "report": report,
        }

    def read_markdown_report(
        self,
        run_id: str,
        target_language: str = "java",
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        md_path = self._output_root(run_id) / "reports" / target / "MIGRATION_REPORT.md"

        if not md_path.exists():
            raise FileNotFoundError(
                f"No migration report found for run_id={run_id}, target={target}. Generate report first."
            )

        return {
            "run_id": run_id,
            "target_language": target,
            "path": str(md_path),
            "content": md_path.read_text(encoding="utf-8", errors="ignore"),
        }

    def _source_files(self, run_id: str) -> list[dict[str, Any]]:
        files = (
            self.db.query(ProjectFile)
            .filter(ProjectFile.run_id == run_id)
            .order_by(ProjectFile.id)
            .all()
        )

        return [
            {
                "id": file.id,
                "filename": file.filename,
                "filepath": file.filepath,
                "detected_lang": file.detected_lang,
                "status": file.status.value if file.status else None,
            }
            for file in files
        ]

    def _business_rules(self, run_id: str) -> list[dict[str, Any]]:
        rules = (
            self.db.query(BusinessRule)
            .filter(BusinessRule.run_id == run_id)
            .order_by(BusinessRule.id)
            .all()
        )

        return [
            {
                "id": rule.id,
                "rule_id": rule.rule_id,
                "rule_text": rule.rule_text or rule.business_logic or "",
                "business_purpose": rule.business_purpose or "",
                "functional_logic": rule.functional_logic or "",
                "technical_ref": rule.technical_ref or "",
                "status": rule.status,
                "file_id": rule.file_id,
                "chunk_id": rule.chunk_id,
            }
            for rule in rules
        ]

    def _dependencies(self, run_id: str) -> list[dict[str, Any]]:
        relations = (
            self.db.query(FileRelation)
            .filter(FileRelation.run_id == run_id)
            .order_by(FileRelation.id)
            .all()
        )

        return [
            {
                "id": relation.id,
                "source_file": relation.source_file,
                "target_item": relation.target_item,
                "relation_type": relation.relation_type,
                "context": getattr(relation, "context", "") or "",
                "resolved": bool(getattr(relation, "resolved", True)),
            }
            for relation in relations
        ]

    def _plans(self, run_id: str, target_language: str) -> list[dict[str, Any]]:
        plan_dir = self._output_root(run_id) / "plans" / target_language

        if not plan_dir.exists():
            return []

        plans = []
        for path in sorted(plan_dir.glob("*.json")):
            try:
                plans.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue

        return plans

    def _generated_files(self, project_dir: Path) -> list[dict[str, Any]]:
        if not project_dir.exists():
            return []

        files = []

        for path in sorted(project_dir.rglob("*")):
            if not path.is_file():
                continue

            rel_path = path.relative_to(project_dir).as_posix()

            files.append({
                "path": rel_path,
                "size": path.stat().st_size,
            })

        return files

    @staticmethod
    def _latest_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _to_markdown(self, report: dict[str, Any]) -> str:
        lines = []

        lines.append("# Migration Report")
        lines.append("")
        lines.append(f"**Run ID:** `{report['run_id']}`")
        lines.append(f"**Project:** {report.get('project_name') or 'Unknown'}")
        lines.append(f"**Target:** {report['target_language']} / {report['target_framework']}")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Source files: **{report['source_file_count']}**")
        lines.append(f"- Business rules: **{report['business_rule_count']}**")
        lines.append(f"- Dependencies: **{report['dependency_count']}**")
        lines.append(f"- Conversion plans: **{report['conversion_plan_count']}**")
        lines.append(f"- Generated files: **{report['generated_file_count']}**")

        validation = report.get("validation") or {}
        if validation:
            status = "Passed" if validation.get("success") else "Failed"
            lines.append(f"- Validation: **{status}**")
            lines.append(f"- Validation command: `{validation.get('command') or ''}`")
        else:
            lines.append("- Validation: **Not run**")

        quality = report.get("quality_gate") or {}
        if quality:
            quality_status = "Passed" if quality.get("success") else "Failed"
            lines.append(f"- Generation quality gate: **{quality_status}**")
            for failure in quality.get("failures") or []:
                lines.append(f"  - {failure}")
        else:
            lines.append("- Generation quality gate: **Not run**")

        fix_result = report.get("fix_result") or {}
        if fix_result:
            lines.append(f"- Auto-fix status: **{fix_result.get('status', 'Unknown')}**")
            lines.append(f"- Fixed files: **{len(fix_result.get('fixed_files') or [])}**")
        else:
            lines.append("- Auto-fix: **Not run**")

        lines.append("")
        lines.append("## Source Files")
        lines.append("")

        for file in report.get("source_files", []):
            lines.append(
                f"- `{file.get('filepath') or file.get('filename')}` "
                f"({file.get('detected_lang') or 'unknown'}, {file.get('status') or 'unknown'})"
            )

        lines.append("")
        lines.append("## Generated Files")
        lines.append("")

        for file in report.get("generated_files", []):
            lines.append(f"- `{file.get('path')}` ({file.get('size')} bytes)")

        lines.append("")
        lines.append("## Conversion Plans")
        lines.append("")

        for plan in report.get("conversion_plans", []):
            lines.append(f"### {plan.get('source_file')}")
            lines.append("")
            lines.append(plan.get("summary") or "No summary.")
            lines.append("")
            lines.append("**Target classes:**")
            for cls in plan.get("classes", []) or []:
                lines.append(
                    f"- `{cls.get('class_name')}` → `{cls.get('file_path')}` "
                    f"({cls.get('layer')})"
                )
            if plan.get("unresolved_items"):
                lines.append("")
                lines.append("**Unresolved items:**")
                for item in plan.get("unresolved_items", []):
                    lines.append(f"- {item}")
            lines.append("")

        lines.append("## Business Rules")
        lines.append("")

        for rule in report.get("business_rules", []):
            rule_id = rule.get("rule_id") or rule.get("id")
            text = rule.get("rule_text") or ""
            status = rule.get("status") or "PENDING"
            lines.append(f"- **{rule_id}** [{status}]: {text}")

        lines.append("")
        lines.append("## Dependencies")
        lines.append("")

        unresolved_count = 0

        for dep in report.get("dependencies", []):
            resolved = dep.get("resolved", True)
            if not resolved or dep.get("relation_type") == "UNRESOLVED":
                unresolved_count += 1

            marker = "resolved" if resolved else "unresolved"
            lines.append(
                f"- `{dep.get('source_file')}` "
                f"--{dep.get('relation_type')}--> "
                f"`{dep.get('target_item')}` ({marker})"
            )

        lines.append("")
        lines.append("## Risk Notes")
        lines.append("")

        if unresolved_count:
            lines.append(f"- There are **{unresolved_count} unresolved dependency reference(s)** that require manual review.")
        else:
            lines.append("- No unresolved dependency references were found in the generated report.")

        if validation and not validation.get("success"):
            lines.append("- Generated project validation failed. Review compiler/syntax errors before production use.")

        if fix_result and fix_result.get("errors"):
            lines.append("- Some auto-fix attempts failed. Review fix errors before final export.")

        lines.append("")
        lines.append("## Validation Output")
        lines.append("")

        if validation:
            lines.append("```txt")
            lines.append((validation.get("stderr") or validation.get("stdout") or "No output.")[:8000])
            lines.append("```")
        else:
            lines.append("Validation was not run.")

        lines.append("")
        lines.append("---")
        lines.append("Generated by ModernizerAI.")

        return "\n".join(lines)

    @staticmethod
    def _framework_for(target_language: str) -> str:
        if target_language == "java":
            return "Quarkus"
        if target_language == "python":
            return "FastAPI"
        if target_language == "csharp":
            return "ASP.NET Core"
        return "Unknown"

    @staticmethod
    def _normalize_target(target_language: str) -> str:
        value = str(target_language or "java").strip().lower()

        aliases = {
            "java": "java",
            "quarkus": "java",
            "python": "python",
            "py": "python",
            "fastapi": "python",
            "csharp": "csharp",
            "c#": "csharp",
            "cs": "csharp",
            "dotnet": "csharp",
            "aspnet": "csharp",
        }

        if value not in aliases:
            raise ValueError("Unsupported target language. Use java, python, or csharp.")

        return aliases[value]

    @staticmethod
    def _output_root(run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "generated_code" / run_id

    @staticmethod
    def _project_dir(run_id: str, target_language: str) -> Path:
        return (
            MigrationReportService._output_root(run_id)
            / "project"
            / target_language
        )
