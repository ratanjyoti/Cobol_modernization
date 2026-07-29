import re
from pathlib import Path
from typing import Any, Dict, List


class PromptStore:
    """
    File-based prompt manager.

    Default prompts:
      backend/Agents/prompts/code_generation/*.md

    Project overrides:
      backend/storage/projects/{project_id}/prompts/code_generation/*.md

    Rule:
      project override first, default prompt second
    """

    PROMPT_FILES = {
        "conversion_planner_system": "conversion_planner_system.md",
        "conversion_planner_user": "conversion_planner_user.md",
        "code_generator_system": "code_generator_system.md",
        "code_generator_user": "code_generator_user.md",
        "compile_fix_system": "compile_fix_system.md",
        "compile_fix_user": "compile_fix_user.md",
    }

    def __init__(self, backend_root: str | Path | None = None):
        if backend_root is None:
            current = Path(__file__).resolve()
            self.backend_root = current.parents[2]
        else:
            self.backend_root = Path(backend_root)

        self.default_prompt_dir = (
            self.backend_root / "Agents" / "prompts" / "code_generation"
        )

        self.project_storage_dir = self.backend_root / "storage" / "projects"

    def list_prompts(self, project_id: str = "default") -> List[Dict[str, Any]]:
        safe_project_id = self._safe_project_id(project_id)
        prompts = []

        for key, filename in self.PROMPT_FILES.items():
            default_path = self.default_prompt_dir / filename
            override_path = self._override_path(safe_project_id, key)

            default_content = self._read_text(default_path)
            has_override = override_path.exists()
            content = self._read_text(override_path) if has_override else default_content

            prompts.append({
                "key": key,
                "name": self._display_name(key),
                "filename": filename,
                "content": content,
                "default_content": default_content,
                "has_override": has_override,
                "project_id": safe_project_id,
            })

        return prompts

    def get_prompt(self, key: str, project_id: str = "default") -> str:
        safe_key = self._safe_key(key)
        safe_project_id = self._safe_project_id(project_id)

        override_path = self._override_path(safe_project_id, safe_key)
        if override_path.exists():
            return self._read_text(override_path)

        default_path = self.default_prompt_dir / self.PROMPT_FILES[safe_key]
        return self._read_text(default_path)

    def save_override(self, key: str, content: str, project_id: str = "default") -> Dict[str, Any]:
        safe_key = self._safe_key(key)
        safe_project_id = self._safe_project_id(project_id)

        override_path = self._override_path(safe_project_id, safe_key)
        override_path.parent.mkdir(parents=True, exist_ok=True)
        override_path.write_text(content or "", encoding="utf-8")

        return {
            "key": safe_key,
            "project_id": safe_project_id,
            "has_override": True,
            "path": str(override_path),
        }

    def reset_override(self, key: str, project_id: str = "default") -> Dict[str, Any]:
        safe_key = self._safe_key(key)
        safe_project_id = self._safe_project_id(project_id)

        override_path = self._override_path(safe_project_id, safe_key)
        if override_path.exists():
            override_path.unlink()

        return {
            "key": safe_key,
            "project_id": safe_project_id,
            "has_override": False,
        }

    def get_bundle(self, project_id: str = "default") -> Dict[str, str]:
        return {
            key: self.get_prompt(key, project_id)
            for key in self.PROMPT_FILES.keys()
        }

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Simple placeholder renderer.

        Example:
          {{technical_yaml}}
          {{ business_rules_json }}
        """

        rendered = template

        for key, value in variables.items():
            pattern = r"{{\s*" + re.escape(key) + r"\s*}}"
            rendered = re.sub(pattern, str(value or ""), rendered)

        return rendered

    def _override_path(self, project_id: str, key: str) -> Path:
        filename = self.PROMPT_FILES[key]
        return (
            self.project_storage_dir
            / project_id
            / "prompts"
            / "code_generation"
            / filename
        )

    def _safe_key(self, key: str) -> str:
        normalized = str(key or "").strip()

        if normalized not in self.PROMPT_FILES:
            raise ValueError(
                f"Unknown prompt key '{key}'. Allowed keys: {list(self.PROMPT_FILES.keys())}"
            )

        return normalized

    @staticmethod
    def _safe_project_id(project_id: str) -> str:
        value = str(project_id or "default").strip()
        value = re.sub(r"[^a-zA-Z0-9_.-]", "_", value)
        return value or "default"

    @staticmethod
    def _read_text(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _display_name(key: str) -> str:
        return key.replace("_", " ").title()