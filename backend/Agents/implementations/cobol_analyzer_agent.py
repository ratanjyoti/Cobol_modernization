import yaml
from Agents.infrastructure.agent_base import AgentBase # Assuming you have a base agent class

class CobolAnalyzerAgent(AgentBase):
    def __init__(self, llm_client):
        self.llm = llm_client

    def generate_technical_yaml(self, chunk_content, global_types, signatures, context_summary):
        # THE SYSTEM PROMPT: This is the most important part
        system_prompt = f"""
        You are a Senior Mainframe Architect. Your task is to perform a Technical Analysis of a COBOL chunk.
        
        INPUTS PROVIDED:
        1. Global Type Map: {global_types}
        2. Known Signatures: {signatures}
        3. Previous Context: {context_summary}

        Your goal is to produce a Technical YAML blueprint. 
        DO NOT translate to Java. DO NOT explain the code. 
        ONLY output valid YAML.

        Required YAML Structure:
        scope:
          global_vars_used: [list of variables from the global map]
          local_vars: [any new variables found]
        control_flow:
          logic_blocks:
            - name: "Paragraph Name"
              type: "LOOP/CONDITIONAL/SEQUENCE"
              description: "Short technical description of the logic"
              calls: [list of other paragraphs called]
        interface:
          db_tables: [list of tables accessed via EXEC SQL]
          external_calls: [list of external programs called]
        complexity:
          level: "Low/Medium/High"
          reason: "Why this score?"
        """

        user_prompt = f"Analyze the following COBOL chunk and produce the Technical YAML:\n\n{chunk_content}"

        # Call the LLM
        response = self.llm.generate(system_prompt, user_prompt)
        
        # Clean the response (remove ```yaml ... ``` markers)
        cleaned_yaml = response.replace("```yaml", "").replace("```", "").strip()
        
        return cleaned_yaml
