import json
import re
from pathlib import Path
from typing import Any

from Agents.implementations.method_body_repair_agent import MethodBodyRepairAgent
from Persistence.sqlite.models import BusinessRule, Project
from Processes.conversion_planning_process import ConversionPlanningProcess
from services.method_quality_service import MethodQualityService
from services.symbol_registry_service import SymbolRegistryService


class MethodBodyRepairProcess:
    def __init__(self, db):
        self.db = db
        self.method_quality = MethodQualityService()

    def repair_comment_only_methods(
        self,
        run_id: str,
        target_language: str = "java",
        max_methods: int = 10,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)

        project_dir = (
            Path("output")
            / "generated_code"
            / run_id
            / "project"
            / target
        )

        scan = self.method_quality.scan_project(
            project_dir=project_dir,
            target_language=target,
        )

        bad_methods = (
            scan.get("comment_only_methods", [])
            + scan.get("placeholder_methods", [])
        )[:max_methods]

        if not bad_methods:
            return {
                "run_id": run_id,
                "target_language": target,
                "repaired": 0,
                "message": "No weak methods/functions found.",
                "scan": scan,
            }

        project = self.db.query(Project).filter_by(run_id=run_id).first()
        llm_config = ConversionPlanningProcess._project_ai_config(project)

        agent = MethodBodyRepairAgent(llm_config)

        registry = SymbolRegistryService(self.db).get_registry(
            run_id=run_id,
            target_language=target,
        )

        business_rules = [
            {
                "rule_id": item.rule_id,
                "rule_text": item.rule_text,
                "business_purpose": item.business_purpose,
                "technical_ref": item.technical_ref,
            }
            for item in self.db.query(BusinessRule)
            .filter(BusinessRule.run_id == run_id)
            .limit(200)
            .all()
        ]

        repaired: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for method in bad_methods:
            try:
                relative_path = method["file_path"]
                absolute_path = project_dir / relative_path

                if not absolute_path.exists():
                    errors.append(
                        {
                            "file_path": relative_path,
                            "method_name": method["method_name"],
                            "error": "File not found",
                        }
                    )
                    continue

                content = absolute_path.read_text(encoding="utf-8", errors="ignore")

                class_name = self._extract_class_or_module_name(
                    content=content,
                    relative_path=relative_path,
                    target_language=target,
                )

                source_evidence = self._build_source_evidence(
                    run_id=run_id,
                    method_name=method["method_name"],
                    relative_path=relative_path,
                    target_language=target,
                )

                result = agent.repair_method_body(
                    file_path=relative_path,
                    class_name=class_name,
                    method_name=method["method_name"],
                    method_header=method["header"],
                    current_body=method.get("body_preview", ""),
                    source_evidence=source_evidence,
                    business_rules=business_rules,
                    locked_symbols=registry,
                    target_language=target,
                )

                updated = self._replace_method_body(
                    content=content,
                    method_name=method["method_name"],
                    replacement_body=result["replacement_body"],
                    target_language=target,
                )

                backup_path = self._backup_file(
                    run_id=run_id,
                    target_language=target,
                    relative_path=relative_path,
                    content=content,
                )

                absolute_path.write_text(updated, encoding="utf-8")

                repaired.append(
                    {
                        "file_path": relative_path,
                        "method_name": method["method_name"],
                        "backup_path": str(backup_path),
                        "warnings": result.get("warnings", []),
                    }
                )

            except Exception as exc:
                errors.append(
                    {
                        "file_path": method.get("file_path"),
                        "method_name": method.get("method_name"),
                        "error": str(exc),
                    }
                )

        after_scan = self.method_quality.scan_project(
            project_dir=project_dir,
            target_language=target,
        )

        report = {
            "run_id": run_id,
            "target_language": target,
            "requested": len(bad_methods),
            "repaired": len(repaired),
            "errors": errors,
            "repaired_methods": repaired,
            "before_count": scan.get("count", 0),
            "after_count": after_scan.get("count", 0),
            "after_scan": after_scan,
        }

        self._write_report(run_id, target, report)

        return report

    def _replace_method_body(
        self,
        content: str,
        method_name: str,
        replacement_body: str,
        target_language: str,
    ) -> str:
        target = self._normalize_target(target_language)

        if target == "python":
            return self._replace_python_function_body(
                content=content,
                function_name=method_name,
                replacement_body=replacement_body,
            )

        return self._replace_brace_method_body(
            content=content,
            method_name=method_name,
            replacement_body=replacement_body,
            target_language=target,
        )

    def _replace_brace_method_body(
        self,
        content: str,
        method_name: str,
        replacement_body: str,
        target_language: str,
    ) -> str:
        if target_language == "csharp":
            visibility = r"(?:public|private|protected|internal)"
        else:
            visibility = r"(?:public|private|protected)"

        pattern = re.compile(
            rf"""
            (?P<header>
                {visibility}\s+
                (?:static\s+)?
                (?:async\s+)?
                [A-Za-z0-9_<>\[\],\s?.]+\s+
                {re.escape(method_name)}\s*
                \([^)]*\)\s*
            )
            \{{
            """,
            re.VERBOSE | re.MULTILINE,
        )

        match = pattern.search(content)

        if not match:
            raise ValueError(f"Could not locate method {method_name}")

        start_brace = content.find("{", match.start())
        end_brace = self._find_matching_brace(content, start_brace)

        if end_brace == -1:
            raise ValueError(f"Could not locate closing brace for {method_name}")

        indented_body = self._indent_body(replacement_body, "        ")

        return (
            content[: start_brace + 1]
            + "\n"
            + indented_body
            + "\n    "
            + content[end_brace:]
        )

    def _replace_python_function_body(
        self,
        content: str,
        function_name: str,
        replacement_body: str,
    ) -> str:
        pattern = re.compile(
            rf"""
            ^(?P<indent>[ \t]*)
            (?P<header>
                (?:async\s+)?
                def\s+
                {re.escape(function_name)}\s*
                \([^)]*\)\s*
                (?:->\s*[^:]+)?
                :
            )
            """,
            re.VERBOSE | re.MULTILINE,
        )

        match = pattern.search(content)

        if not match:
            raise ValueError(f"Could not locate Python function {function_name}")

        indent = match.group("indent") or ""
        body_indent = indent + "    "

        body_start = match.end()
        body_end = self._find_python_function_end(
            content=content,
            body_start=body_start,
            parent_indent_len=len(indent),
        )

        indented_body = self._indent_body(replacement_body, body_indent)

        return (
            content[:body_start]
            + "\n"
            + indented_body
            + "\n"
            + content[body_end:]
        )

    def _find_python_function_end(
        self,
        content: str,
        body_start: int,
        parent_indent_len: int,
    ) -> int:
        lines = content[body_start:].splitlines(keepends=True)
        offset = body_start

        for line in lines:
            if not line.strip():
                offset += len(line)
                continue

            current_indent = len(line) - len(line.lstrip(" \t"))

            if current_indent <= parent_indent_len:
                return offset

            offset += len(line)

        return len(content)

    def _indent_body(self, body: str, indent: str) -> str:
        lines = [line.rstrip() for line in str(body or "").splitlines()]

        return "\n".join(
            indent + line.lstrip()
            for line in lines
            if line.strip()
        )

    def _find_matching_brace(self, text: str, open_index: int) -> int:
        depth = 0
        in_string = False
        in_char = False
        escape = False

        for index in range(open_index, len(text)):
            char = text[index]

            if escape:
                escape = False
                continue

            if char == "\\":
                escape = True
                continue

            if char == '"' and not in_char:
                in_string = not in_string
                continue

            if char == "'" and not in_string:
                in_char = not in_char
                continue

            if in_string or in_char:
                continue

            if char == "{":
                depth += 1

            elif char == "}":
                depth -= 1

                if depth == 0:
                    return index

        return -1

    def _extract_class_or_module_name(
        self,
        content: str,
        relative_path: str,
        target_language: str,
    ) -> str:
        target = self._normalize_target(target_language)

        if target == "python":
            class_match = re.search(
                r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)",
                content or "",
                flags=re.MULTILINE,
            )

            if class_match:
                return class_match.group(1)

            return Path(relative_path).stem

        match = re.search(
            r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)",
            content or "",
        )

        return match.group(1) if match else Path(relative_path).stem

    def _build_source_evidence(
        self,
        run_id: str,
        method_name: str,
        relative_path: str,
        target_language: str,
    ) -> str:
        evidence = {
            "run_id": run_id,
            "target_language": target_language,
            "method_name": method_name,
            "relative_path": relative_path,
            "note": (
                "Use the matching COBOL/Telon paragraph, technical YAML, "
                "business rules, locked symbols, and surrounding generated code "
                "to reconstruct executable logic."
            ),
        }

        return json.dumps(evidence, indent=2)

    def _backup_file(
        self,
        run_id: str,
        target_language: str,
        relative_path: str,
        content: str,
    ) -> Path:
        backup_path = (
            Path("output")
            / "generated_code"
            / run_id
            / "backups"
            / target_language
            / "method_body_repair"
            / relative_path
        )

        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(content, encoding="utf-8")

        return backup_path

    def _write_report(
        self,
        run_id: str,
        target_language: str,
        report: dict[str, Any],
    ) -> None:
        path = (
            Path("output")
            / "generated_code"
            / run_id
            / "fixes"
            / target_language
            / "latest_method_body_repair.json"
        )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    def _normalize_target(self, target_language: str) -> str:
        value = str(target_language or "").lower().strip()

        if value in {"python", "py", "fastapi"}:
            return "python"

        if value in {"csharp", "c#", "cs", "dotnet"}:
            return "csharp"

        return "java"