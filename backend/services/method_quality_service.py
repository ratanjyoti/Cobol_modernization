import re
from pathlib import Path
from typing import Any


class MethodQualityService:
    """
    Detects generated methods that contain only comments/blank lines
    and no real executable Java statements.
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

    EXECUTABLE_PATTERNS = [
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
        r"\btry\s*\{",
        r"\bcatch\s*\(",
        r"\bassert\b",
    ]

    IGNORE_METHOD_NAMES = {
        "toString",
        "hashCode",
        "equals",
    }

    def scan_project(
        self,
        project_dir: str | Path,
    ) -> dict[str, Any]:
        root = Path(project_dir)

        if not root.exists():
            return {
                "success": False,
                "status": "PROJECT_DIR_NOT_FOUND",
                "comment_only_methods": [],
                "files_checked": 0,
                "count": 0,
                "project_dir": str(root),
            }

        findings: list[dict[str, Any]] = []
        files_checked = 0

        for path in sorted(root.rglob("*.java")):
            # Skip generated build folders if any
            normalized = path.as_posix()
            if "/target/" in normalized or "/build/" in normalized:
                continue

            files_checked += 1
            text = path.read_text(encoding="utf-8", errors="ignore")

            file_findings = self.scan_java_file(
                content=text,
                relative_path=path.relative_to(root).as_posix(),
            )

            findings.extend(file_findings)

        return {
            "success": len(findings) == 0,
            "status": "PASSED" if not findings else "COMMENT_ONLY_METHODS_FOUND",
            "comment_only_methods": findings,
            "files_checked": files_checked,
            "count": len(findings),
        }

    def scan_java_file(
        self,
        content: str,
        relative_path: str,
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        for match in self.JAVA_METHOD_RE.finditer(content or ""):
            method_name = match.group("name")

            if method_name in self.IGNORE_METHOD_NAMES:
                continue

            start_brace = content.find("{", match.start())
            end_brace = self._find_matching_brace(content, start_brace)

            if end_brace == -1:
                continue

            body = content[start_brace + 1:end_brace]

            if self._is_comment_only_body(body):
                findings.append(
                    {
                        "file_path": relative_path,
                        "method_name": method_name,
                        "header": match.group("header").strip(),
                        "body_preview": body.strip()[:500],
                    }
                )

        return findings

    def _is_comment_only_body(self, body: str) -> bool:
        clean = self._remove_comments_and_blank_lines(body)

        if not clean.strip():
            return True

        for pattern in self.EXECUTABLE_PATTERNS:
            if re.search(pattern, clean):
                return False

        return True

    def _remove_comments_and_blank_lines(self, text: str) -> str:
        # Remove block comments
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

        lines = []

        for line in text.splitlines():
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("//"):
                continue

            # Remove trailing inline comment
            stripped = re.sub(r"//.*$", "", stripped).strip()

            if stripped:
                lines.append(stripped)

        return "\n".join(lines)

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