# Convert bad planned output paths into proper Java Maven paths.

import re
from pathlib import Path
from typing import Any

from altair import layer

from altair import layer


class PlanSanitizerService:
    """
    Sanitizes conversion plans before they are saved or used for generation.

    Fixes:
    - output paths ending in .cbl/.cob/.cpy/.txt
    - Java class names containing hyphens
    - Java files outside Maven source layout
    - duplicate folder/class paths like DpicnumbersService/DpicnumbersService.java
    """

    INVALID_OUTPUT_EXTENSIONS = {
        ".cbl",
        ".cob",
        ".cpy",
        ".jcl",
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
        target = (target_language or "").lower().strip()

        if target != "java":
            return raw_plan

        plan = dict(raw_plan or {})
        classes = []

        for item in plan.get("classes", []) or []:
            if not isinstance(item, dict):
                continue

            sanitized = dict(item)

            source_path = source_file or plan.get("source_file") or ""
            original_class_name = (
                sanitized.get("class_name")
                or sanitized.get("name")
                or Path(str(source_path)).stem
                or "MigratedProgram"
            )

            original_file_path = (
                sanitized.get("file_path")
                or sanitized.get("path")
                or ""
            )

            layer = self._normalize_layer(
                sanitized.get("layer"),
                source_path,
                original_class_name,
                original_file_path,
            )

            class_name = self._sanitize_class_name(
                original_class_name,
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

            classes.append(sanitized)

        plan["classes"] = classes

        methods = []
        valid_class_names = {item["class_name"] for item in classes}

        fallback_class = classes[0]["class_name"] if classes else self._sanitize_class_name(
            Path(source_file or "MigratedProgram").stem,
            source_path=source_file,
            layer="service",
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

            if owning_class not in valid_class_names:
                owning_class = fallback_class

            sanitized_method["owning_class"] = owning_class
            sanitized_method["method_name"] = self._sanitize_method_name(
                sanitized_method.get("method_name")
                or sanitized_method.get("name")
                or "execute"
            )

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
        target = (target_language or "").lower().strip()

        if target != "java":
            return self._safe_relative_path(path)

        layer = self._normalize_layer(file_type, source_file, path, path)
        class_name = self._sanitize_class_name(
            Path(path or source_file or "MigratedProgram").stem,
            source_path=source_file,
            layer=layer,
            preserve_suffix=True,
        )

        return self._sanitize_java_file_path(
            file_path=path,
            class_name=class_name,
            source_path=source_file,
            layer=layer,
        )

    def _sanitize_java_file_path(
        self,
        file_path: str,
        class_name: str,
        source_path: str,
        layer: str,
    ) -> str:
        clean_path = self._safe_relative_path(file_path)
        ext = Path(clean_path).suffix.lower()

        # If model returned COBOL/source filename as output, replace it.
        if ext in self.INVALID_OUTPUT_EXTENSIONS:
            return self._java_path_for_layer(class_name, layer)

        # If path is empty or not Java, construct correct path.
        if not clean_path or not clean_path.endswith(".java"):
            return self._java_path_for_layer(class_name, layer)

        normalized = clean_path.replace("\\", "/").lstrip("/")

        # Fix paths like DpicnumbersService/DpicnumbersService.java
        parts = normalized.split("/")
        if len(parts) >= 2:
            parent = parts[-2]
            filename_stem = Path(parts[-1]).stem
            if parent.lower() == filename_stem.lower():
                normalized = "/".join(parts[:-2] + [parts[-1]])

        # Ensure proper Maven layout.
        if not normalized.startswith("src/main/java/"):
            normalized = self._java_path_for_layer(class_name, layer)
            return normalized

        # Ensure file name matches sanitized class name.
        path_obj = Path(normalized)
        filename = f"{class_name}.java"
        normalized = path_obj.parent.joinpath(filename).as_posix()

        # If model placed everything in root package, add semantic layer.
        base = self.JAVA_BASE
        root_level_path = f"{base}/{filename}"
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

    def _normalize_layer(
        self,
        layer: Any,
        source_path: str,
        class_name: str,
        file_path: str,
    ) -> str:
        value = str(layer or "").lower().strip()
        source_lower = str(source_path or "").lower()
        class_lower = str(class_name or "").lower()
        path_lower = str(file_path or "").lower()

        if value in {
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
        }:
            return value

        if source_lower.endswith((".cpy", ".copybook")) or "/copybook" in source_lower or "\\copybook" in source_lower:
            return "copybook"

        if source_lower.endswith(".jcl"):
            return "batch"

        if "repository" in class_lower or "repository" in path_lower:
            return "repository"

        if "controller" in class_lower or "resource" in class_lower:
            return "resource"

        if "dto" in class_lower:
            return "dto"

        if "exception" in class_lower:
            return "exception"

        if "adapter" in class_lower or "stub" in class_lower:
            return "adapter"

        if "test" in class_lower or "/test/" in path_lower:
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

        # If model gave a path or filename, use only the stem.
        value = Path(value.replace("\\", "/")).stem

        # If the model gave a source file name as class name, use the source stem.
        if Path(value).suffix.lower() in self.INVALID_OUTPUT_EXTENSIONS:
            value = Path(source_path or "MigratedProgram").stem

        parts = re.split(r"[^A-Za-z0-9]+", value)
        name = "".join(part[:1].upper() + part[1:].lower() for part in parts if part)

        if not name:
            name = "MigratedProgram"

        if name[0].isdigit():
            name = f"Program{name}"

        # Normalize bad suffix casing:
        # Ccheckwsservice -> CcheckwsService
        # Copyr001Paddedcontroller -> Copyr001PaddedController
        # Dpicnumbersservice -> DpicnumbersService
        name = self._normalize_known_suffix_case(name)

        if preserve_suffix:
            return name

        # Remove existing architectural suffix before applying the correct one.
        name = self._strip_known_arch_suffix(name)

        suffix = {
            "program": "Service",
            "service": "Service",
            "resource": "Resource",
            "controller": "Resource",
            "repository": "Repository",
            "dto": "Dto",
            "model": "",
            "domain": "",
            "copybook": "",
            "batch": "Job",
            "adapter": "Adapter",
            "exception": "Exception",
            "test": "Test",
        }.get(  layer, "Service")

        if suffix and not name.endswith(suffix):
            name += suffix
    
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

    def _sanitize_method_name(self, method_name: str) -> str:
        value = str(method_name or "execute").strip()

        parts = re.split(r"[^A-Za-z0-9]+", value)
        parts = [part for part in parts if part]

        if not parts:
            return "execute"

        method = parts[0][:1].lower() + parts[0][1:]

        for part in parts[1:]:
            method += part[:1].upper() + part[1:]

        if method[0].isdigit():
            method = f"method{method}"

        reserved = {
            "class",
            "return",
            "public",
            "private",
            "protected",
            "static",
            "void",
            "int",
            "long",
            "new",
        }

        if method in reserved:
            method += "Method"

        return method

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