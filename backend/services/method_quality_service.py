import re
from pathlib import Path
from typing import Any


class MethodQualityService:
    """
    Detects weak generated code across Java, Python, and C#.

    It catches:
    - comment-only methods/functions
    - pass-only Python functions
    - placeholder return true / return True
    - NotImplemented-style methods
    - TODO/stub/placeholder bodies
    """

    JAVA_METHOD_RE = re.compile(
        r"""
        (?P<header>
            (?:public|private|protected)\s+
            (?:static\s+)?
            [A-Za-z0-9_<>\[\],\s?.]+\s+
            (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*
            \([^)]*\)\s*
        )
        \{
        """,
        re.VERBOSE | re.MULTILINE,
    )

    CSHARP_METHOD_RE = re.compile(
        r"""
        (?P<header>
            (?:public|private|protected|internal)\s+
            (?:static\s+)?
            (?:async\s+)?
            [A-Za-z0-9_<>\[\],\s?.]+\s+
            (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*
            \([^)]*\)\s*
        )
        \{
        """,
        re.VERBOSE | re.MULTILINE,
    )

    PYTHON_FUNCTION_RE = re.compile(
        r"""
        ^(?P<indent>[ \t]*)
        (?P<header>
            (?:async\s+)?
            def\s+
            (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*
            \([^)]*\)\s*
            (?:->\s*[^:]+)?
            :
        )
        """,
        re.VERBOSE | re.MULTILINE,
    )

    IGNORE_METHOD_NAMES = {
        "toString",
        "hashCode",
        "equals",
        "__str__",
        "__repr__",
        "__eq__",
        "__hash__",
    }

    PLACEHOLDER_PATTERNS = [
        r"\bTODO\b",
        r"\bFIXME\b",
        r"\bstub\b",
        r"\bplaceholder\b",
        r"\bnot\s+implemented\b",
        r"UnsupportedOperationException",
        r"NotImplementedException",
        r"NotImplementedError",
        r"return\s+true\s*;",
        r"return\s+false\s*;",
        r"return\s+True\b",
        r"return\s+False\b",
        r"return\s+None\b",
        r"\bpass\b",
    ]

    EXECUTABLE_PATTERNS = {
        "java": [
            r"\bif\s*\(",
            r"\bfor\s*\(",
            r"\bwhile\s*\(",
            r"\bswitch\s*\(",
            r"\breturn\b",
            r"\bthrow\b",
            r"\bnew\b",
            r"=",
            r"\+\+",
            r"--",
            r"\.\w+\s*\(",
            r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(",
            r"\btry\s*\{",
            r"\bcatch\s*\(",
            r"\bassert\b",
        ],
        "python": [
            r"\bif\s+",
            r"\bfor\s+",
            r"\bwhile\s+",
            r"\breturn\b",
            r"\braise\b",
            r"\bwith\s+",
            r"\btry\s*:",
            r"\bexcept\s+",
            r"\bassert\b",
            r"=",
            r"\.\w+\s*\(",
            r"\w+\s*\(",
        ],
        "csharp": [
            r"\bif\s*\(",
            r"\bfor\s*\(",
            r"\bforeach\s*\(",
            r"\bwhile\s*\(",
            r"\bswitch\s*\(",
            r"\breturn\b",
            r"\bthrow\b",
            r"\bnew\b",
            r"=",
            r"\+\+",
            r"--",
            r"\.\w+\s*\(",
            r"\btry\s*\{",
            r"\bcatch\s*\(",
            r"\bawait\b",
        ],
    }

    EXTENSIONS = {
        "java": ".java",
        "python": ".py",
        "csharp": ".cs",
    }

    def scan_project(
        self,
        project_dir: str | Path,
        target_language: str = "java",
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        root = Path(project_dir)
        extension = self.EXTENSIONS.get(target, ".java")

        if not root.exists():
            return {
                "success": False,
                "status": "PROJECT_DIR_NOT_FOUND",
                "target_language": target,
                "project_dir": str(root),
                "comment_only_methods": [],
                "placeholder_methods": [],
                "files_checked": 0,
                "count": 0,
            }

        comment_only_findings: list[dict[str, Any]] = []
        placeholder_findings: list[dict[str, Any]] = []
        files_checked = 0

        for path in sorted(root.rglob(f"*{extension}")):
            normalized = path.as_posix()

            if "/target/" in normalized or "/build/" in normalized or "/bin/" in normalized or "/obj/" in normalized:
                continue

            files_checked += 1
            text = path.read_text(encoding="utf-8", errors="ignore")
            relative_path = path.relative_to(root).as_posix()

            file_result = self.scan_file(
                content=text,
                relative_path=relative_path,
                target_language=target,
            )

            comment_only_findings.extend(file_result["comment_only_methods"])
            placeholder_findings.extend(file_result["placeholder_methods"])

        total_count = len(comment_only_findings) + len(placeholder_findings)

        return {
            "success": total_count == 0,
            "status": "PASSED" if total_count == 0 else "WEAK_METHODS_FOUND",
            "target_language": target,
            "project_dir": str(root),
            "files_checked": files_checked,
            "comment_only_methods": comment_only_findings,
            "placeholder_methods": placeholder_findings,
            "count": total_count,
        }

    def scan_file(
        self,
        content: str,
        relative_path: str,
        target_language: str = "java",
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)

        if target == "python":
            methods = self._extract_python_functions(content)
        elif target == "csharp":
            methods = self._extract_brace_methods(content, self.CSHARP_METHOD_RE)
        else:
            methods = self._extract_brace_methods(content, self.JAVA_METHOD_RE)

        comment_only: list[dict[str, Any]] = []
        placeholders: list[dict[str, Any]] = []

        for method in methods:
            method_name = method["method_name"]

            if method_name in self.IGNORE_METHOD_NAMES:
                continue

            if method["header"].lower().startswith("public record "):
                continue

            body = method["body"]

            if self._contains_placeholder(body):
                placeholders.append(
                    {
                        "file_path": relative_path,
                        "method_name": method_name,
                        "header": method["header"],
                        "body_preview": body.strip()[:500],
                        "reason": "placeholder_or_stub_pattern",
                    }
                )
                continue

            if self._is_comment_only_body(body, target):
                comment_only.append(
                    {
                        "file_path": relative_path,
                        "method_name": method_name,
                        "header": method["header"],
                        "body_preview": body.strip()[:500],
                        "reason": "comment_only_or_no_executable_logic",
                    }
                )

        return {
            "comment_only_methods": comment_only,
            "placeholder_methods": placeholders,
        }

    def _extract_brace_methods(
        self,
        content: str,
        pattern: re.Pattern,
    ) -> list[dict[str, str]]:
        methods: list[dict[str, str]] = []

        for match in pattern.finditer(content or ""):
            method_name = match.group("name")
            start_brace = content.find("{", match.start())
            end_brace = self._find_matching_brace(content, start_brace)

            if end_brace == -1:
                continue

            body = content[start_brace + 1:end_brace]

            methods.append(
                {
                    "method_name": method_name,
                    "header": match.group("header").strip(),
                    "body": body,
                }
            )

        return methods

    def _extract_python_functions(self, content: str) -> list[dict[str, str]]:
        methods: list[dict[str, str]] = []
        text = content or ""

        matches = list(self.PYTHON_FUNCTION_RE.finditer(text))

        for index, match in enumerate(matches):
            method_name = match.group("name")
            header = match.group("header").strip()
            indent = match.group("indent") or ""

            body_start = match.end()
            body_end = len(text)

            if index + 1 < len(matches):
                body_end = matches[index + 1].start()

            candidate_body = text[body_start:body_end]
            body = self._trim_python_body_to_indent(candidate_body, len(indent))

            methods.append(
                {
                    "method_name": method_name,
                    "header": header,
                    "body": body,
                }
            )

        return methods

    def _trim_python_body_to_indent(
        self,
        body: str,
        parent_indent_len: int,
    ) -> str:
        lines = body.splitlines()
        kept: list[str] = []

        for line in lines:
            if not line.strip():
                kept.append(line)
                continue

            current_indent = len(line) - len(line.lstrip(" \t"))

            if current_indent <= parent_indent_len:
                break

            kept.append(line)

        return "\n".join(kept)

    def _is_comment_only_body(
        self,
        body: str,
        target_language: str,
    ) -> bool:
        clean = self._remove_comments_and_blank_lines(body, target_language)

        if not clean.strip():
            return True

        for pattern in self.EXECUTABLE_PATTERNS.get(target_language, []):
            if re.search(pattern, clean):
                return False

        return True

    def _contains_placeholder(self, body: str) -> bool:
        text = body or ""

        for pattern in self.PLACEHOLDER_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True

        return False

    def _remove_comments_and_blank_lines(
        self,
        text: str,
        target_language: str,
    ) -> str:
        if target_language in {"java", "csharp"}:
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

            lines = []
            for line in text.splitlines():
                stripped = line.strip()

                if not stripped:
                    continue

                if stripped.startswith("//"):
                    continue

                stripped = re.sub(r"//.*$", "", stripped).strip()

                if stripped:
                    lines.append(stripped)

            return "\n".join(lines)

        if target_language == "python":
            lines = []

            for line in text.splitlines():
                stripped = line.strip()

                if not stripped:
                    continue

                if stripped.startswith("#"):
                    continue

                stripped = re.sub(r"#.*$", "", stripped).strip()

                if stripped:
                    lines.append(stripped)

            return "\n".join(lines)

        return text

    def _find_matching_brace(self, text: str, open_index: int) -> int:
        if open_index < 0 or open_index >= len(text):
            return -1

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

    def _normalize_target(self, target_language: str) -> str:
        value = str(target_language or "").lower().strip()

        if value in {"c#", "cs", "dotnet", "csharp"}:
            return "csharp"

        if value in {"py", "python", "fastapi"}:
            return "python"

        return "java"
