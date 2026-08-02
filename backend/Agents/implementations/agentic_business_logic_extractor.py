from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from Agents.implementations.business_logic_extractor import BusinessLogicExtractorAgent
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
    Compact language-aware business logic orchestrator.

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
        self.local_extractor = BusinessLogicExtractorAgent(llm_client=None)
        self.timeout_seconds = int(self.llm_config.get("timeout") or 60)

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
            if agent_key != "generic":
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
        system_prompt = SYSTEM_PROMPTS.get(agent_key) or SYSTEM_PROMPTS["generic"]

        user_prompt = USER_PROMPT_TEMPLATE.format(
            file_id=context.file_id,
            file_name=context.file_name,
            detected_language=context.detected_language or "unknown",
            agent_key=agent_key,
            technical_yaml=self._trim(context.technical_yaml, 12000),
            dependency_context=self._trim(context.dependency_context, 4000),
            glossary_context=self._trim(context.glossary_context, 4000),
            source_code=self._trim(context.source_code, 16000),
        )

        response_text = self._call_llm(system_prompt, user_prompt)
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

        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=self.timeout_seconds,
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

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
        local_payload = self.local_extractor.extract_rules(
            technical_yaml=context.technical_yaml,
            raw_code=context.source_code,
            context_packet={
                "summary_history": context.dependency_context,
                "global_types": context.glossary_context,
            },
            use_llm=False,
            source_name=context.file_name,
        )

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
                rules.append(item)

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
        mapping = {
            "business_decision": "decision",
            "data_access": "data_rule",
            "external_service": "external_dependency",
        }
        return mapping.get(normalized, normalized or "other")

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
