import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class CodeValidationService:
    """
    Language-aware validation service.

    Java:
        Uses mvnw.cmd/mvnw if present, otherwise mvn compile.

    Python:
        Uses current Python executable to run compileall against generated_app and tests.

    C#:
        Uses dotnet build.
    """

    def validate(
        self,
        project_dir: str | Path,
        target_language: str,
        timeout_seconds: int = 120,
    ) -> dict[str, Any]:
        target = self._normalize_target(target_language)
        root = Path(project_dir)

        if not root.exists():
            return self._result(
                success=False,
                status="PROJECT_DIR_NOT_FOUND",
                target_language=target,
                project_dir=root,
                command=[],
                stdout="",
                stderr=f"Project directory not found: {root}",
                returncode=-1,
                download_allowed=False,
            )

        if target == "java":
            return self._validate_java(root, timeout_seconds)

        if target == "python":
            return self._validate_python(root, timeout_seconds)

        if target == "csharp":
            return self._validate_csharp(root, timeout_seconds)

        return self._result(
            success=False,
            status="UNSUPPORTED_TARGET_LANGUAGE",
            target_language=target,
            project_dir=root,
            command=[],
            stdout="",
            stderr=f"Unsupported target language: {target_language}",
            returncode=-1,
            download_allowed=False,
        )

    # ------------------------------------------------------------------
    # Java
    # ------------------------------------------------------------------

    def _validate_java(
        self,
        root: Path,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        mvnw_cmd = root / "mvnw.cmd"
        mvnw = root / "mvnw"

        if mvnw_cmd.exists():
            command = [str(mvnw_cmd), "compile"]
        elif mvnw.exists():
            command = [str(mvnw), "compile"]
        else:
            mvn = shutil.which("mvn")

            if not mvn:
                return self._static_validate_java(root)

            command = [mvn, "compile"]

        return self._run_command(
            command=command,
            cwd=root,
            target_language="java",
            timeout_seconds=timeout_seconds,
        )

    def _static_validate_java(self, root: Path) -> dict[str, Any]:
        java_files = sorted((root / "src").rglob("*.java")) if (root / "src").exists() else sorted(root.rglob("*.java"))
        errors: list[str] = []

        if not java_files:
            errors.append("No Java source files found for static validation.")

        reserved_method_pattern = re.compile(
            r"\b(?:public|private|protected)\s+[A-Za-z0-9_<>\[\], ?]+\s+"
            r"(?:if|else|for|while|switch|case|default|class|return)\s*\(",
            flags=re.IGNORECASE,
        )

        placeholder_pattern = re.compile(
            r"\bTODO\b|\bFIXME\b|\bstub\b|\bplaceholder\b|\bnot\s+implemented\b|executeBusinessRule",
            flags=re.IGNORECASE,
        )

        for path in java_files:
            content = path.read_text(encoding="utf-8", errors="ignore")
            rel = path.relative_to(root).as_posix()
            if content.count("{") != content.count("}"):
                errors.append(f"{rel}: unbalanced braces")
            if reserved_method_pattern.search(content):
                errors.append(f"{rel}: reserved Java keyword used as a method name")
            if placeholder_pattern.search(content):
                errors.append(f"{rel}: placeholder marker found")
            if "class " not in content and "record " not in content and "interface " not in content:
                errors.append(f"{rel}: no Java type declaration found")
            declared_methods = set(
                re.findall(
                    r"\b(?:public|private|protected)\s+[A-Za-z0-9_<>\[\], ?]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
                    content,
                )
            )
            paragraph_calls = set(re.findall(r"\b(p\d[A-Za-z0-9_]*)\s*\(", content))
            missing_calls = sorted(paragraph_calls - declared_methods)
            if missing_calls:
                errors.append(f"{rel}: missing generated paragraph method(s): {', '.join(missing_calls)}")

        success = not errors
        return self._result(
            success=success,
            status="STATIC_PASSED" if success else "STATIC_FAILED",
            target_language="java",
            project_dir=root,
            command=["static-java-validation"],
            stdout=(
                f"Static Java validation checked {len(java_files)} file(s). "
                "Maven/JDK was not available on this machine."
            ),
            stderr="\n".join(errors),
            returncode=0 if success else -1,
            download_allowed=success,
        )

    # ------------------------------------------------------------------
    # Python
    # ------------------------------------------------------------------

    def _validate_python(
        self,
        root: Path,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        python_exe = sys.executable or shutil.which("python") or shutil.which("python3")

        if not python_exe:
            return self._result(
                success=False,
                status="TOOL_MISSING",
                target_language="python",
                project_dir=root,
                command=["python", "-m", "compileall"],
                stdout="",
                stderr="Python executable was not found.",
                returncode=-1,
                download_allowed=False,
            )

        targets = []

        generated_app = root / "generated_app"
        tests = root / "tests"

        if generated_app.exists():
            targets.append("generated_app")

        if tests.exists():
            targets.append("tests")

        if not targets:
            # Fallback: compile all Python files in project root.
            py_files = list(root.rglob("*.py"))

            if not py_files:
                return self._result(
                    success=False,
                    status="NO_SOURCE_FILES",
                    target_language="python",
                    project_dir=root,
                    command=[python_exe, "-m", "compileall"],
                    stdout="",
                    stderr="No Python source files found to validate.",
                    returncode=-1,
                    download_allowed=False,
                )

            targets = ["."]

        command = [python_exe, "-m", "compileall", "-q", *targets]

        return self._run_command(
            command=command,
            cwd=root,
            target_language="python",
            timeout_seconds=timeout_seconds,
        )

    # ------------------------------------------------------------------
    # C#
    # ------------------------------------------------------------------

    def _validate_csharp(
        self,
        root: Path,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        dotnet = shutil.which("dotnet")

        if not dotnet:
            return self._result(
                success=False,
                status="TOOL_MISSING",
                target_language="csharp",
                project_dir=root,
                command=["dotnet", "build"],
                stdout="",
                stderr="dotnet SDK was not found. Install .NET SDK to validate C# output.",
                returncode=-1,
                download_allowed=False,
            )

        sln_files = sorted(root.glob("*.sln"))
        csproj_files = sorted(root.glob("*.csproj"))

        if sln_files:
            command = [dotnet, "build", str(sln_files[0].name)]
        elif csproj_files:
            command = [dotnet, "build", str(csproj_files[0].name)]
        else:
            return self._result(
                success=False,
                status="PROJECT_FILE_MISSING",
                target_language="csharp",
                project_dir=root,
                command=[dotnet, "build"],
                stdout="",
                stderr="No .sln or .csproj file found in generated C# project.",
                returncode=-1,
                download_allowed=False,
            )

        return self._run_command(
            command=command,
            cwd=root,
            target_language="csharp",
            timeout_seconds=timeout_seconds,
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _run_command(
        self,
        command: list[str],
        cwd: Path,
        target_language: str,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd),
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                shell=False,
            )

            success = completed.returncode == 0

            return self._result(
                success=success,
                status="PASSED" if success else "FAILED",
                target_language=target_language,
                project_dir=cwd,
                command=command,
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
                download_allowed=success,
            )

        except subprocess.TimeoutExpired as exc:
            return self._result(
                success=False,
                status="TIMEOUT",
                target_language=target_language,
                project_dir=cwd,
                command=command,
                stdout=exc.stdout or "",
                stderr=exc.stderr or f"Validation timed out after {timeout_seconds} seconds.",
                returncode=-1,
                download_allowed=False,
            )

        except Exception as exc:
            return self._result(
                success=False,
                status="VALIDATION_ERROR",
                target_language=target_language,
                project_dir=cwd,
                command=command,
                stdout="",
                stderr=str(exc),
                returncode=-1,
                download_allowed=False,
            )

    def _result(
        self,
        success: bool,
        status: str,
        target_language: str,
        project_dir: Path,
        command: list[str],
        stdout: str,
        stderr: str,
        returncode: int,
        download_allowed: bool,
    ) -> dict[str, Any]:
        return {
            "success": bool(success),
            "status": status,
            "target_language": target_language,
            "project_dir": str(project_dir),
            "command": command,
            "command_text": " ".join(command),
            "stdout": stdout or "",
            "stderr": stderr or "",
            "returncode": returncode,
            "download_allowed": bool(download_allowed and success),
        }

    def _normalize_target(self, target_language: str) -> str:
        value = str(target_language or "").lower().strip()

        if value in {"python", "py", "fastapi"}:
            return "python"

        if value in {"csharp", "c#", "cs", "dotnet"}:
            return "csharp"

        return "java"
