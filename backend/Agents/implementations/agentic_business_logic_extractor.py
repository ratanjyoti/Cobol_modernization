# Owns language-aware business logic agent routing, LLM calls, JSON parsing, fallback, and normalization.
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from Agents.prompts.business_logic_agentic_prompts import (
    SYSTEM_PROMPTS,
    USER_PROMPT_TEMPLATE,
)


@dataclass
class BusinessLogicFileContext:
    file_id: int | str
    file_name: str
    detected_language: str
    source_code: str
    technical_yaml: str
    dependency_context: str = ""
    glossary_context: str = ""


class AgenticBusinessLogicExtractor:
    """
    language-aware business logic orchestrator.

    Responsibilities:
    - identify correct business logic agent from detected language/file name
    - select language-specific prompt
    - call LLM
    - parse JSON
    - normalize output
    - fallback to generic agent if language-specific extraction fails
    """

    def __init__(self, llm_config: dict[str, Any]):
        self.llm_config = llm_config or {}
        self.local_like = self._is_local_like()
        default_timeout = 30 if self.local_like else 120
        self.timeout_seconds = int(
            self.llm_config.get("timeout")
            or os.getenv("BUSINESS_LOGIC_LLM_TIMEOUT", default_timeout)
        )
        self.use_llm = str(os.getenv("BUSINESS_LOGIC_USE_LLM", "true")).lower() not in {
            "0",
            "false",
            "no",
        }
        self.local_max_llm_chars = int(
            os.getenv("BUSINESS_LOGIC_LOCAL_MAX_LLM_CHARS", "8000")
        )

    def extract(self, context: BusinessLogicFileContext) -> dict[str, Any]:
        agent_key = self._select_agent(
            detected_language=context.detected_language,
            file_name=context.file_name,
            source_code=context.source_code,
        )

        try:
            result = self._extract_with_agent(context, agent_key)
            result["agent_name"] = self._agent_name(agent_key)
            result["agent_key"] = agent_key
            result["fallback_used"] = False
            return result

        except Exception as first_error:
            if agent_key != "generic" and not self.local_like:
                try:
                    fallback_result = self._extract_with_agent(context, "generic")
                    fallback_result["agent_name"] = self._agent_name("generic")
                    fallback_result["agent_key"] = "generic"
                    fallback_result["fallback_used"] = True
                    fallback_result["fallback_reason"] = str(first_error)
                    return fallback_result
                except Exception as fallback_error:
                    first_error = fallback_error

            local_result = self._extract_locally(context, agent_key)
            local_result["agent_name"] = self._agent_name(agent_key)
            local_result["agent_key"] = agent_key
            local_result["fallback_used"] = True
            local_result["fallback_reason"] = str(first_error)
            return local_result

    def _extract_with_agent(
        self,
        context: BusinessLogicFileContext,
        agent_key: str,
    ) -> dict[str, Any]:
        if not self.use_llm:
            raise RuntimeError("Business logic LLM calls are disabled by BUSINESS_LOGIC_USE_LLM.")
        if self.local_like and len(context.source_code or "") > self.local_max_llm_chars:
            raise RuntimeError(
                "Source file exceeds BUSINESS_LOGIC_LOCAL_MAX_LLM_CHARS; using deterministic local extraction."
            )

        system_prompt = SYSTEM_PROMPTS.get(agent_key) or SYSTEM_PROMPTS["generic"]
        budgets = self._prompt_budgets()

        user_prompt = USER_PROMPT_TEMPLATE.format(
            file_id=context.file_id,
            file_name=context.file_name,
            detected_language=context.detected_language or "unknown",
            agent_key=agent_key,
            technical_yaml=self._trim(context.technical_yaml, budgets["technical_yaml"]),
            dependency_context=self._trim(context.dependency_context, budgets["dependency_context"]),
            glossary_context=self._trim(context.glossary_context, budgets["glossary_context"]),
            source_code=self._trim(context.source_code, budgets["source_code"]),
        )

        response_text = self._call_llm(system_prompt, user_prompt)
        if not str(response_text or "").strip():
            raise ValueError("Business logic agent returned empty output.")
        parsed = self._parse_json(response_text)

        return self._normalize_result(
            payload=parsed,
            context=context,
            agent_key=agent_key,
        )

    def _select_agent(
        self,
        detected_language: str,
        file_name: str,
        source_code: str,
    ) -> str:
        lang = str(detected_language or "").lower().strip()
        name = str(file_name or "").lower().strip()
        ext = Path(name).suffix.lower()
        code_upper = str(source_code or "").upper()

        if lang in {"cobol", "cbl", "cob"}:
            return "cobol"

        if lang in {"telon", "tln"}:
            return "telon"

        if lang in {"jcl"}:
            return "jcl"

        if lang in {"copybook", "cpy"}:
            return "copybook"

        if lang in {"sql", "db2"}:
            return "sql"

        if ext in {".cbl", ".cob"}:
            return "cobol"

        if ext in {".tel", ".tln"}:
            return "telon"

        if ext == ".jcl":
            return "jcl"

        if ext == ".cpy":
            return "copybook"

        if ext == ".sql":
            return "sql"

        # Content-based fallback
        if "IDENTIFICATION DIVISION" in code_upper or "PROCEDURE DIVISION" in code_upper:
            return "cobol"

        if "EXEC SQL" in code_upper:
            return "cobol"

        if "//JOB" in code_upper or "EXEC PGM=" in code_upper or " DD " in code_upper:
            return "jcl"

        if " PIC " in code_upper and "PROCEDURE DIVISION" not in code_upper:
            return "copybook"

        return "generic"

    def _agent_name(self, agent_key: str) -> str:
        names = {
            "cobol": "CobolBusinessLogicAgent",
            "telon": "TelonBusinessLogicAgent",
            "jcl": "JclBusinessLogicAgent",
            "copybook": "CopybookBusinessLogicAgent",
            "sql": "SqlBusinessLogicAgent",
            "generic": "GenericBusinessLogicAgent",
        }
        return names.get(agent_key, "GenericBusinessLogicAgent")

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        mode = (
            self.llm_config.get("mode")
            or self.llm_config.get("provider")
            or self.llm_config.get("llm_provider")
            or "local"
        ).lower()

        if mode in {"openrouter", "api", "cloud", "custom"}:
            return self._call_openai_compatible(system_prompt, user_prompt)

        return self._call_local(system_prompt, user_prompt)

    def _call_openai_compatible(self, system_prompt: str, user_prompt: str) -> str:
        api_key = (
            self.llm_config.get("key")
            or self.llm_config.get("api_key")
            or self.llm_config.get("openrouter_api_key")
        )
        base_url = (
            self.llm_config.get("url")
            or self.llm_config.get("base_url")
            or self.llm_config.get("custom_api_base_url")
            or "https://openrouter.ai/api/v1"
        )
        model = self.llm_config.get("model") or self.llm_config.get("llm_model")

        if not model:
            raise ValueError("Missing LLM model for business logic extraction.")

        headers = {"Content-Type": "application/json"}

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": int(self.llm_config.get("max_tokens") or (1600 if self.local_like else 2400)),
            "response_format": self._json_response_format("business_logic_result"),
        }

        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )

        if response.status_code == 400 and str(base_url).rstrip("/").endswith("/v1"):
            payload.pop("response_format", None)
            response = requests.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

    def _is_local_like(self) -> bool:
        mode = str(
            self.llm_config.get("mode")
            or self.llm_config.get("provider")
            or self.llm_config.get("llm_provider")
            or ""
        ).lower()
        base_url = str(
            self.llm_config.get("url")
            or self.llm_config.get("base_url")
            or self.llm_config.get("custom_api_base_url")
            or ""
        ).lower()
        return mode in {"local", "ollama", "lmstudio", "lm-studio"} or any(
            host in base_url for host in ("127.0.0.1", "localhost", ":1234", ":11434")
        )

    def _prompt_budgets(self) -> dict[str, int]:
        if self.local_like:
            return {
                "technical_yaml": 4500,
                "dependency_context": 1200,
                "glossary_context": 800,
                "source_code": 6000,
            }

        return {
            "technical_yaml": 12000,
            "dependency_context": 4000,
            "glossary_context": 4000,
            "source_code": 16000,
        }

    @staticmethod
    def _json_response_format(name: str) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": False,
                "schema": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        }

    def _call_local(self, system_prompt: str, user_prompt: str) -> str:
        base_url = (
            self.llm_config.get("url")
            or self.llm_config.get("base_url")
            or self.llm_config.get("custom_api_base_url")
            or "http://127.0.0.1:11434"
        )
        model = self.llm_config.get("model") or self.llm_config.get("llm_model") or "llama3"

        # OpenAI-compatible local server, for LM Studio.
        if "/v1" in base_url:
            return self._call_openai_compatible(system_prompt, user_prompt)

        # Ollama native API.
        response = requests.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {
                    "temperature": 0.1,
                },
            },
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()
        data = response.json()

        return data.get("message", {}).get("content", "")

    def _extract_locally(
        self,
        context: BusinessLogicFileContext,
        agent_key: str,
    ) -> dict[str, Any]:
        local_payload = self._build_local_payload(context)

        payload = {
            "business_purpose": local_payload.get("business_purpose", ""),
            "functional_logic": [
                {
                    "title": "Functional flow",
                    "description": local_payload.get("functional_logic", ""),
                    "technical_reference": context.file_name,
                    "confidence": 0.6,
                }
            ],
            "business_rules": [
                {
                    "rule_type": self._normalize_rule_type(rule.get("rule_type")),
                    "rule_text": rule.get("rule_text", ""),
                    "technical_reference": rule.get("technical_ref", ""),
                    "confidence": self._normalize_confidence(rule.get("confidence")),
                }
                for rule in local_payload.get("rules", [])
                if isinstance(rule, dict)
            ],
            "validations": [],
            "calculations": [],
            "data_rules": [],
            "state_transitions": [],
            "external_dependencies": [],
            "unresolved_items": [],
        }

        return self._normalize_result(
            payload=payload,
            context=context,
            agent_key=agent_key,
        )

    def _build_local_payload(self, context: BusinessLogicFileContext) -> dict[str, Any]:
        source_code = context.source_code or ""
        file_name = context.file_name or "uploaded source file"
        domain = self._infer_domain(file_name, source_code)
        rules = self._local_rules_from_source(source_code, domain)
        rules.extend(self._local_rules_from_yaml(context.technical_yaml, domain))

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
            unique_rules.append(
                {
                    "rule_text": rule_text,
                    "rule_type": rule.get("rule_type", "decision"),
                    "technical_ref": rule.get("technical_ref", ""),
                    "confidence": rule.get("confidence", 0.65),
                }
            )

        return {
            "business_purpose": self._local_business_purpose(
                file_name,
                domain,
                source_code,
            ),
            "functional_logic": self._local_functional_logic(domain, source_code),
            "rules": unique_rules[:25],
        }

    def _local_rules_from_source(
        self,
        source_code: str,
        domain: dict[str, str],
    ) -> list[dict[str, Any]]:
        lines = [
            (line_no, self._strip_sequence_number(line).strip())
            for line_no, line in enumerate((source_code or "").splitlines(), start=1)
        ]
        rules = []

        for index, (line_no, line) in enumerate(lines):
            if not line or line.upper().startswith(("*", "*>")):
                continue

            upper = line.upper()

            if upper.startswith("IF "):
                condition = self._condition_to_business_text(line)
                for action_line_no, action_line in lines[index + 1:index + 8]:
                    action_upper = action_line.upper()
                    if not action_line or action_upper.startswith(("*", "*>")):
                        continue
                    if action_upper.startswith(("ELSE", "END-IF", "END IF")):
                        break

                    action_text, rule_type = self._action_to_business_outcome(
                        action_line,
                        domain,
                    )
                    if action_text:
                        rules.append(
                            {
                                "rule_text": f"If {condition}, {action_text}.",
                                "rule_type": rule_type,
                                "technical_ref": f"source lines {line_no}-{action_line_no}",
                                "confidence": 0.85,
                            }
                        )

                continue

            rule_text, rule_type = self._line_to_business_rule(line, domain)
            if rule_text:
                rules.append(
                    {
                        "rule_text": rule_text,
                        "rule_type": rule_type,
                        "technical_ref": f"source line {line_no}",
                        "confidence": 0.65,
                    }
                )

        return rules

    def _local_rules_from_yaml(
        self,
        technical_yaml: str,
        domain: dict[str, str],
    ) -> list[dict[str, Any]]:
        rules = []

        for line_no, raw_line in enumerate((technical_yaml or "").splitlines(), start=1):
            line = raw_line.strip()
            if "description:" not in line:
                continue

            description = line.split("description:", 1)[1].strip().strip("'\"")
            rule_text, rule_type = self._line_to_business_rule(description, domain)

            if rule_text:
                rules.append(
                    {
                        "rule_text": rule_text,
                        "rule_type": rule_type,
                        "technical_ref": f"technical_yaml line {line_no}",
                        "confidence": 0.6,
                    }
                )

        return rules

    def _local_business_purpose(
        self,
        file_name: str,
        domain: dict[str, str],
        source_code: str,
    ) -> str:
        operations = []
        upper = (source_code or "").upper()

        if "ACCEPT" in upper:
            operations.append("captures input")
        if any(token in upper for token in ("READ", "SELECT", "EXEC SQL", "START")):
            operations.append(f"retrieves {domain['entity']} data")
        if any(token in upper for token in ("DISPLAY", "WRITE")):
            operations.append("produces business output")
        if any(token in upper for token in ("COMPUTE", "ADD ", "SUBTRACT", "MULTIPLY", "DIVIDE")):
            operations.append("calculates business values")
        if any(token in upper for token in ("DELETE", "REWRITE")):
            operations.append("maintains stored records")
        if "CALL" in upper:
            operations.append("coordinates supporting programs")

        operation_text = ", ".join(dict.fromkeys(operations)) or "executes required business steps"

        return (
            f"The {file_name} component supports {domain['process']}. "
            f"It {operation_text} so the modernized system can preserve the original business outcome."
        )

    def _local_functional_logic(self, domain: dict[str, str], source_code: str) -> str:
        steps = []
        upper = (source_code or "").upper()

        if "ACCEPT" in upper:
            steps.append(f"The process captures required {domain['entity']} input.")
        if any(token in upper for token in ("READ", "SELECT", "EXEC SQL", "START")):
            steps.append(f"The process retrieves required {domain['entity']} records.")
        if any(token in upper for token in ("IF", "EVALUATE")):
            steps.append("Business conditions decide the applicable outcome or exception path.")
        if any(token in upper for token in ("COMPUTE", "ADD ", "SUBTRACT", "MULTIPLY", "DIVIDE")):
            steps.append("Business values are calculated before output or persistence.")
        if any(token in upper for token in ("DISPLAY", "WRITE")):
            steps.append("The resulting business information is displayed, written, or passed downstream.")
        if "CALL" in upper:
            steps.append("Supporting programs are invoked when required.")

        return " ".join(steps) or f"The component executes the {domain['process']} workflow."

    def _line_to_business_rule(
        self,
        line: str,
        domain: dict[str, str],
    ) -> tuple[str, str]:
        stripped = self._strip_sequence_number(line).strip().rstrip(".")
        upper = stripped.upper()

        if upper.startswith("IF ") or upper.startswith("EVALUATE "):
            condition = self._condition_to_business_text(stripped)
            return (f"If {condition}, the matching business outcome must be applied.", "decision")

        if upper.startswith("COMPUTE "):
            target = self._extract_compute_target(stripped)
            return (f"The system must calculate {target} using the defined legacy formula.", "calculation")

        if upper.startswith("ADD "):
            return ("The system must add the specified business amount into the target total.", "calculation")

        if upper.startswith("SUBTRACT "):
            return ("The system must subtract the specified business amount from the target value.", "calculation")

        if upper.startswith("MULTIPLY "):
            return ("The system must multiply the specified business values according to the legacy rule.", "calculation")

        if upper.startswith("DIVIDE "):
            return ("The system must divide the specified business values while preserving decimal precision.", "calculation")

        if upper.startswith("READ ") or " READ " in upper:
            return (f"The system must retrieve the required {domain['entity']} record before continuing.", "data_rule")

        if upper.startswith(("WRITE ", "REWRITE ")) or " WRITE " in upper:
            return (f"The system must persist the required {domain['entity']} record as part of the process.", "state_transition")

        if upper.startswith("DELETE ") or " DELETE " in upper:
            return (f"The system must remove the selected {domain['entity']} record only when permitted.", "state_transition")

        if "EXEC SQL" in upper:
            return ("The system must access database information required to complete the business transaction.", "data_rule")

        if upper.startswith("CALL ") or " CALL " in upper:
            service = self._extract_called_service(stripped)
            return (f"The system must invoke {service} to complete the supporting business operation.", "external_dependency")

        if upper.startswith("PERFORM ") or " PERFORM " in upper:
            target = self._extract_perform_target(stripped)
            if target:
                return (f"The system must perform {self._business_phrase(target)} as part of the business workflow.", "workflow")

        return ("", "")

    def _action_to_business_outcome(
        self,
        line: str,
        domain: dict[str, str],
    ) -> tuple[str, str]:
        stripped = self._strip_sequence_number(line).strip().rstrip(".")
        upper = stripped.upper()

        move_match = re.search(
            r"\bMOVE\s+(.+?)\s+TO\s+([A-Z0-9_-]+)",
            stripped,
            flags=re.IGNORECASE,
        )
        if move_match:
            value = move_match.group(1).strip()
            target = move_match.group(2).strip()
            value_phrase = self._literal_to_business_value(value, target)

            if self._is_flag_target(target):
                subject = "account" if "OVERDRAFT" in target.upper() else self._business_phrase(target)
                return (f"the {subject} must be marked as {value_phrase}", "state_transition")

            return (f"the {self._business_phrase(target)} must be set to {value_phrase}", "state_transition")

        if upper.startswith("COMPUTE "):
            target = self._extract_compute_target(stripped)
            return (f"the {target} must be recalculated", "calculation")

        if upper.startswith("DISPLAY "):
            return ("the required business message must be shown", "workflow")

        if upper.startswith("CALL "):
            service = self._extract_called_service(stripped)
            return (f"{service} must be invoked", "external_dependency")

        return self._line_to_business_rule(stripped, domain)

    def _infer_domain(self, file_name: str, source_code: str) -> dict[str, str]:
        text = f"{file_name}\n{source_code}".lower()

        if any(word in text for word in ("account", "acct", "balance", "overdraft")):
            return {"entity": "account", "process": "account processing"}

        if any(word in text for word in ("customer", "cust", "client")):
            return {"entity": "customer", "process": "customer information handling"}

        if any(word in text for word in ("payroll", "salary", "employee", "emp")):
            return {"entity": "employee", "process": "payroll management"}

        if any(word in text for word in ("order", "invoice", "payment", "transaction", "txn")):
            return {"entity": "transaction", "process": "transaction processing"}

        return {"entity": "business record", "process": "legacy business processing"}

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

        negative_match = re.match(
            r"\s*([A-Z0-9_-]+)\s*(?:<|LESS\s+THAN)\s*(?:0|ZERO|ZEROS|ZEROES)\s*$",
            condition,
            flags=re.IGNORECASE,
        )
        if negative_match:
            return f"{self._business_phrase(negative_match.group(1))} is negative"

        condition = condition.replace("<=", " is less than or equal to ")
        condition = condition.replace(">=", " is greater than or equal to ")
        condition = condition.replace(" NOT = ", " is not equal to ")
        condition = condition.replace("=", " is equal to ")
        condition = condition.replace("<", " is less than ")
        condition = condition.replace(">", " is greater than ")
        return self._business_phrase(condition)

    def _literal_to_business_value(self, value: str, target: str) -> str:
        cleaned = str(value or "").strip().strip("'\"").rstrip(".")
        target_upper = target.upper()

        if cleaned.upper() in {"Y", "YES", "TRUE", "1"}:
            return "overdraft" if "OVERDRAFT" in target_upper else "active"
        if cleaned.upper() in {"N", "NO", "FALSE", "0"}:
            return "not overdraft" if "OVERDRAFT" in target_upper else "inactive"
        if cleaned.upper() in {"ZERO", "ZEROS", "ZEROES"}:
            return "zero"

        return self._business_phrase(cleaned)

    def _extract_compute_target(self, line: str) -> str:
        match = re.search(r"\bCOMPUTE\s+([A-Z0-9_-]+)", line, flags=re.IGNORECASE)
        return self._business_phrase(match.group(1)) if match else "the required business value"

    def _extract_called_service(self, line: str) -> str:
        service = re.sub(r".*\bCALL\b", "", line, flags=re.IGNORECASE)
        return self._business_phrase(service.strip(" .'\"") or "the supporting business service")

    def _extract_perform_target(self, line: str) -> str:
        match = re.search(r"\bPERFORM\s+([A-Z0-9_-]+)", line, flags=re.IGNORECASE)
        return match.group(1) if match else ""

    @staticmethod
    def _is_flag_target(target: str) -> bool:
        return any(marker in str(target or "").upper() for marker in ("FLAG", "SW", "SWITCH", "IND", "INDICATOR", "STATUS"))

    @staticmethod
    def _strip_sequence_number(line: str) -> str:
        return re.sub(r"^\d{5,6}\s+", "", str(line or "").strip())

    @staticmethod
    def _clean_text(text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "").strip())

    @staticmethod
    def _business_phrase(text: str) -> str:
        phrase = str(text or "").replace("-", " ").replace("_", " ").strip(" .'\"")
        replacements = {
            "acct": "account",
            "bal": "balance",
            "cust": "customer",
            "amt": "amount",
            "txn": "transaction",
            "id": "identifier",
            "num": "number",
            "qty": "quantity",
            "emp": "employee",
        }
        words = [replacements.get(word, word) for word in re.findall(r"[A-Za-z0-9']+", phrase.lower())]
        return re.sub(r"\s+", " ", " ".join(words)).strip()

    def _parse_json(self, text: str) -> dict[str, Any]:
        raw = str(text or "").strip()

        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"^```\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            return json.loads(raw)
        except Exception:
            match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
            if match:
                return json.loads(match.group(0))

        raise ValueError(f"Business logic agent returned invalid JSON: {raw[:500]}")

    def _normalize_result(
        self,
        payload: dict[str, Any],
        context: BusinessLogicFileContext,
        agent_key: str,
    ) -> dict[str, Any]:
        if not isinstance(payload, dict):
            payload = {}

        normalized = {
            "file_id": context.file_id,
            "file_name": context.file_name,
            "source_language": context.detected_language or agent_key,
            "technical_yaml": context.technical_yaml or "",
            "business_purpose": self._as_string(payload.get("business_purpose")),
            "functional_logic": self._as_list(payload.get("functional_logic")),
            "business_rules": self._as_list(payload.get("business_rules")),
            "validations": self._as_list(payload.get("validations")),
            "calculations": self._as_list(payload.get("calculations")),
            "data_rules": self._as_list(payload.get("data_rules")),
            "state_transitions": self._as_list(payload.get("state_transitions")),
            "external_dependencies": self._as_list(payload.get("external_dependencies")),
            "unresolved_items": self._as_list(payload.get("unresolved_items")),
            "raw_output": payload,
        }

        # Also convert validations/calculations/data rules into business_rules
        # so your existing DB/UI still sees them.
        normalized["business_rules"] = self._merge_rule_like_items(normalized)

        return normalized

    def _merge_rule_like_items(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = []

        for item in result.get("business_rules", []) or []:
            if isinstance(item, dict):
                normalized_item = dict(item)
                normalized_item["rule_type"] = self._normalize_rule_type(
                    item.get("rule_type")
                )
                normalized_item["confidence"] = self._normalize_confidence(
                    item.get("confidence", 0.7)
                )
                rules.append(normalized_item)

        for item in result.get("validations", []) or []:
            if isinstance(item, dict):
                rules.append(
                    {
                        "rule_type": "validation",
                        "rule_text": item.get("rule_text") or item.get("description") or "",
                        "technical_reference": item.get("technical_reference") or "",
                        "confidence": item.get("confidence", 0.7),
                    }
                )

        for item in result.get("calculations", []) or []:
            if isinstance(item, dict):
                rules.append(
                    {
                        "rule_type": "calculation",
                        "rule_text": item.get("calculation_text") or item.get("formula_or_logic") or "",
                        "technical_reference": item.get("technical_reference") or "",
                        "confidence": item.get("confidence", 0.7),
                    }
                )

        for item in result.get("data_rules", []) or []:
            if isinstance(item, dict):
                rules.append(
                    {
                        "rule_type": "data_rule",
                        "rule_text": item.get("business_meaning") or "",
                        "technical_reference": item.get("technical_reference") or item.get("field_or_record") or "",
                        "confidence": item.get("confidence", 0.7),
                    }
                )

        return rules

    def _as_string(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    def _as_list(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return [value]
        if isinstance(value, str) and value.strip():
            return [{"description": value.strip()}]
        return []

    @staticmethod
    def _normalize_rule_type(value: Any) -> str:
        normalized = str(value or "other").lower().strip()
        if "|" in normalized:
            return "other"

        mapping = {
            "business_decision": "decision",
            "data_access": "data_rule",
            "external_service": "external_dependency",
        }
        allowed = {
            "validation",
            "calculation",
            "decision",
            "data_rule",
            "transaction",
            "workflow",
            "state_transition",
            "external_dependency",
            "other",
        }
        normalized = mapping.get(normalized, normalized or "other")
        return normalized if normalized in allowed else "other"

    @staticmethod
    def _normalize_confidence(value: Any) -> float:
        if isinstance(value, (int, float)):
            return max(0.0, min(1.0, float(value)))

        mapping = {"high": 0.9, "medium": 0.7, "low": 0.45}
        return mapping.get(str(value or "").lower().strip(), 0.7)

    def _trim(self, text: Any, max_chars: int) -> str:
        value = str(text or "")
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + "\n\n...[TRUNCATED]..."
