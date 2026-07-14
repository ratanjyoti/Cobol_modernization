from typing import Dict, List

from pydantic import BaseModel

from Agents.infrastructure.agent_base import AgentBase
from Agents.models.analysis_models import TechnicalAnalysisReport


class DataStructure(BaseModel):
    name: str
    fields: List[Dict[str, str]]


class LogicStep(BaseModel):
    step_number: int
    description: str
    technical_trigger: str


class TechnicalAnalyzerAgent(AgentBase):
    def __init__(self, llm_client):
        self.llm_client = llm_client

    async def analyze_deep(self, content: str, lang: str):
        prompt = f"""
        You are an expert Mainframe Modernization Architect.
        Analyze the following {lang} code and produce a comprehensive Technical Analysis Report.

        CODE:
        {content}

        REQUIREMENTS:
        1. BUSINESS PURPOSE: Provide a 3-5 sentence summary of the program's goal.
        2. DATA STRUCTURES: Extract all record layouts. For each field, provide the name, PIC clause, and a business description.
        3. LOGIC FLOW: Break down the PROCEDURE DIVISION into a step-by-step narrative.
        4. DEPENDENCIES: Identify all external files, programs, and copybooks.
        5. RECOMMENDATIONS: Provide 3-5 specific modernization tips.

        OUTPUT:
        You must return a JSON object matching the TechnicalAnalysisReport schema.
        """
        if hasattr(self.llm_client, "generate_json"):
            return await self.llm_client.generate_json(prompt, response_model=TechnicalAnalysisReport)
        response = self.llm_client.generate(
            "Return only JSON matching the requested technical analysis schema.",
            prompt,
        )
        return TechnicalAnalysisReport.model_validate_json(response)
