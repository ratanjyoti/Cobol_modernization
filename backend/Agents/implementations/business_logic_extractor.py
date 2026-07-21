import json
import re

import yaml

from Agents.implementations.business_rule_schema import validate_rule_payload
from Agents.infrastructure.agent_base import AgentBase


class BusinessLogicExtractorAgent(AgentBase):
    def __init__(self, llm_client=None):
        self.llm = llm_client

    def extract_rules(self, technical_yaml, raw_code, context_packet=None, use_llm=True, source_name=None):
        system_prompt = """
You are a Senior Business Analyst. Your task is to create a professional "Functional Specification" for a legacy COBOL program.

### OUTPUT STRUCTURE REQUIRED:
For each file, you must provide:
1. BUSINESS PURPOSE: A detailed 3-5 sentence paragraph explaining exactly what this program does for the business. Who uses it? What is the end goal?
2. DETAILED FUNCTIONAL LOGIC: A comprehensive breakdown of the business process. Describe the flow of data and the decisions made. (e.g., "The system first validates the account status; if the account is 'Frozen', it rejects the transaction and logs an error...").
3. ATOMIC BUSINESS RULES: A list of specific, granular rules (IF/THEN) derived from the code.

### RULES FOR WRITING:
- NO TECHNICAL JARGON: No 'variables', 'paragraphs', 'IF statements', or 'MOVE'.
- BE EXHAUSTIVE: Do not summarize. If the code has 10 different logic paths, describe all 10.
- USE DOMAIN TERMS: Use 'Account Balance' instead of 'WS-BAL'.
- STYLE: Write it as a professional business requirement document.

### OUTPUT FORMAT:
Return ONLY a JSON object:
{
  "business_purpose": "Detailed paragraph about the program's goal...",
  "functional_logic": "A deep-dive explanation of the process flow...",
  "rules": [
    {"rule_text": "Detailed rule 1...", "technical_ref": "Line 100"},
    {"rule_text": "Detailed rule 2...", "technical_ref": "Line 120"}
  ]
}
"""

        packet = context_packet or {}
        user_prompt = "\n\n".join([
            f"[Source File]\n{source_name or 'Unknown'}",
            f"[Symbol Lock]\n{packet.get('global_types') or 'None'}",
            f"[Technical YAML]\n{technical_yaml or 'None'}",
            f"[Raw COBOL]\n{raw_code or ''}",
        ])

        response = ""
        if use_llm and self.llm is not None:
            try:
                response = self.llm.generate(system_prompt, user_prompt) or ""
            except Exception as exc:
                print(f"LLM call failed: {exc}")

        parsed = self._parse_json_rules(response)
        if parsed:
            return parsed

        return self._extract_report_locally(technical_yaml, raw_code, source_name)

    def _parse_json_rules(self, response):
        if not response:
            return None

        cleaned = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", response, flags=re.DOTALL).strip()

        try:
            data = json.loads(cleaned)
        except Exception:
            return None

        if isinstance(data, dict):
            rules = data.get("rules") or []
            return {
                "business_purpose": self._clean_paragraph(data.get("business_purpose") or ""),
                "functional_logic": self._clean_paragraph(data.get("functional_logic") or ""),
                "rules": self._normalize_rule_items(rules),
            }

        if isinstance(data, list):
            return {
                "business_purpose": "",
                "functional_logic": "",
                "rules": self._normalize_rule_items(data),
            }

        return None

    def _normalize_rule_items(self, decoded):
        normalized = []
        seen = set()
        if not isinstance(decoded, list):
            return normalized

        for item in decoded:
            if isinstance(item, str):
                rule_text = item
                technical_ref = ""
            elif isinstance(item, dict):
                rule_text = item.get("rule_text") or item.get("text") or item.get("rule") or ""
                technical_ref = item.get("technical_ref") or item.get("source") or item.get("reference") or ""
            else:
                continue

            rule_text = self._clean_paragraph(rule_text)
            key = rule_text.lower()
            if rule_text and key not in seen:
                seen.add(key)
                normalized.append({"rule_text": rule_text, "technical_ref": str(technical_ref or "")})
        return normalized

    def _extract_report_locally(self, technical_yaml, raw_code, source_name=None):
        program_name = self._program_name(raw_code, source_name)
        domain = self._infer_domain(raw_code, program_name)
        purpose = self._business_purpose(program_name, domain, raw_code)
        functional_logic = self._functional_logic(domain, raw_code)
        rules = self._normalize_rule_items(self._extract_rules_locally(technical_yaml, raw_code))

        if not rules:
            rules = [{
                "rule_text": f"The {program_name} program must preserve its {domain['process']} business behavior during modernization.",
                "technical_ref": "Derived from uploaded source file",
            }]

        return {
            "business_purpose": purpose,
            "functional_logic": functional_logic,
            "rules": rules,
        }

    def _normalize_rules(self, decoded):
        if not isinstance(decoded, list):
            return []

        normalized = []
        seen = set()
        for index, item in enumerate(decoded, start=1):
            if isinstance(item, str):
                rule_text = item
                technical_ref = ""
            elif isinstance(item, dict):
                rule_text = item.get("rule_text") or item.get("text") or item.get("rule") or ""
                technical_ref = item.get("technical_ref") or item.get("source") or item.get("reference") or ""
            else:
                continue

            rule_text = self._as_user_story(rule_text)
            key = rule_text.lower()
            if rule_text and key not in seen:
                seen.add(key)
                normalized.append({
                    "rule_id": f"BR-{index:03d}",
                    "rule_text": rule_text,
                    "technical_ref": str(technical_ref),
                })

        return normalized

    def _extract_rules_locally(self, technical_yaml, raw_code):
        rules = []
        rules.extend(self._rules_from_yaml(technical_yaml))
        rules.extend(self._rules_from_code(raw_code))

        unique = []
        seen = set()
        for index, rule in enumerate(rules, start=1):
            text = self._as_user_story(rule.get("rule_text", ""))
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                unique.append({
                    "rule_id": f"BR-{index:03d}",
                    "rule_text": text,
                    "technical_ref": rule.get("technical_ref", ""),
                })

        return unique[:8]

    def _rules_from_yaml(self, technical_yaml):
        try:
            data = yaml.safe_load(technical_yaml) or {}
        except yaml.YAMLError:
            return []

        if not isinstance(data, dict):
            return []

        blocks = (((data.get("control_flow") or {}).get("logic_blocks")) or [])
        rules = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            description = (block.get("description") or "").strip()
            if not description:
                continue
            action = self._business_phrase(description)
            rules.append({
                "rule_text": f"As an operations user, I want to {action} so that the migrated system preserves the intended business behavior.",
                "technical_ref": f"control_flow.logic_blocks.{block.get('name', 'unnamed')}",
            })
        return rules

    def _rules_from_code(self, raw_code):
        rules = []
        for line_no, raw_line in enumerate((raw_code or "").splitlines(), start=1):
            line = self._strip_sequence_number(raw_line.strip())
            upper = line.upper()
            if not line or upper.startswith(("*", "*>")):
                continue

            if upper.startswith("IF ") or " IF " in upper or upper.startswith("EVALUATE "):
                condition = self._condition_to_business_text(line)
                rules.append({
                    "rule_text": f"As an operations user, I want to apply the appropriate outcome when {condition} so that business policy is enforced consistently.",
                    "technical_ref": f"COBOL line {line_no}: {line}",
                })
            elif upper.startswith("COMPUTE "):
                target = self._business_phrase(line.split()[1] if len(line.split()) > 1 else "result")
                rules.append({
                    "rule_text": f"As an operations user, I want to calculate {target} so that downstream decisions use the correct value.",
                    "technical_ref": f"COBOL line {line_no}: {line}",
                })
            elif upper.startswith("CALL ") or " CALL " in upper:
                service = self._business_phrase(re.sub(r".*\bCALL\b", "", line, flags=re.IGNORECASE).strip(" '.\""))
                rules.append({
                    "rule_text": f"As an operations user, I want to request {service} so that the required business service is completed.",
                    "technical_ref": f"COBOL line {line_no}: {line}",
                })
            elif "EXEC SQL" in upper:
                rules.append({
                    "rule_text": "As an operations user, I want to access the required business data so that the transaction can be completed with current records.",
                    "technical_ref": f"COBOL line {line_no}: {line}",
                })
        return rules

    def _program_name(self, raw_code, source_name=None):
        match = re.search(r"\bPROGRAM-ID\.?\s+([A-Z0-9_-]+)", raw_code or "", re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()
        return source_name or "uploaded source file"

    def _infer_domain(self, raw_code, program_name):
        text = f"{program_name}\n{raw_code or ''}".lower()
        program_lower = program_name.lower()
        if program_lower.endswith(".cpy") or "copybook" in text or "01 " in text:
            if any(word in text for word in ["customer", "cust", "client"]):
                return {
                    "entity": "customer",
                    "process": "customer data definition",
                    "action": "storing customer information including identifiers, names, addresses, balances, and statuses",
                    "outcome": "customer programs share a consistent structure for reading, displaying, and updating customer details",
                }
            return {
                "entity": "business record",
                "process": "shared data definition",
                "action": "storing the shared business data structure used by related programs",
                "outcome": "all related programs interpret the same business fields consistently",
            }
        if any(word in text for word in ["folha", "payroll", "salary", "salario", "employee", "empregado"]):
            return {
                "entity": "employee",
                "process": "payroll management",
                "action": "managing employee data, calculating salaries, and supporting payroll maintenance operations",
                "outcome": "payroll records remain accurate and ready for business processing",
            }
        if any(word in text for word in ["customer", "cust", "client"]):
            program_lower = program_name.lower()
            if "display" in program_lower or ("display" in text and "inquiry" not in program_lower and "read" not in text):
                action = "displaying customer information including identifiers, names, addresses, balances, and statuses"
            elif "inquiry" in program_lower or any(word in text for word in ["read", "search", "id"]):
                action = "retrieving customer information based on a provided customer identifier"
            else:
                action = "maintaining and presenting customer information for business users"
            return {
                "entity": "customer",
                "process": "customer information handling",
                "action": action,
                "outcome": "staff can access the customer details needed for service and account decisions",
            }
        if any(word in text for word in ["account", "acct", "balance"]):
            return {
                "entity": "account",
                "process": "account processing",
                "action": "validating account information, evaluating balances, and applying account-related business decisions",
                "outcome": "account activity follows the organization's operational policies",
            }
        if any(word in text for word in ["order", "invoice", "payment"]):
            return {
                "entity": "transaction",
                "process": "transaction processing",
                "action": "processing business transactions, calculating required values, and producing the expected operational outcome",
                "outcome": "transactions are completed consistently and recorded for downstream use",
            }
        return {
            "entity": "business record",
            "process": "legacy business processing",
            "action": "validating input data, executing the required business decisions, and producing the expected output",
            "outcome": "the migrated system preserves the behavior of the original legacy process",
        }

    def _business_purpose(self, program_name, domain, raw_code):
        operations = []
        upper = raw_code.upper() if raw_code else ""
        if "ACCEPT" in upper:
            operations.append("captures user or batch input")
        if "READ" in upper or "SELECT" in upper or "EXEC SQL" in upper:
            operations.append(f"retrieves {domain['entity']} data")
        if "DISPLAY" in upper or "WRITE" in upper:
            operations.append("presents business information to users or reports")
        if "COMPUTE" in upper or "ADD " in upper or "SUBTRACT" in upper or "MULTIPLY" in upper:
            operations.append("calculates business values")
        if "DELETE" in upper or "REWRITE" in upper or "WRITE" in upper:
            operations.append("updates stored business records")

        operation_text = ", ".join(dict.fromkeys(operations)) or "coordinates the required business steps"
        return (
            f"The {program_name} program serves the business function of {domain['action']}. "
            f"It {operation_text} as part of the {domain['process']} workflow. "
            f"The end goal is to ensure that {domain['outcome']}."
        )

    def _functional_logic(self, domain, raw_code):
        steps = []
        upper = raw_code.upper() if raw_code else ""
        if "ACCEPT" in upper:
            steps.append(f"The process begins by accepting the required {domain['entity']} input from the user or calling process.")
        if "READ" in upper or "SELECT" in upper or "EXEC SQL" in upper:
            steps.append(f"The program then retrieves the matching {domain['entity']} details from the available file or data source.")
        if "IF" in upper or "EVALUATE" in upper:
            steps.append("Business conditions are evaluated to decide which action, message, calculation, or exception path should be applied.")
        if "COMPUTE" in upper or "ADD " in upper or "SUBTRACT" in upper or "MULTIPLY" in upper:
            steps.append("When numeric values are present, the program calculates the required business totals or derived amounts before output is produced.")
        if "DISPLAY" in upper or "WRITE" in upper:
            steps.append("The resulting information is formatted and presented or written so the business user can act on the outcome.")
        if "DELETE" in upper or "REWRITE" in upper:
            steps.append("Where maintenance actions are requested, the existing business record is changed or removed according to the selected operation.")
        if not steps:
            steps.append(f"The program executes the required {domain['process']} steps from input through final output while preserving legacy behavior.")
        return " ".join(steps)

    @staticmethod
    def _clean_paragraph(text):
        return re.sub(r"\s+", " ", str(text or "").strip())
    @staticmethod
    def _strip_sequence_number(line):
        return re.sub(r"^\d{5,6}\s+", "", str(line or "").strip())
    def _condition_to_business_text(self, line):
        line = self._strip_sequence_number(line)
        condition = re.sub(r"^\s*IF\s+", "", line, flags=re.IGNORECASE)
        condition = re.sub(r"^\s*EVALUATE\s+", "", condition, flags=re.IGNORECASE)
        # Remove the action part to keep only the condition
        condition = re.split(r"\bTHEN\b|\bPERFORM\b|\bMOVE\b|\bCOMPUTE\b|\.", condition, maxsplit=1, flags=re.IGNORECASE)[0]
        
        # Make it read like a business requirement
        condition = condition.replace("<=", " is less than or equal to ")
        condition = condition.replace(">=", " is greater than or equal to ")
        condition = condition.replace("=", " is equal to ")
        condition = condition.replace("<", " is less than ")
        condition = condition.replace(">", " is greater than ")
        
        return f"whenever the condition '{self._business_phrase(condition)}' is met"

    def _as_user_story(self, text):
        text = re.sub(r"\s+", " ", str(text or "").strip())
        if not text: return ""
        
        # If it's already a detailed rule, don't force it into a short "As a..." format
        if len(text) > 100 or "whenever" in text.lower():
            return f"Business Rule: {text}"
            
        return f"As a business user, I want to {text[0].lower() + text[1:]} to ensure operational consistency."

    def _business_phrase(self, text):
        phrase = str(text or "").replace("-", " ").replace("_", " ")
        replacements = {
            "acct": "account",
            "acc": "account",
            "bal": "balance",
            "cust": "customer",
            "amt": "amount",
            "txn": "transaction",
            "calc": "calculate",
            "prem": "premium",
            "elig": "eligibility",
            "stat": "status",
            "id": "identifier",
        }
        words = []
        for word in re.findall(r"[A-Za-z0-9']+|\S", phrase.lower()):
            words.append(replacements.get(word, word))
        cleaned = re.sub(r"\s+", " ", " ".join(words)).strip()
        cleaned = cleaned.replace(" and applies ", " and apply ")
        leading_verbs = {
            "checks ": "check ",
            "applies ": "apply ",
            "calculates ": "calculate ",
            "validates ": "validate ",
            "determines ": "determine ",
            "updates ": "update ",
        }
        for prefix, replacement in leading_verbs.items():
            if cleaned.startswith(prefix):
                return replacement + cleaned[len(prefix):]
        return cleaned









