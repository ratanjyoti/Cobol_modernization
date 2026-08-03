import re

import yaml
from Agents.infrastructure.agent_base import AgentBase

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

        try:
            response = self.llm.generate(system_prompt, user_prompt)
            cleaned_yaml = str(response or "").replace("```yaml", "").replace("```", "").strip()
            if cleaned_yaml and self._is_valid_yaml(cleaned_yaml):
                return cleaned_yaml
        except Exception as exc:
            print(f"Technical YAML LLM fallback used: {exc}")

        return self._fallback_yaml(chunk_content)

    @staticmethod
    def _is_valid_yaml(content: str) -> bool:
        try:
            parsed = yaml.safe_load(content)
            return isinstance(parsed, dict) and any(key in parsed for key in ("scope", "control_flow", "interface"))
        except Exception:
            return False

    @staticmethod
    def _fallback_yaml(chunk_content: str) -> str:
        upper_content = chunk_content.upper()
        variables = sorted(set(re.findall(r"^\s*\d{2}\s+([A-Z0-9-]+)\s+PIC\b", upper_content, flags=re.MULTILINE)))
        calls = sorted(set(re.findall(r"\bCALL\s+['\"]?([A-Z0-9-]+)", upper_content)))
        sql_blocks = re.findall(r"EXEC\s+SQL(.*?)END-EXEC", upper_content, flags=re.DOTALL)
        tables = sorted(
            {
                table
                for block in sql_blocks
                for table in re.findall(r"\b(?:FROM|UPDATE|INTO)\s+([A-Z0-9_.-]+)", block)
            }
        )
        conditions = [line.strip() for line in chunk_content.splitlines() if re.search(r"\b(IF|EVALUATE)\b", line, flags=re.IGNORECASE)]

        logic_blocks = [
            {
                "name": "PROCEDURE DIVISION",
                "type": "SEQUENCE",
                "description": "Main procedural statements detected from the source chunk.",
                "calls": list(calls),
            }
        ]
        if conditions:
            logic_blocks.append(
                {
                    "name": "Conditional Logic",
                    "type": "CONDITIONAL",
                    "description": "; ".join(conditions[:5]),
                    "calls": [],
                }
            )

        return yaml.safe_dump(
            {
                "scope": {
                    "global_vars_used": [],
                    "local_vars": variables,
                },
                "control_flow": {
                    "logic_blocks": logic_blocks,
                },
                "interface": {
                    "db_tables": tables,
                    "external_calls": list(calls),
                },
                "complexity": {
                    "level": "Low" if len(conditions) <= 1 and len(calls) <= 1 else "Medium",
                    "reason": "Deterministic fallback based on detected conditions, calls, and SQL table references.",
                },
            },
            sort_keys=False,
        )
