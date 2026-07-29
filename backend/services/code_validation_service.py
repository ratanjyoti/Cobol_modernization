import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


class CodeValidationService:
    """
    Runs basic validation for generated projects.

    Java:
      mvn compile

    Python:
      python -m py_compile all .py files

    C#:
      dotnet build
    """

    def validate(self, project_dir: Path, target_language: str) -> dict[str, Any]:
        target = (target_language or "java").lower().strip()

        if not project_dir.exists():
            return {
                "success": False,
                "target_language": target,
                "project_dir": str(project_dir),
                "command": "",
                "stdout": "",
                "stderr": f"Project directory does not exist: {project_dir}",
                "returncode": -1,
            }

        if target == "java":
            return self._validate_java(project_dir)

        if target == "python":
            return self._validate_python(project_dir)

        if target in {"csharp", "c#", "cs"}:
            return self._run_command(
                project_dir=project_dir,
                command=["dotnet", "build"],
                target_language="csharp",
                timeout=180,
            )

        return {
            "success": False,
            "target_language": target,
            "project_dir": str(project_dir),
            "command": "",
            "stdout": "",
            "stderr": f"Unsupported target language: {target_language}",
            "returncode": -1,
        }

    def _validate_java(self, project_dir: Path) -> dict[str, Any]:
        if shutil.which("mvn"):
            return self._run_command(
                project_dir=project_dir,
                command=["mvn", "compile"],
                target_language="java",
                timeout=180,
            )

        java_files = [
            path
            for path in project_dir.rglob("*.java")
            if "target" not in path.parts
        ]

        return {
            "success": False,
            "status": "TOOL_MISSING",
            "download_allowed": False,
            "target_language": "java",
            "project_dir": str(project_dir),
            "command": "mvn compile",
            "stdout": "",
            "stderr": "Required tool 'mvn' was not found on this machine. Install Maven or validate on a build server before download.",
            "returncode": -1,
            "checked_files": [str(path.relative_to(project_dir)) for path in java_files],
            "failed_files": [str(path.relative_to(project_dir)) for path in java_files],
        }

    @staticmethod
    def _java_source_issue(file_path: Path, content: str) -> str:
        if not content.strip():
            return "file is empty"

        lower = content.lower()
        if "todo: implement business logic" in lower or "placeholder" in lower:
            return "contains placeholder implementation text"

        public_class = re.search(r"\bpublic\s+(?:final\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)", content)
        if public_class and public_class.group(1) != file_path.stem:
            return f"public class {public_class.group(1)} does not match file name {file_path.stem}"

        if "src\\main\\java" in str(file_path) or "src/main/java" in file_path.as_posix():
            if not re.search(r"^\s*package\s+[A-Za-z_][A-Za-z0-9_.]*\s*;", content, re.MULTILINE):
                return "missing package declaration"

        if content.count("{") != content.count("}"):
            return "unbalanced braces"

        if re.search(r"\bendIf\s*\(", content):
            return "contains COBOL-like endIf method call"

        return ""

    def _validate_python(self, project_dir: Path) -> dict[str, Any]:
        python_files = [
            path
            for path in project_dir.rglob("*.py")
            if "__pycache__" not in path.parts
        ]

        if not python_files:
            return {
                "success": False,
                "target_language": "python",
                "project_dir": str(project_dir),
                "command": "python -m py_compile <files>",
                "stdout": "",
                "stderr": "No Python files were found to validate.",
                "returncode": -1,
            }

        all_stdout = []
        all_stderr = []
        failed = []

        for file_path in python_files:
            result = self._run_command(
                project_dir=project_dir,
                command=["python", "-m", "py_compile", str(file_path)],
                target_language="python",
                timeout=60,
            )

            if result["stdout"]:
                all_stdout.append(result["stdout"])

            if result["stderr"]:
                all_stderr.append(f"{file_path}:\n{result['stderr']}")

            if not result["success"]:
                failed.append(str(file_path.relative_to(project_dir)))

        return {
            "success": len(failed) == 0,
            "target_language": "python",
            "project_dir": str(project_dir),
            "command": "python -m py_compile <all .py files>",
            "stdout": "\n".join(all_stdout),
            "stderr": "\n\n".join(all_stderr),
            "returncode": 0 if len(failed) == 0 else 1,
            "checked_files": [str(path.relative_to(project_dir)) for path in python_files],
            "failed_files": failed,
        }

    def _run_command(
        self,
        project_dir: Path,
        command: list[str],
        target_language: str,
        timeout: int,
    ) -> dict[str, Any]:
        try:
            result = subprocess.run(
                command,
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )

            return {
                "success": result.returncode == 0,
                "target_language": target_language,
                "project_dir": str(project_dir),
                "command": " ".join(command),
                "stdout": result.stdout[-8000:],
                "stderr": result.stderr[-8000:],
                "returncode": result.returncode,
            }

        except FileNotFoundError:
            tool = command[0]
            return {
                "success": False,
                "target_language": target_language,
                "project_dir": str(project_dir),
                "command": " ".join(command),
                "stdout": "",
                "stderr": (
                    f"Required tool '{tool}' was not found on this machine. "
                    f"Install it or run validation on a machine where '{tool}' is available."
                ),
                "returncode": -1,
            }

        except subprocess.TimeoutExpired as exc:
            return {
                "success": False,
                "target_language": target_language,
                "project_dir": str(project_dir),
                "command": " ".join(command),
                "stdout": (exc.stdout or "")[-8000:] if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "")[-8000:] if isinstance(exc.stderr, str) else "Validation timed out.",
                "returncode": -1,
            }

        except Exception as exc:
            return {
                "success": False,
                "target_language": target_language,
                "project_dir": str(project_dir),
                "command": " ".join(command),
                "stdout": "",
                "stderr": str(exc),
                "returncode": -1,
            }
