import json
import re

import yaml

from Agents.implementations.business_rule_schema import validate_rule_payload
from Agents.infrastructure.agent_base import AgentBase


class BusinessLogicExtractorAgent(AgentBase):
    def __init__(self, llm_client=None):
        self.llm = llm_client

    def extract_rules(self, technical_yaml, raw_code, context_packet=None, use_llm=True):
        system_prompt = """
You are a Senior Business Analyst specializing in legacy modernization.
Perform the semantic leap from HOW the COBOL works to WHY the business needs it.

Thought process to follow:
1. Identify Trigger: what business event starts this behavior?
2. Trace Path: what business path follows from the technical flow?
3. Identify Actor: who benefits or performs this work?
4. Synthesize Story: write a user story.

Rules:
- Do not mention variables, paragraphs, loops, IF statements, or implementation mechanics.
- Write business intent only.
- Every rule must be a user story: "As a [Role], I want to [Action] so that [Value]."
- Return only valid JSON in this shape:
{"rules":[{"rule_text":"...","technical_ref":"..."}]}
"""
        packet = context_packet or {}
        user_prompt = "\n\n".join([
            "[Symbol Lock - Type Mappings]\n" + (packet.get("global_types") or "None"),
            "[Symbol Lock - Paragraph Signatures]\n" + (packet.get("global_signatures") or "None"),
            "[Technical YAML]\n" + (technical_yaml or "None"),
            "[Raw COBOL]\n" + (raw_code or ""),
        ])

        response = ""
        if use_llm and self.llm is not None and hasattr(self.llm, "generate"):
            try:
                response = self.llm.generate(system_prompt, user_prompt) or ""
            except Exception as exc:
                print(f"Business rule LLM call failed; using local fallback: {exc}")

        parsed_rules = self._parse_json_rules(response)
        if parsed_rules:
            return parsed_rules

        return self._extract_rules_locally(technical_yaml, raw_code)

    def _parse_json_rules(self, response):
        if not (response or "").strip():
            return []

        candidates = [response.strip()]
        fenced = re.search(r"```(?:json)?\s*(.*?)```", response, flags=re.IGNORECASE | re.DOTALL)
        if fenced:
            candidates.insert(0, fenced.group(1).strip())

        object_start = response.find("{")
        object_end = response.rfind("}")
        if object_start != -1 and object_end != -1 and object_end > object_start:
            candidates.append(response[object_start:object_end + 1])

        list_start = response.find("[")
        list_end = response.rfind("]")
        if list_start != -1 and list_end != -1 and list_end > list_start:
            candidates.append(response[list_start:list_end + 1])

        for candidate in candidates:
            try:
                decoded = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            validated = validate_rule_payload(decoded)
            if validated:
                return self._normalize_rules(validated)

        return []

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

    @staticmethod
    def _strip_sequence_number(line):
        return re.sub(r"^\d{5,6}\s+", "", str(line or "").strip())
    def _condition_to_business_text(self, line):
        line = self._strip_sequence_number(line)
        condition = re.sub(r"^\s*IF\s+", "", line, flags=re.IGNORECASE)
        condition = re.sub(r"^\s*EVALUATE\s+", "", condition, flags=re.IGNORECASE)
        condition = re.split(r"\bTHEN\b|\bPERFORM\b|\bMOVE\b|\bCOMPUTE\b|\.", condition, maxsplit=1, flags=re.IGNORECASE)[0]
        condition = condition.replace("<=", " is less than or equal to ")
        condition = condition.replace(">=", " is greater than or equal to ")
        condition = condition.replace("=", " is equal to ")
        condition = condition.replace("<", " is less than ")
        condition = condition.replace(">", " is greater than ")
        condition = re.sub(r"\bNOT\s+=\b", " is not equal to ", condition, flags=re.IGNORECASE)
        return self._business_phrase(condition).strip() or "the qualifying business condition is met"

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

    def _as_user_story(self, text):
        text = re.sub(r"\s+", " ", str(text or "").strip())
        if not text:
            return ""
        if text.lower().startswith("as a ") or text.lower().startswith("as an "):
            return text
        return f"As an operations user, I want to {text[0].lower() + text[1:]} so that the business process remains consistent."
