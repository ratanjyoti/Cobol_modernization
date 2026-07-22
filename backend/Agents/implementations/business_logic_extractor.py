import json
import re
from typing import Any

import yaml

from Agents.infrastructure.agent_base import AgentBase

try:
    from Agents.implementations.business_rule_schema import validate_rule_payload
except Exception:
    validate_rule_payload = None


class BusinessLogicExtractorAgent(AgentBase):
    """
    Extracts business purpose, functional logic, and atomic business rules
    from COBOL chunks using LLM first, then deterministic local fallback.
    """

    def __init__(self, llm_client=None):
        self.llm = llm_client

    def extract_rules(
        self,
        technical_yaml: str,
        raw_code: str,
        context_packet: dict | None = None,
        use_llm: bool = True,
        source_name: str | None = None,
    ) -> dict:
        system_prompt = """
You are a Senior Business Analyst and Mainframe Modernization Expert.

Your task is to extract business logic from legacy COBOL code and write it as a professional Functional Specification.

IMPORTANT WRITING RULES:
- Write in business language, not COBOL syntax.
- Do not say "IF statement", "MOVE", "PERFORM", "paragraph", or "variable" unless required in technical_ref.
- Convert technical names into business terms where possible.
- Be specific and evidence-based. Do not invent business rules.
- Every rule must be traceable to a technical_ref.
- If the code contains validation, calculation, status change, file read/write, SQL, or external call behavior, extract it.

EXTRACT:
1. business_purpose:
   A 3-5 sentence explanation of what this program/chunk does for the business.

2. functional_logic:
   A detailed business process narrative explaining:
   - inputs received
   - validations performed
   - decisions made
   - calculations performed
   - records read/written/updated/deleted
   - outputs produced
   - exception paths

3. rules:
   Atomic rules. Each rule must describe exactly one business rule, validation, calculation, data access rule, or state transition.

OUTPUT FORMAT:
Return ONLY valid JSON. No markdown. No explanation outside JSON.

Schema:
{
  "business_purpose": "string",
  "functional_logic": "string",
  "rules": [
    {
      "rule_text": "string",
      "rule_type": "BUSINESS_DECISION | VALIDATION | CALCULATION | DATA_ACCESS | STATE_TRANSITION | EXTERNAL_SERVICE | WORKFLOW",
      "technical_ref": "string",
      "confidence": "HIGH | MEDIUM | LOW"
    }
  ]
}
"""

        packet = context_packet or {}

        user_prompt = "\n\n".join([
            f"[Source File]\n{source_name or 'Unknown'}",
            f"[Global Type / Symbol Context]\n{packet.get('global_types') or 'None'}",
            f"[Global Signatures]\n{packet.get('global_signatures') or 'None'}",
            f"[Prior Chunk Summary]\n{packet.get('summary_history') or 'None'}",
            f"[Technical YAML Evidence]\n{technical_yaml or 'None'}",
            f"[Raw COBOL Code]\n{raw_code or ''}",
        ])

        response = ""

        if use_llm and self.llm is not None:
            try:
                response = self._call_llm(system_prompt, user_prompt)
            except Exception as exc:
                print(f"LLM rule extraction failed, using local fallback: {exc}")

        parsed = self._parse_json_response(response)

        if parsed and parsed.get("rules"):
            parsed = self._validate_or_normalize_payload(parsed)
            return parsed

        return self._extract_report_locally(
            technical_yaml=technical_yaml,
            raw_code=raw_code,
            source_name=source_name,
        )

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Supports both clients:
        - generate(system_prompt, user_prompt)
        - generate(prompt)
        """
        if hasattr(self.llm, "generate"):
            try:
                return self.llm.generate(system_prompt, user_prompt) or ""
            except TypeError:
                return self.llm.generate(system_prompt + "\n\n" + user_prompt) or ""

        raise RuntimeError("LLM client does not expose generate()")

    def _parse_json_response(self, response: str) -> dict | None:
        if not response:
            return None

        cleaned = self._strip_code_fence(response)

        # Try direct JSON first.
        try:
            data = json.loads(cleaned)
            return self._normalize_payload(data)
        except Exception:
            pass

        # Try extracting first JSON object from messy response.
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return self._normalize_payload(data)
            except Exception:
                return None

        return None

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        text = str(text or "").strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _normalize_payload(self, data: Any) -> dict | None:
        if isinstance(data, list):
            return {
                "business_purpose": "",
                "functional_logic": "",
                "rules": self._normalize_rule_items(data),
            }

        if not isinstance(data, dict):
            return None

        return {
            "business_purpose": self._clean_text(data.get("business_purpose") or data.get("purpose") or ""),
            "functional_logic": self._clean_text(data.get("functional_logic") or data.get("logic") or ""),
            "rules": self._normalize_rule_items(data.get("rules") or data.get("business_rules") or []),
        }

    def _normalize_rule_items(self, decoded: Any) -> list[dict]:
        if not isinstance(decoded, list):
            return []

        normalized = []
        seen = set()

        for item in decoded:
            if isinstance(item, str):
                rule_text = item
                rule_type = "BUSINESS_DECISION"
                technical_ref = ""
                confidence = "MEDIUM"
            elif isinstance(item, dict):
                rule_text = (
                    item.get("rule_text")
                    or item.get("text")
                    or item.get("rule")
                    or item.get("description")
                    or ""
                )
                rule_type = item.get("rule_type") or item.get("type") or "BUSINESS_DECISION"
                technical_ref = item.get("technical_ref") or item.get("source") or item.get("reference") or ""
                confidence = item.get("confidence") or "MEDIUM"
            else:
                continue

            rule_text = self._clean_text(rule_text)
            technical_ref = self._clean_text(technical_ref)

            if not rule_text:
                continue

            rule_type = str(rule_type).upper().strip()
            allowed_types = {
                "BUSINESS_DECISION",
                "VALIDATION",
                "CALCULATION",
                "DATA_ACCESS",
                "STATE_TRANSITION",
                "EXTERNAL_SERVICE",
                "WORKFLOW",
            }
            if rule_type not in allowed_types:
                rule_type = "BUSINESS_DECISION"

            confidence = str(confidence).upper().strip()
            if confidence not in {"HIGH", "MEDIUM", "LOW"}:
                confidence = "MEDIUM"

            key = re.sub(r"\s+", " ", rule_text.lower())

            if key not in seen:
                seen.add(key)
                normalized.append({
                    "rule_text": rule_text,
                    "rule_type": rule_type,
                    "technical_ref": technical_ref,
                    "confidence": confidence,
                })

        return normalized

    def _validate_or_normalize_payload(self, payload: dict) -> dict:
        """
        Uses schema validator if available. If validator fails, keep normalized payload.
        """
        if validate_rule_payload is None:
            return payload

        try:
            return validate_rule_payload(payload)
        except Exception:
            return payload

    def _extract_report_locally(
        self,
        technical_yaml: str,
        raw_code: str,
        source_name: str | None = None,
    ) -> dict:
        program_name = self._program_name(raw_code, source_name)
        domain = self._infer_domain(raw_code, program_name)

        purpose = self._business_purpose(program_name, domain, raw_code)
        functional_logic = self._functional_logic(domain, raw_code)

        rules = []
        rules.extend(self._rules_from_yaml(technical_yaml))
        rules.extend(self._rules_from_code(raw_code, domain))

        unique_rules = []
        seen = set()

        for rule in rules:
            rule_text = self._clean_text(rule.get("rule_text", ""))
            if not rule_text:
                continue

            key = rule_text.lower()
            if key in seen:
                continue

            seen.add(key)
            unique_rules.append({
                "rule_text": rule_text,
                "rule_type": rule.get("rule_type", "BUSINESS_DECISION"),
                "technical_ref": rule.get("technical_ref", ""),
                "confidence": rule.get("confidence", "MEDIUM"),
            })

        if not unique_rules:
            unique_rules.append({
                "rule_text": (
                    f"The {program_name} component must preserve its "
                    f"{domain['process']} behavior during modernization."
                ),
                "rule_type": "WORKFLOW",
                "technical_ref": "Derived from uploaded source file",
                "confidence": "LOW",
            })

        return {
            "business_purpose": purpose,
            "functional_logic": functional_logic,
            "rules": unique_rules[:20],
        }

    def _rules_from_yaml(self, technical_yaml: str) -> list[dict]:
        if not technical_yaml:
            return []

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

            description = self._clean_text(block.get("description") or "")
            name = block.get("name", "unnamed")

            if not description:
                continue

            rule_text, rule_type = self._line_to_business_rule(description)

            if rule_text:
                rules.append({
                    "rule_text": rule_text,
                    "rule_type": rule_type,
                    "technical_ref": f"control_flow.logic_blocks.{name}",
                    "confidence": "MEDIUM",
                })

        return rules

    def _rules_from_code(self, raw_code: str, domain: dict) -> list[dict]:
        rules = []

        for line_no, raw_line in enumerate((raw_code or "").splitlines(), start=1):
            line = self._strip_sequence_number(raw_line).strip()
            upper = line.upper()

            if not line:
                continue

            if upper.startswith(("*", "*>")):
                continue

            rule_text, rule_type = self._line_to_business_rule(line, domain)

            if rule_text:
                rules.append({
                    "rule_text": rule_text,
                    "rule_type": rule_type,
                    "technical_ref": f"COBOL line {line_no}: {line[:220]}",
                    "confidence": "MEDIUM",
                })

        return rules

    def _line_to_business_rule(self, line: str, domain: dict | None = None) -> tuple[str, str]:
        domain = domain or {
            "entity": "business record",
            "process": "legacy business processing",
        }

        stripped = self._strip_sequence_number(line).strip()
        upper = stripped.upper()

        if upper.startswith("IF ") or " IF " in upper or upper.startswith("EVALUATE "):
            condition = self._condition_to_business_text(stripped)
            return (
                f"When {condition}, the system must apply the corresponding business outcome consistently.",
                "BUSINESS_DECISION",
            )

        if upper.startswith("COMPUTE "):
            target = self._extract_compute_target(stripped)
            return (
                f"The system must calculate {target} using the defined legacy formula before the result is used downstream.",
                "CALCULATION",
            )

        if upper.startswith("ADD "):
            return (
                "The system must add the specified business amount into the target total to keep accumulated values accurate.",
                "CALCULATION",
            )

        if upper.startswith("SUBTRACT "):
            return (
                "The system must subtract the specified business amount from the target value to keep the resulting balance accurate.",
                "CALCULATION",
            )

        if upper.startswith("MULTIPLY "):
            return (
                "The system must multiply the specified business values according to the legacy calculation rule.",
                "CALCULATION",
            )

        if upper.startswith("DIVIDE "):
            return (
                "The system must divide the specified business values according to the legacy calculation rule while preserving decimal precision.",
                "CALCULATION",
            )

        if upper.startswith("READ ") or " READ " in upper:
            return (
                f"The system must retrieve the required {domain['entity']} record before continuing the business process.",
                "DATA_ACCESS",
            )

        if upper.startswith("WRITE ") or " WRITE " in upper:
            return (
                f"The system must create or output the required {domain['entity']} record as part of the business process.",
                "STATE_TRANSITION",
            )

        if upper.startswith("REWRITE ") or " REWRITE " in upper:
            return (
                f"The system must update the existing {domain['entity']} record while preserving the legacy maintenance behavior.",
                "STATE_TRANSITION",
            )

        if upper.startswith("DELETE ") or " DELETE " in upper:
            return (
                f"The system must remove the selected {domain['entity']} record only when the legacy deletion condition is satisfied.",
                "STATE_TRANSITION",
            )

        if "EXEC SQL" in upper:
            sql_meaning = self._sql_to_business_text(stripped)
            return (sql_meaning, "DATA_ACCESS")

        if upper.startswith("CALL ") or " CALL " in upper:
            service = self._extract_called_service(stripped)
            return (
                f"The system must invoke {service} to complete the required supporting business operation.",
                "EXTERNAL_SERVICE",
            )

        if upper.startswith("PERFORM ") or " PERFORM " in upper:
            target = self._extract_perform_target(stripped)
            if self._is_business_perform_target(target):
                phrase = self._business_phrase(target)
                return (
                    f"The system must perform {phrase} as part of the business workflow.",
                    "WORKFLOW",
                )

        if upper.startswith("ACCEPT ") or " ACCEPT " in upper:
            return (
                f"The system must capture the required {domain['entity']} input before processing can continue.",
                "VALIDATION",
            )

        return ("", "")

    def _program_name(self, raw_code: str, source_name: str | None = None) -> str:
        match = re.search(r"\bPROGRAM-ID\.?\s+([A-Z0-9_-]+)", raw_code or "", re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()

        return source_name or "uploaded source file"

    def _infer_domain(self, raw_code: str, program_name: str) -> dict:
        text = f"{program_name}\n{raw_code or ''}".lower()
        program_lower = program_name.lower()

        if program_lower.endswith(".cpy") or "copybook" in text or re.search(r"^\s*01\s+", raw_code or "", re.MULTILINE):
            if any(word in text for word in ["customer", "cust", "client"]):
                return {
                    "entity": "customer",
                    "process": "customer data definition",
                    "action": "storing customer identifiers, names, addresses, balances, and statuses",
                    "outcome": "all customer-facing programs use a consistent customer record structure",
                }

            return {
                "entity": "business record",
                "process": "shared data definition",
                "action": "defining the shared business data structure used by related programs",
                "outcome": "related programs interpret the same business fields consistently",
            }

        if any(word in text for word in ["folha", "payroll", "salary", "salario", "employee", "empregado", "colaborador"]):
            return {
                "entity": "employee",
                "process": "payroll management",
                "action": "managing employee payroll data, salary calculations, absences, deductions, and maintenance operations",
                "outcome": "payroll records remain accurate and ready for business processing",
            }

        if any(word in text for word in ["customer", "cust", "client"]):
            if "display" in program_lower:
                action = "displaying customer information including identifiers, names, addresses, balances, and statuses"
            elif "inquiry" in program_lower or any(word in text for word in ["read", "search", "id"]):
                action = "retrieving customer information based on a supplied customer identifier"
            else:
                action = "maintaining and presenting customer information for business users"

            return {
                "entity": "customer",
                "process": "customer information handling",
                "action": action,
                "outcome": "staff can access customer details needed for service and account decisions",
            }

        if any(word in text for word in ["account", "acct", "balance"]):
            return {
                "entity": "account",
                "process": "account processing",
                "action": "validating account information, evaluating balances, and applying account-related business decisions",
                "outcome": "account activity follows operational policies",
            }

        if any(word in text for word in ["order", "invoice", "payment", "transaction", "txn"]):
            return {
                "entity": "transaction",
                "process": "transaction processing",
                "action": "processing business transactions, calculating required values, and producing operational outcomes",
                "outcome": "transactions are completed consistently and recorded for downstream use",
            }

        return {
            "entity": "business record",
            "process": "legacy business processing",
            "action": "validating input data, executing business decisions, and producing the expected output",
            "outcome": "the modernized system preserves the behavior of the original legacy process",
        }

    def _business_purpose(self, program_name: str, domain: dict, raw_code: str) -> str:
        operations = []
        upper = raw_code.upper() if raw_code else ""

        if "ACCEPT" in upper:
            operations.append("captures user or batch input")
        if any(k in upper for k in ["READ", "SELECT", "EXEC SQL", "START"]):
            operations.append(f"retrieves {domain['entity']} data")
        if any(k in upper for k in ["DISPLAY", "WRITE"]):
            operations.append("presents or outputs business information")
        if any(k in upper for k in ["COMPUTE", "ADD ", "SUBTRACT", "MULTIPLY", "DIVIDE"]):
            operations.append("calculates business values")
        if any(k in upper for k in ["DELETE", "REWRITE", "WRITE"]):
            operations.append("maintains stored business records")
        if "CALL" in upper:
            operations.append("coordinates with supporting business services")

        operation_text = ", ".join(dict.fromkeys(operations)) or "coordinates required business steps"

        return (
            f"The {program_name} component serves the business function of {domain['action']}. "
            f"It {operation_text} as part of the {domain['process']} workflow. "
            f"The end goal is to ensure that {domain['outcome']}."
        )

    def _functional_logic(self, domain: dict, raw_code: str) -> str:
        steps = []
        upper = raw_code.upper() if raw_code else ""

        if "ACCEPT" in upper:
            steps.append(f"The process begins by capturing the required {domain['entity']} input.")
        if any(k in upper for k in ["READ", "SELECT", "EXEC SQL", "START"]):
            steps.append(f"The system retrieves the matching {domain['entity']} details from the relevant file or data source.")
        if any(k in upper for k in ["IF", "EVALUATE"]):
            steps.append("Business conditions are evaluated to decide the correct action, message, calculation, or exception path.")
        if any(k in upper for k in ["COMPUTE", "ADD ", "SUBTRACT", "MULTIPLY", "DIVIDE"]):
            steps.append("The system calculates required totals, balances, deductions, or derived values before output is produced.")
        if any(k in upper for k in ["DISPLAY", "WRITE"]):
            steps.append("The final business information is displayed, written, or passed to the next process.")
        if any(k in upper for k in ["DELETE", "REWRITE"]):
            steps.append("Where maintenance is requested, the selected business record is updated or removed according to the legacy rule.")
        if "CALL" in upper:
            steps.append("Supporting programs or services are invoked when specialized formatting, lookup, or downstream processing is required.")

        if not steps:
            steps.append(f"The component executes the required {domain['process']} steps while preserving legacy behavior.")

        return " ".join(steps)

    def _condition_to_business_text(self, line: str) -> str:
        condition = self._strip_sequence_number(line)
        condition = re.sub(r"^\s*IF\s+", "", condition, flags=re.IGNORECASE)
        condition = re.sub(r"^\s*EVALUATE\s+", "", condition, flags=re.IGNORECASE)

        condition = re.split(
            r"\bTHEN\b|\bPERFORM\b|\bMOVE\b|\bCOMPUTE\b|\bDISPLAY\b|\bCALL\b|\.",
            condition,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        condition = condition.replace("<=", " is less than or equal to ")
        condition = condition.replace(">=", " is greater than or equal to ")
        condition = condition.replace(" NOT = ", " is not equal to ")
        condition = condition.replace("=", " is equal to ")
        condition = condition.replace("<", " is less than ")
        condition = condition.replace(">", " is greater than ")

        return self._business_phrase(condition)

    def _sql_to_business_text(self, line: str) -> str:
        upper = line.upper()

        if "SELECT" in upper:
            return "The system must retrieve the required business data from the database before completing the transaction."
        if "INSERT" in upper:
            return "The system must create a new database record when the business process produces new persistent information."
        if "UPDATE" in upper:
            return "The system must update existing database information when the business process changes a record."
        if "DELETE" in upper:
            return "The system must remove database information only when the legacy business process permits deletion."

        return "The system must access database information required to complete the business transaction."

    def _extract_compute_target(self, line: str) -> str:
        match = re.search(r"\bCOMPUTE\s+([A-Z0-9_-]+)", line, flags=re.IGNORECASE)
        if match:
            return self._business_phrase(match.group(1))

        return "the required business value"

    def _extract_called_service(self, line: str) -> str:
        service = re.sub(r".*\bCALL\b", "", line, flags=re.IGNORECASE)
        service = service.strip(" .'\"")
        return self._business_phrase(service or "the supporting business service")

    def _extract_perform_target(self, line: str) -> str:
        match = re.search(r"\bPERFORM\s+([A-Z0-9_-]+)", line, flags=re.IGNORECASE)
        if match:
            return match.group(1)

        return ""

    @staticmethod
    def _is_business_perform_target(target: str) -> bool:
        if not target:
            return False

        business_words = [
            "CALC",
            "VALID",
            "CHECK",
            "UPDATE",
            "DELETE",
            "SEARCH",
            "FIND",
            "PAY",
            "TAX",
            "BAL",
            "BALANCE",
            "CUSTOMER",
            "CUST",
            "EMP",
            "SAL",
            "SALARY",
            "INVOICE",
            "ORDER",
            "WRITE",
            "READ",
            "DISPLAY",
            "FORMAT",
        ]

        upper = target.upper()
        return any(word in upper for word in business_words)

    @staticmethod
    def _strip_sequence_number(line: str) -> str:
        return re.sub(r"^\d{5,6}\s+", "", str(line or "").strip())

    @staticmethod
    def _clean_text(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip())

    def _business_phrase(self, text: str) -> str:
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
            "num": "number",
            "qty": "quantity",
            "sal": "salary",
            "he": "overtime hours",
            "irrf": "income tax withholding",
            "inss": "social security contribution",
            "vt": "transportation benefit",
        }

        words = []
        for word in re.findall(r"[A-Za-z0-9']+|\S", phrase.lower()):
            words.append(replacements.get(word, word))

        cleaned = re.sub(r"\s+", " ", " ".join(words)).strip()
        return cleaned