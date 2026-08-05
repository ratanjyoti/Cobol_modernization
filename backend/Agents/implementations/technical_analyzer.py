import json
import re
from typing import Dict, List

from pydantic import BaseModel

from Agents.infrastructure.agent_base import AgentBase
from Agents.infrastructure.prompt_store import PromptStore
from Agents.models.analysis_models import TechnicalAnalysisReport

class DataStructure(BaseModel):
    name: str
    fields: List[Dict[str, str]]

class LogicStep(BaseModel):
    step_number: int
    description: str
    technical_trigger: str


class TechnicalAnalyzerAgent(AgentBase):
    def __init__(self, llm_client, prompt_store: PromptStore | None = None):
        self.llm_client = llm_client
        self.prompt_store = prompt_store or PromptStore()

    async def analyze_skeleton(self, content: str, global_types: str, project_id: str = "default"):
        system_prompt = self.prompt_store.get_prompt("technical_analysis_system", project_id)
        user_template = self.prompt_store.get_prompt("technical_analysis_user", project_id)
        user_prompt = self.prompt_store.render(
            user_template,
            {
                "content": content,
                "global_types": global_types,
            },
        )

        response = await self.llm_client.generate(system_prompt, user_prompt)
        return self._strip_code_fence(response)

    async def analyze_deep(self, content: str, lang: str, project_id: str = "default"):
        system_prompt = self.prompt_store.get_prompt("technical_deep_system", project_id)
        user_template = self.prompt_store.get_prompt("technical_deep_user", project_id)
        user_prompt = self.prompt_store.render(
            user_template,
            {
                "content": content,
                "lang": lang,
            },
        )

        response = await self.llm_client.generate(system_prompt, user_prompt)
        cleaned = self._strip_code_fence(response)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            data = self._safe_json_extract(cleaned)

        return TechnicalAnalysisReport.model_validate(data)

    @staticmethod
    def _strip_code_fence(text: str | None) -> str:
        text = str(text or "").strip()

        fenced = re.search(
            r"```(?:json|yaml|yml)?\s*(.*?)\s*```",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        )

        if fenced:
            return fenced.group(1).strip()

        return text

    @staticmethod
    def _safe_json_extract(text: str):
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1 or end <= start:
            raise ValueError("No valid JSON object found in technical analysis response")

        return json.loads(text[start : end + 1])