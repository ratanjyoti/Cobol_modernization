# Agents/implementations/language_analysis_agent.py

import yaml
from typing import Any
from Agents.infrastructure.prompt_store import PromptStore

class LanguageAnalysisAgent:
    """
    ORCHESTRATOR: Performs technical analysis by injecting
    source-specific data into generic analysis blueprints.
    """

    def __init__(self, llm_client, prompt_store=None):
        self.llm = llm_client
        self.prompt_store = prompt_store or PromptStore()

    def analyze(self, *, language: str, filename: str, source_content: str, 
                global_types: Any = None, signatures: Any = None, 
                context_summary: str = "", project_id: str = "default") -> dict:
        
        # 1. Load Blueprints
        system_prompt = self.prompt_store.get_prompt("tech_analyzer_system", project_id)
        user_template = self.prompt_store.get_prompt("tech_analyzer_user", project_id)

        # 2. Orchestrate: Fill the blueprint with this specific file's data
        user_prompt = self.prompt_store.render(user_template, {
            "language": language,
            "filename": filename,
            "global_types": global_types or {},
            "signatures": signatures or {},
            "context_summary": context_summary or "No previous context.",
            "source_content": source_content
        })

        response = self.llm.generate(system_prompt, user_prompt)
        cleaned = self._remove_markdown_fences(response)

        try:
            decoded = yaml.safe_load(cleaned)
            if not isinstance(decoded, dict): raise ValueError("Not a YAML object")
            decoded["language"] = decoded.get("language") or language
            decoded["parse_success"] = True
            return decoded
        except Exception as exc:
            return {"language": language, "raw_output": cleaned, "parse_success": False, "parse_error": str(exc)}

    @staticmethod
    def _remove_markdown_fences(value: Any) -> str:
        text = str(value or "").strip()
        return re.sub(r"```(?:yaml|yml|json)?\s*(.*?)\s*```", r"\1", text, flags=re.DOTALL).strip()
