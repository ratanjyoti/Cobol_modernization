import re
from pathlib import Path
from typing import Any


class PlanSanitizerService:
    """
    Sanitizes conversion plans and generated output paths for Java, Python, and C#.

    Fixes:
    - output paths ending in .cbl/.cob/.cpy/.txt
    - invalid class/module names
    - wrong folder layouts
    - duplicate folder/class paths
    - Java Maven layout
    - Python FastAPI layout
    - C# ASP.NET Core layout
    """

    INVALID_OUTPUT_EXTENSIONS = {
        ".cbl",
        ".cob",
        ".cpy",
        ".jcl",
        ".tel",
        ".tln",
        ".txt",
        ".dat",
        ".csv",
    }

    JAVA_BASE = "src/main/java/com/modernizer/migration"

    def sanitize_plan(
        self,
        raw_plan: dict[str, Any],
        source_file: str,
        target_language: str,
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)

        if target not in {"java", "python", "csharp"}:
            return raw_plan

        plan = dict(raw_plan or {})
        classes = []

        for item in plan.get("classes", []) or []:
            if not isinstance(item, dict):
                continue

            sanitized = dict(item)

            source_path = source_file or plan.get("source_file") or ""
            original_name = (
                sanitized.get("class_name")
                or sanitized.get("name")
                or sanitized.get("module_name")
                or Path(str(source_path)).stem
                or "MigratedProgram"
            )

            original_file_path = sanitized.get("file_path") or sanitized.get("path") or ""

            layer = self._normalize_layer(
                layer=sanitized.get("layer"),
                source_path=source_path,
                name=original_name,
                file_path=original_file_path,
            )

            if target == "java":
                class_name = self._sanitize_class_name(
                    original_name,
                    source_path=source_path,
                    layer=layer,
                )
                file_path = self._sanitize_java_file_path(
                    file_path=original_file_path,
                    class_name=class_name,
                    source_path=source_path,
                    layer=layer,
                )
                sanitized["class_name"] = class_name
                sanitized["file_path"] = file_path
                sanitized["layer"] = layer

            elif target == "python":
                module_name = self._sanitize_python_module_name(
                    original_name,
                    source_path=source_path,
                    layer=layer,
                )
                class_name = self._sanitize_class_name(
                    original_name,
                    source_path=source_path,
                    layer=layer,
                    preserve_suffix=False,
                )
                file_path = self._sanitize_python_file_path(
                    file_path=original_file_path,
                    module_name=module_name,
                    source_path=source_path,
                    layer=layer,
                )
                sanitized["class_name"] = class_name
                sanitized["module_name"] = module_name
                sanitized["file_path"] = file_path
                sanitized["layer"] = layer

            elif target == "csharp":
                class_name = self._sanitize_class_name(
                    original_name,
                    source_path=source_path,
                    layer=layer,
                )
                file_path = self._sanitize_csharp_file_path(
                    file_path=original_file_path,
                    class_name=class_name,
                    source_path=source_path,
                    layer=layer,
                )
                sanitized["class_name"] = class_name
                sanitized["file_path"] = file_path
                sanitized["layer"] = layer

            classes.append(sanitized)

        plan["classes"] = classes

        methods = []
        valid_class_names = {item.get("class_name") for item in classes if item.get("class_name")}

        fallback_class = (
            classes[0].get("class_name")
            if classes
            else self._sanitize_class_name(
                Path(source_file or "MigratedProgram").stem,
                source_path=source_file,
                layer="service",
            )
        )

        for item in plan.get("methods", []) or []:
            if not isinstance(item, dict):
                continue

            sanitized_method = dict(item)

            owning_class = (
                sanitized_method.get("owning_class")
                or sanitized_method.get("class")
                or fallback_class
            )

            owning_class = self._sanitize_class_name(
                owning_class,
                source_path=source_file,
                layer="service",
                preserve_suffix=True,
            )

            if valid_class_names and owning_class not in valid_class_names:
                owning_class = fallback_class

            sanitized_method["owning_class"] = owning_class

            method_name = (
                sanitized_method.get("method_name")
                or sanitized_method.get("name")
                or "execute"
            )

            if target == "python":
                sanitized_method["method_name"] = self._sanitize_python_function_name(method_name)
            elif target == "csharp":
                sanitized_method["method_name"] = self._sanitize_csharp_method_name(method_name)
            else:
                sanitized_method["method_name"] = self._sanitize_java_method_name(method_name)

            methods.append(sanitized_method)

        plan["methods"] = methods
        return plan

    def sanitize_file_path_for_generated_file(
        self,
        path: str,
        source_file: str,
        target_language: str,
        file_type: str = "",
    ) -> str:
        target = self._normalize_target(target_language)
        layer = self._normalize_layer(file_type, source_file, path, path)

        if target == "java":
            class_name = self._sanitize_class_name(
                Path(path or source_file or "MigratedProgram").stem,
                source_path=source_file,
                layer=layer,
                preserve_suffix=True,
            )
            return self._sanitize_java_file_path(path, class_name, source_file, layer)

        if target == "python":
            module_name = self._sanitize_python_module_name(
                Path(path or source_file or "migrated_program").stem,
                source_path=source_file,
                layer=layer,
            )
            return self._sanitize_python_file_path(path, module_name, source_file, layer)

        if target == "csharp":
            class_name = self._sanitize_class_name(
                Path(path or source_file or "MigratedProgram").stem,
                source_path=source_file,
                layer=layer,
                preserve_suffix=True,
            )
            return self._sanitize_csharp_file_path(path, class_name, source_file, layer)

        return self._safe_relative_path(path)

    # ------------------------------------------------------------------
    # Java paths
    # ------------------------------------------------------------------

    def _sanitize_java_file_path(
        self,
        file_path: str,
        class_name: str,
        source_path: str,
        layer: str,
    ) -> str:
        clean_path = self._safe_relative_path(file_path)
        ext = Path(clean_path).suffix.lower()

        if ext in self.INVALID_OUTPUT_EXTENSIONS:
            return self._java_path_for_layer(class_name, layer)

        if not clean_path or not clean_path.endswith(".java"):
            return self._java_path_for_layer(class_name, layer)

        normalized = clean_path.replace("\\", "/").lstrip("/")
        normalized = self._remove_duplicate_parent(normalized)

        if not normalized.startswith("src/main/java/") and not normalized.startswith("src/test/java/"):
            return self._java_path_for_layer(class_name, layer)

        path_obj = Path(normalized)
        normalized = path_obj.parent.joinpath(f"{class_name}.java").as_posix()

        root_level_path = f"{self.JAVA_BASE}/{class_name}.java"
        if normalized == root_level_path:
            normalized = self._java_path_for_layer(class_name, layer)

        return normalized

    def _java_path_for_layer(self, class_name: str, layer: str) -> str:
        folder = {
            "program": "programs",
            "service": "services",
            "resource": "resources",
            "controller": "resources",
            "repository": "repositories",
            "dto": "dto",
            "model": "models",
            "domain": "models",
            "copybook": "copybooks",
            "batch": "batch",
            "adapter": "adapters",
            "exception": "exceptions",
            "test": "test",
        }.get(layer, "services")

        if layer == "test":
            return f"src/test/java/com/modernizer/migration/{folder}/{class_name}.java"

        return f"{self.JAVA_BASE}/{folder}/{class_name}.java"

    # ------------------------------------------------------------------
    # Python paths
    # ------------------------------------------------------------------

    def _sanitize_python_file_path(
        self,
        file_path: str,
        module_name: str,
        source_path: str,
        layer: str,
    ) -> str:
        clean_path = self._safe_relative_path(file_path)
        ext = Path(clean_path).suffix.lower()

        if ext in self.INVALID_OUTPUT_EXTENSIONS:
            return self._python_path_for_layer(module_name, layer)

        if not clean_path or not clean_path.endswith(".py"):
            return self._python_path_for_layer(module_name, layer)

        normalized = clean_path.replace("\\", "/").lstrip("/")
        normalized = self._remove_duplicate_parent(normalized)

        if not normalized.startswith("generated_app/") and not normalized.startswith("tests/"):
            return self._python_path_for_layer(module_name, layer)

        path_obj = Path(normalized)
        return path_obj.parent.joinpath(f"{module_name}.py").as_posix()

    def _python_path_for_layer(self, module_name: str, layer: str) -> str:
        folder = {
            "program": "programs",
            "service": "services",
            "resource": "routers",
            "controller": "routers",
            "repository": "repositories",
            "dto": "schemas",
            "model": "models",
            "domain": "models",
            "copybook": "copybooks",
            "batch": "batch",
            "adapter": "adapters",
            "exception": "exceptions",
            "test": "tests",
        }.get(layer, "services")

        if layer == "test":
            return f"tests/{module_name}.py"

        return f"generated_app/{folder}/{module_name}.py"

    # ------------------------------------------------------------------
    # C# paths
    # ------------------------------------------------------------------

    def _sanitize_csharp_file_path(
        self,
        file_path: str,
        class_name: str,
        source_path: str,
        layer: str,
    ) -> str:
        clean_path = self._safe_relative_path(file_path)
        ext = Path(clean_path).suffix.lower()

        if ext in self.INVALID_OUTPUT_EXTENSIONS:
            return self._csharp_path_for_layer(class_name, layer)

        if not clean_path or not clean_path.endswith(".cs"):
            return self._csharp_path_for_layer(class_name, layer)

        normalized = clean_path.replace("\\", "/").lstrip("/")
        normalized = self._remove_duplicate_parent(normalized)

        allowed_roots = {
            "Controllers",
            "Services",
            "Repositories",
            "Models",
            "DTOs",
            "Adapters",
            "Batch",
            "Exceptions",
            "Tests",
        }

        first = normalized.split("/", 1)[0]
        if first not in allowed_roots:
            return self._csharp_path_for_layer(class_name, layer)

        path_obj = Path(normalized)
        return path_obj.parent.joinpath(f"{class_name}.cs").as_posix()

    def _csharp_path_for_layer(self, class_name: str, layer: str) -> str:
        folder = {
            "program": "Services",
            "service": "Services",
            "resource": "Controllers",
            "controller": "Controllers",
            "repository": "Repositories",
            "dto": "DTOs",
            "model": "Models",
            "domain": "Models",
            "copybook": "Models",
            "batch": "Batch",
            "adapter": "Adapters",
            "exception": "Exceptions",
            "test": "Tests",
        }.get(layer, "Services")

        return f"{folder}/{class_name}.cs"

    # ------------------------------------------------------------------
    # Names
    # ------------------------------------------------------------------

    def _normalize_layer(
        self,
        layer: Any,
        source_path: str,
        name: str,
        file_path: str,
    ) -> str:
        value = str(layer or "").lower().strip()
        source_lower = str(source_path or "").lower()
        name_lower = str(name or "").lower()
        path_lower = str(file_path or "").lower()

        valid = {
            "program",
            "service",
            "resource",
            "controller",
            "repository",
            "dto",
            "model",
            "domain",
            "copybook",
            "batch",
            "adapter",
            "exception",
            "test",
        }

        if value in valid:
            return value

        if source_lower.endswith((".cpy", ".copybook")) or "copybook" in source_lower:
            return "copybook"

        if source_lower.endswith(".jcl"):
            return "batch"

        if "repository" in name_lower or "repository" in path_lower:
            return "repository"

        if "controller" in name_lower or "resource" in name_lower or "router" in name_lower:
            return "resource"

        if "dto" in name_lower or "schema" in name_lower:
            return "dto"

        if "exception" in name_lower:
            return "exception"

        if "adapter" in name_lower or "stub" in name_lower:
            return "adapter"

        if "test" in name_lower or "/test/" in path_lower or path_lower.startswith("tests/"):
            return "test"

        if source_lower.endswith((".cbl", ".cob", ".tel", ".tln")):
            return "program"

        return "service"

    def _sanitize_class_name(
        self,
        class_name: str,
        source_path: str,
        layer: str,
        preserve_suffix: bool = False,
    ) -> str:
        value = str(class_name or "").strip()
        value = Path(value.replace("\\", "/")).stem

        if Path(value).suffix.lower() in self.INVALID_OUTPUT_EXTENSIONS:
            value = Path(source_path or "MigratedProgram").stem

        parts = re.split(r"[^A-Za-z0-9]+", value)
        name = "".join(part[:1].upper() + part[1:].lower() for part in parts if part)

        if not name:
            name = "MigratedProgram"

        if name[0].isdigit():
            name = f"Program{name}"

        name = self._normalize_known_suffix_case(name)

        if preserve_suffix:
            return name

        name = self._strip_known_arch_suffix(name)

        suffix = {
            "program": "Service",
            "service": "Service",
            "resource": "Controller",
            "controller": "Controller",
            "repository": "Repository",
            "dto": "Dto",
            "model": "",
            "domain": "",
            "copybook": "",
            "batch": "Job",
            "adapter": "Adapter",
            "exception": "Exception",
            "test": "Test",
        }.get(layer, "Service")

        if suffix and not name.endswith(suffix):
            name += suffix

        return name

    def _sanitize_python_module_name(
        self,
        name: str,
        source_path: str,
        layer: str,
    ) -> str:
        value = str(name or "").strip()
        value = Path(value.replace("\\", "/")).stem

        if Path(value).suffix.lower() in self.INVALID_OUTPUT_EXTENSIONS:
            value = Path(source_path or "migrated_program").stem

        value = self._strip_known_arch_suffix(value)

        parts = re.split(r"[^A-Za-z0-9]+", value)
        snake = "_".join(part.lower() for part in parts if part)

        if not snake:
            snake = "migrated_program"

        if snake[0].isdigit():
            snake = f"program_{snake}"

        suffix = {
            "program": "service",
            "service": "service",
            "resource": "router",
            "controller": "router",
            "repository": "repository",
            "dto": "schema",
            "model": "model",
            "domain": "model",
            "copybook": "",
            "batch": "job",
            "adapter": "adapter",
            "exception": "exception",
            "test": "test",
        }.get(layer, "service")

        if suffix and not snake.endswith(f"_{suffix}"):
            snake += f"_{suffix}"

        return snake

    def _sanitize_java_method_name(self, method_name: str) -> str:
        return self._to_lower_camel(method_name, fallback="execute")

    def _sanitize_python_function_name(self, function_name: str) -> str:
        value = str(function_name or "execute").strip()
        parts = re.split(r"[^A-Za-z0-9]+", value)
        snake = "_".join(part.lower() for part in parts if part)

        if not snake:
            snake = "execute"

        if snake[0].isdigit():
            snake = f"method_{snake}"

        if snake in {"class", "return", "def", "import", "from", "None", "True", "False"}:
            snake += "_method"

        return snake

    def _sanitize_csharp_method_name(self, method_name: str) -> str:
        name = self._to_pascal_case(method_name, fallback="Execute")

        if name in {"Class", "Return", "Public", "Private", "Protected", "Static", "Void", "Int", "Long", "New"}:
            name += "Method"

        return name

    def _to_lower_camel(self, value: str, fallback: str) -> str:
        pascal = self._to_pascal_case(value, fallback=fallback[:1].upper() + fallback[1:])
        return pascal[:1].lower() + pascal[1:]

    def _to_pascal_case(self, value: str, fallback: str) -> str:
        parts = re.split(r"[^A-Za-z0-9]+", str(value or ""))
        name = "".join(part[:1].upper() + part[1:].lower() for part in parts if part)

        if not name:
            name = fallback

        if name[0].isdigit():
            name = f"Method{name}"

        return name

    @staticmethod
    def _normalize_known_suffix_case(name: str) -> str:
        suffixes = [
            "controller",
            "resource",
            "repository",
            "service",
            "dto",
            "model",
            "domain",
            "adapter",
            "exception",
            "test",
            "job",
        ]

        for suffix in suffixes:
            lower_name = name.lower()
            lower_suffix = suffix.lower()

            if lower_name.endswith(lower_suffix):
                base = name[: -len(suffix)]
                normalized_suffix = suffix[:1].upper() + suffix[1:]
                return base + normalized_suffix

        return name

    @staticmethod
    def _strip_known_arch_suffix(name: str) -> str:
        suffixes = [
            "Controller",
            "Resource",
            "Repository",
            "Service",
            "Dto",
            "DTO",
            "Schema",
            "Router",
            "Model",
            "Domain",
            "Adapter",
            "Exception",
            "Test",
            "Job",
        ]

        for suffix in suffixes:
            if name.endswith(suffix) and len(name) > len(suffix):
                return name[: -len(suffix)]

        return name

    def _remove_duplicate_parent(self, normalized_path: str) -> str:
        parts = normalized_path.split("/")

        if len(parts) >= 2:
            parent = parts[-2]
            filename_stem = Path(parts[-1]).stem

            if parent.lower() == filename_stem.lower():
                return "/".join(parts[:-2] + [parts[-1]])

        return normalized_path

    def _safe_relative_path(self, path: str) -> str:
        value = str(path or "").replace("\\", "/").strip().lstrip("/")

        if not value:
            return ""

        parts = [
            part
            for part in value.split("/")
            if part and part not in {".", ".."}
        ]

        return "/".join(parts)

    def _normalize_target(self, target_language: str) -> str:
        value = str(target_language or "").lower().strip()

        if value in {"c#", "cs", "dotnet", "csharp"}:
            return "csharp"

        if value in {"py", "python", "fastapi"}:
            return "python"

        if value in {"java", "quarkus"}:
            return "java"

        return value