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
        Global Type Mappings: {global_types}
        
        CODE:
        {content}
        
        TASK:
        Create a Technical YAML map of this chunk. Identify:
        1. Logic Flow: (e.g., Paragraph A -> calls Paragraph B)
        2. Data Mutations: (e.g., Variable X is updated based on Condition Y)
        3. External Hits: (SQL Tables or CICS calls)
        
        OUTPUT FORMAT:
        Return ONLY a valid YAML block. Do not include conversational text.
        """
        # Use the generate method from your agent_base
        response = await self.llm_client.generate(prompt)
        return response

    async def analyze_deep(self, content: str, lang: str):
        prompt = f"""
        You are a Mainframe Modernization Architect. Produce a professional Reverse Engineering Report for this {lang} code.
        
        CODE:
        {content}
        
        You MUST produce the following sections exactly:
        1. BUSINESS PURPOSE: A detailed 3-5 sentence paragraph describing the program's goal.
        2. DATA STRUCTURES: A detailed list of every record layout, including field names, PIC clauses, and business descriptions.
        3. PROCESSING LOGIC FLOW: A numbered step-by-step narrative of the entire program execution.
        4. EXTERNAL DEPENDENCIES: List all files, copybooks, and external programs called.
        5. COMPLEXITY & MODERNIZATION: Provide a Complexity Rating (Low/Medium/High) and 3 specific tips for migrating this to Java/Quarkus.
        
        OUTPUT: Return ONLY a JSON object.
        """
        response = await self.llm_client.generate(prompt)
        return json.loads(response) # Ensure this maps to your TechnicalAnalysisReport model
