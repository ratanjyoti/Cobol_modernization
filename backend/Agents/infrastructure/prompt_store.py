

import re
from pathlib import Path
from typing import Any, Dict, List

class PromptStore:
    """
    The Orchestration Store. 
    Contains generic 'Blueprints' that agents fill with language-specific data.
    """
    PROMPT_FILES = {
        # Technical Analysis Blueprint
        "tech_analyzer_system": "technical_analysis_system.md",
        "tech_analyzer_user": "technical_analysis_user.md",
        
        # Method Repair Blueprint
        "method_repair_system": "method_repair_system.md",
        "method_repair_user": "method_repair_user.md",
        
        # Business Logic (Language specific system prompts are kept as they differ fundamentally)
        "biz_logic_system_cobol": "business_logic_cobol_system.md",
        "biz_logic_system_sql": "business_logic_sql_system.md",
        "biz_logic_system_generic": "business_logic_generic_system.md",
        "biz_logic_user": "business_logic_user_template.md",
        
        # Generation & Planning
        "planner_system": "conversion_planner_system.md",
        "planner_user": "conversion_planner_user.md",
        "gen_system": "code_generator_system.md",
        "gen_user": "code_generator_user.md",
        "fix_system": "compile_fix_system.md",
        "fix_user": "compile_fix_user.md",
    }

    def __init__(self, backend_root: str | Path | None = None):
        if backend_root is None:
            current = Path(__file__).resolve()
            self.backend_root = current.parents[2]
        else:
            self.backend_root = Path(backend_root)

        self.default_prompt_dir = self.backend_root / "Agents" / "prompts" / "code_generation"
        self.project_storage_dir = self.backend_root / "storage" / "projects"

    def get_prompt(self, key: str, project_id: str = "default") -> str:
        # Standard lookup logic: Override -> Default
        safe_project_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(project_id)).strip()
        
        # Try Project Override
        filename = self.PROMPT_FILES.get(key)
        if not filename: return f"Error: Key {key} not found in registry"
        
        override_path = self.project_storage_dir / safe_project_id / "prompts" / "code_generation" / filename
        if override_path.exists():
            return override_path.read_text(encoding="utf-8", errors="ignore").strip()

        # Try Default
        default_path = self.default_prompt_dir / filename
        return default_path.read_text(encoding="utf-8", errors="ignore").strip() if default_path.exists() else ""

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """The Orchestrator's rendering engine."""
        rendered = template
        for key, value in variables.items():
            pattern = r"{{\s*" + re.escape(key) + r"\s*}}"
            rendered = re.sub(pattern, str(value or ""), rendered)
        return rendered

    def list_prompts(self, project_id: str = "default") -> List[Dict[str, Any]]:
        # Used by Prompt Studio to show all available blueprints
        prompts = []
        for key, filename in self.PROMPT_FILES.items():
            content = self.get_prompt(key, project_id)
            prompts.append({
                "key": key, 
                "name": key.replace("_", " ").title(),
                "filename": filename,
                "content": content,
                "project_id": project_id
            })
        return prompts
