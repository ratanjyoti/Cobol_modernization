import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from Persistence.sqlite.models import ProjectFile
from services.method_quality_service import MethodQualityService
from services.symbol_registry_service import SymbolRegistryService


class GenerationQualityService:
    """
    Hard gate between generated files and validation/download.

    This rejects scaffold-only projects, placeholder methods, partial project
    generation, copybook/service misrouting, and missing locked-symbol coverage.
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.method_quality_service = MethodQualityService()

    def evaluate(
        self,
        run_id: str,
        target_language: str,
        project_dir: Path,
    ) -> dict[str, Any]:
        target = (target_language or "java").lower().strip()
        output_root = self._output_root(run_id)
        plans = self._load_plans(output_root, target)
        manifest = self._load_json(project_dir / "generation_manifest.json")
        code_files = self._code_files(project_dir, target)
        source_files = self._source_files(run_id)
        registry = SymbolRegistryService(self.db).get_registry(run_id, target)
        method_quality = self.method_quality_service.scan_project(
            project_dir=project_dir,
            target_language=target,
        )

        failures: list[str] = []
        warnings: list[str] = []

        if not plans:
            failures.append("No conversion plans were found for this run.")

        if not code_files:
            failures.append("No generated source code files were found.")

        manifest_source_count = int(manifest.get("source_file_count") or 0)
        plan_count = len(plans)

        if plan_count and manifest_source_count < plan_count:
            failures.append(
                f"Only {manifest_source_count} source file(s) were generated, but {plan_count} conversion plan(s) exist."
            )

        planned_class_paths = self._planned_class_paths(plans)
        generated_rel_paths = {path.relative_to(project_dir).as_posix() for path in code_files}
        missing_planned_classes = sorted(planned_class_paths - generated_rel_paths)
        generated_source_files = {
            str(item.get("source_file") or "")
            for item in manifest.get("files") or []
            if item.get("source_file")
        }

        if missing_planned_classes:
            failures.append(
                "Generated project is missing planned class files: "
                + ", ".join(missing_planned_classes[:20])
            )

        placeholder_files = []
        copybook_service_files = []
        implementation_signal_count = 0

        for path in code_files:
            content = path.read_text(encoding="utf-8", errors="ignore")
            rel_path = path.relative_to(project_dir).as_posix()

            if self._is_placeholder_code(content, target):
                placeholder_files.append(rel_path)

            source_name = self._source_for_generated_file(manifest, rel_path)
            if self._copybook_service_misroute(source_name, rel_path, content):
                copybook_service_files.append(rel_path)

            implementation_signal_count += self._implementation_signal_count(content, target)

        if placeholder_files:
            failures.append(
                "Placeholder/stub generated code was rejected: "
                + ", ".join(placeholder_files[:20])
            )

        if not method_quality.get("success"):
            comment_items = method_quality.get("comment_only_methods", [])[:30]
            placeholder_items = method_quality.get("placeholder_methods", [])[:30]

            if comment_items:
                failures.append(
                    "Generated methods/functions contain comments but no executable implementation: "
                    + ", ".join(
                        f"{item['file_path']}::{item['method_name']}"
                        for item in comment_items
                    )
                )

            if placeholder_items:
                failures.append(
                    "Generated methods/functions contain placeholder or stub logic: "
                    + ", ".join(
                        f"{item['file_path']}::{item['method_name']}"
                        for item in placeholder_items
                    )
                )

        if copybook_service_files:
            failures.append(
                "Copybook files were generated as generic services instead of model/DTO or real helper logic: "
                + ", ".join(copybook_service_files[:20])
            )

        if code_files and implementation_signal_count == 0:
            failures.append("Generated code contains no implementation evidence beyond declarations/comments.")

        scoped_type_mappings = self._registry_items_for_sources(
            registry.get("type_mappings", []),
            generated_source_files,
        )
        scoped_signatures = self._registry_items_for_sources(
            registry.get("signatures", []),
            generated_source_files,
        )

        type_coverage = self._name_coverage(
            [item.get("target_name") for item in scoped_type_mappings],
            code_files,
        )
        method_coverage = self._method_coverage(
            [item.get("target_method") for item in scoped_signatures],
            code_files,
        )

        if type_coverage["total"] and type_coverage["ratio"] < 0.25:
            failures.append(
                f"Locked variable coverage is too low: {type_coverage['covered']}/{type_coverage['total']} "
                f"({type_coverage['ratio']:.0%})."
            )

        if method_coverage["total"] and method_coverage["ratio"] < 0.50:
            failures.append(
                f"Locked method coverage is too low: {method_coverage['covered']}/{method_coverage['total']} "
                f"({method_coverage['ratio']:.0%})."
            )

        stale_fallback_plans = [
            plan.get("source_file")
            for plan in plans
            if self._is_bad_fallback_plan(plan, source_files)
        ]
        if stale_fallback_plans:
            warnings.append(
                "Local fallback conversion plan used because the selected LLM was unavailable or over context: "
                + ", ".join(str(item) for item in stale_fallback_plans[:20])
            )

        result = {
            "success": len(failures) == 0,
            "status": "PASSED" if len(failures) == 0 else "FAILED",
            "run_id": run_id,
            "target_language": target,
            "download_allowed": len(failures) == 0,
            "metrics": {
                "source_file_count": len(source_files),
                "conversion_plan_count": plan_count,
                "manifest_source_file_count": manifest_source_count,
                "generated_code_file_count": len(code_files),
                "planned_class_count": len(planned_class_paths),
                "missing_planned_class_count": len(missing_planned_classes),
                "implementation_signal_count": implementation_signal_count,
                "locked_variable_total": type_coverage["total"],
                "locked_variable_covered": type_coverage["covered"],
                "locked_variable_coverage_ratio": type_coverage["ratio"],
                "locked_method_total": method_coverage["total"],
                "locked_method_covered": method_coverage["covered"],
                "locked_method_coverage_ratio": method_coverage["ratio"],
            },
            "method_quality": method_quality,
            "failures": failures,
            "warnings": warnings,
        }

        self._write_latest_quality(output_root, target, result)
        return result

    def run_quality_gate(
        self,
        run_id: str,
        target_language: str,
        project_dir: Path | None = None,
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        project_dir = project_dir or self._project_dir(run_id, target)
        return self.evaluate(
            run_id=run_id,
            target_language=target,
            project_dir=project_dir,
        )

    def latest(
        self,
        run_id: str,
        target_language: str,
    ) -> dict[str, Any]:
        return self._load_json(
            self._output_root(run_id)
            / "quality"
            / (target_language or "java").lower().strip()
            / "latest_quality.json"
        )

    def _source_files(self, run_id: str) -> dict[str, ProjectFile]:
        files = (
            self.db.query(ProjectFile)
            .filter(ProjectFile.run_id == run_id)
            .order_by(ProjectFile.id)
            .all()
        )
        return {
            file.filename: file
            for file in files
            if self._is_convertible_source(file.filename, file.detected_lang)
        }

    @staticmethod
    def _load_plans(output_root: Path, target_language: str) -> list[dict[str, Any]]:
        plan_dir = output_root / "plans" / target_language
        if not plan_dir.exists():
            return []

        plans = []
        for path in sorted(plan_dir.glob("*.json")):
            payload = GenerationQualityService._load_json(path)
            if payload:
                plans.append(payload)
        return plans

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _source_extension(self, target_language: str) -> str:
        target = self._normalize_target(target_language)

        if target == "python":
            return ".py"

        if target == "csharp":
            return ".cs"

        return ".java"

    def _code_files(self, project_dir: Path, target_language: str) -> list[Path]:
        if not project_dir.exists():
            return []

        source_extension = self._source_extension(target_language)
        files = []

        for path in sorted(project_dir.rglob(f"*{source_extension}")):
            normalized = path.as_posix()

            if (
                "/target/" in normalized
                or "/build/" in normalized
                or "/bin/" in normalized
                or "/obj/" in normalized
                or "/__pycache__/" in normalized
            ):
                continue

            files.append(path)

        return files

    @staticmethod
    def _planned_class_paths(plans: list[dict[str, Any]]) -> set[str]:
        paths = set()
        for plan in plans:
            package_name = str(plan.get("target_package_or_namespace") or "com.modernizer.migration")
            for item in plan.get("classes") or []:
                file_path = str(item.get("file_path") or "").replace("\\", "/").strip("/")
                if file_path:
                    if file_path.endswith(".java") and not file_path.startswith("src/"):
                        filename = Path(file_path).name
                        if "/" in file_path:
                            prefix = file_path.rsplit("/", 1)[0].replace(".", "/")
                        else:
                            prefix = package_name.replace(".", "/")
                        file_path = f"src/main/java/{prefix}/{filename}"
                    paths.add(file_path)
        return paths

    def _placeholder_patterns(self, target_language: str) -> list[str]:
        target = self._normalize_target(target_language)

        common = [
            r"\bTODO\b",
            r"\bFIXME\b",
            r"\bstub\b",
            r"\bplaceholder\b",
            r"\bnot\s+implemented\b",
        ]

        if target == "python":
            return common + [
                r"\bpass\b",
                r"raise\s+NotImplementedError",
                r"return\s+True\b",
                r"return\s+False\b",
                r"return\s+None\b",
                r"execute_business_rule",
            ]

        if target == "csharp":
            return common + [
                r"NotImplementedException",
                r"return\s+true\s*;",
                r"return\s+false\s*;",
                r"ExecuteBusinessRule",
            ]

        return common + [
            r"UnsupportedOperationException",
            r"return\s+true\s*;",
            r"return\s+false\s*;",
            r"executeBusinessRule",
        ]

    def _is_placeholder_code(self, content: str, target_language: str) -> bool:
        lower = (content or "").lower()
        if "extends exception" in lower or "extends runtimeexception" in lower:
            return False

        for pattern in self._placeholder_patterns(target_language):
            if re.search(pattern, content or "", flags=re.IGNORECASE | re.DOTALL):
                return True

        non_comment_lines = [
            line.strip()
            for line in (content or "").splitlines()
            if line.strip()
            and not line.strip().startswith(("//", "/*", "*"))
            and not line.strip().startswith("@")
        ]
        if len(non_comment_lines) <= 6 and "class " in lower:
            return True
        return False

    @staticmethod
    def _copybook_service_misroute(source_name: str, rel_path: str, content: str) -> bool:
        if not (source_name or "").lower().endswith(".cpy"):
            return False
        if "/model/" in rel_path or "/dto/" in rel_path or "\\model\\" in rel_path:
            return False
        if "executeBusinessRule" in content:
            return True
        return rel_path.lower().endswith("service.java") and "@applicationscoped" in content.lower()

    def _implementation_signal_count(self, content: str, target_language: str) -> int:
        target = self._normalize_target(target_language)

        if target == "python":
            without_comments = "\n".join(
                line.split("#", 1)[0]
                for line in (content or "").splitlines()
            )
            signals = [
                r"\bif\s+",
                r"\bfor\s+",
                r"\bwhile\s+",
                r"\breturn\b",
                r"\braise\b",
                r"\bwith\s+",
                r"\btry\s*:",
                r"\bexcept\s+",
                r"\.[a-zA-Z_][A-Za-z0-9_]*\(",
                r"\b[a-zA-Z_][A-Za-z0-9_]*\(",
                r"=\s*[^=]",
                r"\+|-|\*|/",
            ]
        else:
            without_comments = re.sub(r"//.*|/\*.*?\*/", "", content or "", flags=re.DOTALL)
            signals = [
                r"\bif\s*\(",
                r"\bswitch\s*\(",
                r"\bfor(?:each)?\s*\(",
                r"\bwhile\s*\(",
                r"\breturn\s+[^;]+;",
                r"\bthrow\b",
                r"\bnew\b",
                r"\.[a-zA-Z_][A-Za-z0-9_]*\(",
                r"=\s*[^=]",
                r"\+|-|\*|/",
            ]

        return sum(len(re.findall(pattern, without_comments)) for pattern in signals)

    @staticmethod
    def _comment_only_method_count(content: str) -> int:
        count = 0
        method_pattern = re.compile(
            r"\bpublic\s+(?:static\s+)?[A-Za-z0-9_<>\[\], ?]+\s+"
            r"[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\)\s*\{(?P<body>.*?)\n\s*\}",
            flags=re.DOTALL,
        )
        for match in method_pattern.finditer(content or ""):
            body = match.group("body")
            body_without_comments = re.sub(r"//.*|/\*.*?\*/", "", body, flags=re.DOTALL).strip()
            if not body_without_comments:
                count += 1
        return count

    @staticmethod
    def _source_for_generated_file(manifest: dict[str, Any], rel_path: str) -> str:
        for item in manifest.get("files") or []:
            if item.get("path") == rel_path:
                return item.get("source_file") or ""
        return ""

    @staticmethod
    def _name_coverage(names: list[Any], code_files: list[Path]) -> dict[str, Any]:
        unique_names = sorted({str(name or "").strip() for name in names if str(name or "").strip()})
        combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in code_files)
        covered = [
            name
            for name in unique_names
            if re.search(rf"\b{re.escape(name)}\b", combined)
        ]
        total = len(unique_names)
        return {
            "total": total,
            "covered": len(covered),
            "ratio": (len(covered) / total) if total else 1.0,
        }

    @staticmethod
    def _method_coverage(names: list[Any], code_files: list[Path]) -> dict[str, Any]:
        unique_names = sorted({str(name or "").strip() for name in names if str(name or "").strip()})
        combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in code_files)
        covered = [
            name
            for name in unique_names
            if re.search(rf"\b{re.escape(name)}\s*\(", combined)
        ]
        total = len(unique_names)
        return {
            "total": total,
            "covered": len(covered),
            "ratio": (len(covered) / total) if total else 1.0,
        }

    @staticmethod
    def _registry_items_for_sources(
        items: list[dict[str, Any]],
        source_files: set[str],
    ) -> list[dict[str, Any]]:
        if not source_files:
            return items
        return [
            item
            for item in items
            if str(item.get("filename") or "") in source_files
        ]

    @staticmethod
    def _is_bad_fallback_plan(plan: dict[str, Any], source_files: dict[str, ProjectFile]) -> bool:
        summary = str(plan.get("summary") or "").lower()
        assumptions = " ".join(str(item).lower() for item in plan.get("assumptions") or [])
        source_file = str(plan.get("source_file") or "")
        source = source_files.get(source_file)
        filename = (source_file or "").lower()

        is_data_copybook = bool(source and filename.endswith(".cpy") and "data copybook" in summary)
        if is_data_copybook:
            return False
        return "deterministic conversion plan" in summary or "fallback plan created" in assumptions

    @staticmethod
    def _is_convertible_source(filename: str | None, detected_lang: str | None) -> bool:
        name = (filename or "").lower()
        lang = (detected_lang or "").lower()
        return (
            name.endswith((".cbl", ".cob", ".cpy", ".tel", ".tln"))
            or "telon" in lang
            or ("cobol" in lang and not name.endswith((".txt", ".md", ".json", ".xml")))
        )

    @staticmethod
    def _write_latest_quality(output_root: Path, target_language: str, result: dict[str, Any]) -> None:
        quality_dir = output_root / "quality" / target_language
        quality_dir.mkdir(parents=True, exist_ok=True)
        (quality_dir / "latest_quality.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def _output_root(run_id: str) -> Path:
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / "output" / "generated_code" / run_id

    @staticmethod
    def _project_dir(run_id: str, target_language: str) -> Path:
        return (
            GenerationQualityService._output_root(run_id)
            / "project"
            / target_language
        )

    @staticmethod
    def _normalize_target(target_language: str) -> str:
        value = str(target_language or "").lower().strip()

        if value in {"python", "py", "fastapi"}:
            return "python"

        if value in {"csharp", "c#", "cs", "dotnet"}:
            return "csharp"

        return "java"
