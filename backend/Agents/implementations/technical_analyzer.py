import json
import re
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

    async def analyze_skeleton(self, content: str, global_types: str):
        prompt = f"""
You are a Mainframe Technical Architect. Analyze the following COBOL code.

CONTEXT:
Global Type Mappings:
{global_types}

CODE:
{content}

TASK:
Create a Technical YAML map of this chunk. Identify:
1. Logic Flow: paragraph-to-paragraph or section-to-section execution.
2. Data Mutations: variables updated and the condition/reason for update.
3. External Hits: SQL tables, file operations, CICS calls, or program calls.
4. Business Logic Candidates: IF, EVALUATE, COMPUTE, ADD, SUBTRACT, MULTIPLY, DIVIDE, READ, WRITE, REWRITE, DELETE, CALL, EXEC SQL.

OUTPUT FORMAT:
Return ONLY valid YAML.
Do not include markdown fences.
Do not include conversational text.
"""

        response = await self.llm_client.generate(prompt)
        return self._strip_code_fence(response)

    async def analyze_deep(self, content: str, lang: str):
        prompt = f"""
You are a Mainframe Modernization Architect.

Produce a professional reverse engineering report for this {lang} code.

CODE:
{content}

Return ONLY a valid JSON object with this exact structure:

{{
  "business_purpose": "Detailed 3-5 sentence paragraph describing the program goal.",
  "data_structures": [
    {{
      "name": "record or structure name",
      "description": "business meaning of this structure",
      "fields": [
        {{
          "name": "field name",
          "pic_clause": "PIC clause if available",
          "business_meaning": "what this field means in the business",
          "data_type": "numeric/alphanumeric/packed decimal/date/status/etc"
        }}
      ]
    }}
  ],
  "processing_logic_flow": [
    {{
      "step_number": 1,
      "description": "business/technical step explanation",
      "technical_trigger": "paragraph, statement, or operation that causes this step"
    }}
  ],
  "external_dependencies": [
    {{
      "name": "dependency name",
      "type": "copybook/file/program/sql_table/cics_transaction/unknown",
      "description": "why this dependency is used"
    }}
  ],
  "complexity": {{
    "rating": "Low/Medium/High",
    "reasons": [
      "reason 1",
      "reason 2"
    ]
  }},
  "modernization_recommendations": [
    "specific migration recommendation 1",
    "specific migration recommendation 2",
    "specific migration recommendation 3"
  ]
}}

Rules:
- Return JSON only.
- No markdown.
- No comments.
- Do not invent dependencies that are not supported by the code.
- Preserve monetary precision and PIC information when visible.
"""

        response = await self.llm_client.generate(prompt)
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