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
from services.business_rule_quality_service import BusinessRuleQualityService
from services.legacy_source_preprocessor import LegacySourcePreprocessor


@dataclass
class BusinessLogicFileContext:
    file_id: int | str
    file_name: str
    detected_language: str
    source_code: str
    technical_yaml: str
    dependency_context: str = ""
    glossary_context: str = ""
    artifact_type: str = ""
    file_role: str = ""
    source_character_count: int = 0
    line_map: list[Any] | None = None
    paragraphs: list[Any] | None = None
    primary_start_line: int | None = None
    primary_end_line: int | None = None
    semantic_units: list[str] | None = None


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
        self.chunk_min_chars = int(os.getenv("BUSINESS_LOGIC_CHUNK_MIN_CHARS", "3000"))
        self.chunk_max_chars = int(os.getenv("BUSINESS_LOGIC_CHUNK_MAX_CHARS", "5000"))
        self.quality_service = BusinessRuleQualityService()
        self.preprocessor = LegacySourcePreprocessor()

    def extract(self, context: BusinessLogicFileContext) -> dict[str, Any]:
        agent_key = self._select_agent(
            detected_language=context.detected_language,
            file_name=context.file_name,
            source_code=context.source_code,
        )

        try:
            result = self._extract_with_agent(context, agent_key)
            result.update(
                self._execution_metadata(
                    context=context,
                    agent_key=agent_key,
                    extraction_mode=result.get("extraction_mode") or "llm",
                    llm_called=bool(result.get("llm_called", True)),
                    fallback_used=bool(result.get("fallback_used", False)),
                    fallback_reason=result.get("fallback_reason", ""),
                )
            )
            return result

        except Exception as first_error:
            if agent_key != "generic" and not self.local_like:
                try:
                    fallback_result = self._extract_with_agent(context, "generic")
                    fallback_result.update(
                        self._execution_metadata(
                            context=context,
                            agent_key="generic",
                            extraction_mode=fallback_result.get("extraction_mode") or "llm_generic_fallback",
                            llm_called=bool(fallback_result.get("llm_called", True)),
                            fallback_used=True,
                            fallback_reason=str(first_error),
                        )
                    )
                    return fallback_result
                except Exception as fallback_error:
                    first_error = fallback_error

            local_result = self._extract_locally(context, agent_key)
            local_result.update(
                self._execution_metadata(
                    context=context,
                    agent_key=agent_key,
                    extraction_mode="deterministic_fallback",
                    llm_called=False,
                    fallback_used=True,
                    fallback_reason=str(first_error),
                )
            )
            return local_result

    def extract_chunk(
        self,
        context: BusinessLogicFileContext,
        *,
        chunk_index: int | str,
        total_chunks: int,
        primary_start_line: int,
        primary_end_line: int,
        semantic_units: list[str],
    ) -> dict[str, Any]:
        agent_key = self._select_agent(
            detected_language=context.detected_language,
            file_name=context.file_name,
            source_code=context.source_code,
        )

        try:
            if self.local_like and len(context.source_code or "") > self.local_max_llm_chars:
                raise RuntimeError("Business Logic chunk prompt exceeds local LLM input budget.")
            result = self._extract_with_agent_request(context, agent_key)
            result.update(
                self._execution_metadata(
                    context=context,
                    agent_key=agent_key,
                    extraction_mode="llm",
                    llm_called=True,
                    fallback_used=False,
                    fallback_reason="",
                )
            )
        except Exception as exc:
            result = self._extract_locally(context, agent_key)
            result.update(
                self._execution_metadata(
                    context=context,
                    agent_key=agent_key,
                    extraction_mode="deterministic_fallback",
                    llm_called=False,
                    fallback_used=True,
                    fallback_reason=str(exc),
                )
            )

        result["chunk_index"] = chunk_index
        result["total_chunks"] = total_chunks
        result["primary_start_line"] = primary_start_line
        result["primary_end_line"] = primary_end_line
        result["semantic_units"] = semantic_units
        return result

    def _extract_with_agent(
        self,
        context: BusinessLogicFileContext,
        agent_key: str,
    ) -> dict[str, Any]:
        if self.local_like and len(context.source_code or "") > self.local_max_llm_chars:
            return self._extract_with_semantic_chunks(context, agent_key)

        return self._extract_with_agent_request(context, agent_key)

    def _extract_with_agent_request(
        self,
        context: BusinessLogicFileContext,
        agent_key: str,
    ) -> dict[str, Any]:
        if not self.use_llm:
            raise RuntimeError("Business logic LLM calls are disabled by BUSINESS_LOGIC_USE_LLM.")
        prompt_key = "cobol" if agent_key == "cobol_procedural_copybook" else agent_key
        system_prompt = SYSTEM_PROMPTS.get(prompt_key) or SYSTEM_PROMPTS["generic"]
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

    def _extract_with_semantic_chunks(
        self,
        context: BusinessLogicFileContext,
        agent_key: str,
    ) -> dict[str, Any]:
        chunks = self._semantic_chunks(context)
        if not chunks:
            raise RuntimeError("No semantic chunks could be assembled for business logic extraction.")

        merged: dict[str, Any] = {
            "business_purpose": "",
            "functional_logic": [],
            "business_rules": [],
            "validations": [],
            "calculations": [],
            "data_rules": [],
            "state_transitions": [],
            "external_dependencies": [],
            "unresolved_items": [],
        }
        failed_chunks: list[str] = []

        for chunk_index, chunk in enumerate(chunks, start=1):
            paragraph_names = ", ".join(chunk.get("paragraph_names") or []) or "FILE"
            chunk_context = BusinessLogicFileContext(
                file_id=context.file_id,
                file_name=f"{context.file_name} :: chunk {chunk_index}",
                detected_language=context.detected_language,
                source_code=chunk.get("source_code", ""),
                technical_yaml=self._chunk_technical_yaml(context, chunk, paragraph_names),
                dependency_context=context.dependency_context,
                glossary_context=context.glossary_context,
                artifact_type=context.artifact_type,
                file_role=context.file_role,
                source_character_count=context.source_character_count,
                line_map=context.line_map,
                paragraphs=chunk.get("paragraphs") or [],
            )
            try:
                partial = self._extract_with_agent_request(chunk_context, agent_key)
            except Exception as exc:
                failed_chunks.append(f"{chunk_index}:{exc}")
                partial = self._extract_locally(chunk_context, agent_key)

            if not merged["business_purpose"] and partial.get("business_purpose"):
                merged["business_purpose"] = partial.get("business_purpose")
            for key in (
                "functional_logic",
                "business_rules",
                "validations",
                "calculations",
                "data_rules",
                "state_transitions",
                "external_dependencies",
                "unresolved_items",
            ):
                values = partial.get(key) or []
                if isinstance(values, list):
                    merged[key].extend(values)

        normalized = self._normalize_result(merged, context, agent_key)
        normalized["extraction_mode"] = (
            "llm_semantic_chunking_with_partial_fallback"
            if failed_chunks
            else "llm_semantic_chunking"
        )
        normalized["llm_called"] = True
        normalized["fallback_used"] = bool(failed_chunks)
        normalized["fallback_reason"] = "; ".join(failed_chunks[:5])
        return normalized

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
            if self._looks_procedural_copybook(source_code):
                return "cobol_procedural_copybook"
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
            if self._looks_procedural_copybook(source_code):
                return "cobol_procedural_copybook"
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
            "cobol_procedural_copybook": "CobolProceduralCopybookAgent",
            "sql": "SqlBusinessLogicAgent",
            "generic": "GenericBusinessLogicAgent",
        }
        return names.get(agent_key, "GenericBusinessLogicAgent")

    @staticmethod
    def _looks_procedural_copybook(source_code: str) -> bool:
        return bool(
            re.search(
                r"(?im)^\s*(IF|EVALUATE|PERFORM|ADD|SUBTRACT|MULTIPLY|DIVIDE|"
                r"COMPUTE|MOVE|SET|CALL|DISPLAY|INITIALIZE)\b",
                source_code or "",
            )
        )

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
                    **{
                        key: value
                        for key, value in rule.items()
                        if key
                        in {
                            "paragraph",
                            "semantic_unit",
                            "source_start_line",
                            "source_end_line",
                            "source_excerpt",
                            "condition_or_trigger",
                            "business_outcome",
                            "derivation",
                            "evidence_status",
                        }
                    },
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
        rules = self._local_rules_from_source(context, domain)
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
                    **{
                        key: value
                        for key, value in rule.items()
                        if key
                        in {
                            "paragraph",
                            "semantic_unit",
                            "source_start_line",
                            "source_end_line",
                            "source_excerpt",
                            "condition_or_trigger",
                            "business_outcome",
                            "derivation",
                            "evidence_status",
                        }
                    },
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
        context: BusinessLogicFileContext,
        domain: dict[str, str],
    ) -> list[dict[str, Any]]:
        source_code = context.source_code or ""
        statements = self._numbered_primary_statements(source_code)
        if not statements:
            paragraphs = context.paragraphs or self.preprocessor.assemble_cobol_paragraphs(source_code)
            statements = [
                (paragraph.name, statement.start_line, statement.end_line, statement.text)
                for paragraph in paragraphs
                for statement in getattr(paragraph, "statements", [])
            ]
            if not statements:
                statements = [
                    ("FILE", line_no, line_no, self._strip_sequence_number(line).strip())
                    for line_no, line in enumerate(source_code.splitlines(), start=1)
                ]
        rules = []

        for index, (paragraph_name, line_no, end_line, line) in enumerate(statements):
            if not line or line.upper().startswith(("*", "*>")):
                continue

            upper = line.upper()

            if upper.startswith("IF "):
                condition = self._condition_to_business_text(line)
                inline_actions = self._actions_from_control_statement(line, domain)
                if inline_actions:
                    for action_text, rule_type in inline_actions:
                        rules.append(
                            {
                                "rule_text": self._scope_rule_text(paragraph_name, f"If {condition}, {action_text}."),
                                "rule_type": rule_type,
                                "technical_ref": f"{paragraph_name} lines {line_no}-{end_line}",
                                "paragraph": paragraph_name,
                                "source_start_line": line_no,
                                "source_end_line": end_line,
                                    "source_excerpt": line,
                                    "condition_or_trigger": condition,
                                    "business_outcome": action_text,
                                    "confidence": 0.72,
                                    "derivation": "deterministic",
                                    "evidence_status": "verified",
                                }
                        )
                else:
                    for next_paragraph, action_line_no, action_end_line, action_line in statements[index + 1:]:
                        if next_paragraph != paragraph_name:
                            break
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
                                    "rule_text": self._scope_rule_text(paragraph_name, f"If {condition}, {action_text}."),
                                    "rule_type": rule_type,
                                    "technical_ref": f"{paragraph_name} lines {line_no}-{action_end_line}",
                                    "paragraph": paragraph_name,
                                    "source_start_line": line_no,
                                    "source_end_line": action_end_line,
                                    "source_excerpt": f"{line} {action_line}",
                                    "condition_or_trigger": condition,
                                    "business_outcome": action_text,
                                    "confidence": 0.68,
                                    "derivation": "deterministic",
                                    "evidence_status": "verified",
                                }
                            )
                            break

                continue

            if upper.startswith("EVALUATE "):
                for branch_text in self._rules_from_evaluate(line, paragraph_name, line_no, end_line):
                    rules.append(branch_text)
                continue

            rule_text, rule_type = self._line_to_business_rule(line, domain)
            if rule_text:
                rules.append(
                    {
                        "rule_text": rule_text,
                        "rule_type": rule_type,
                        "technical_ref": f"{paragraph_name} lines {line_no}-{end_line}",
                        "paragraph": paragraph_name,
                        "source_start_line": line_no,
                        "source_end_line": end_line,
                        "source_excerpt": line,
                        "condition_or_trigger": line,
                        "business_outcome": rule_text,
                        "confidence": 0.62,
                        "derivation": "deterministic",
                        "evidence_status": "verified",
                    }
                )

        return rules

    def _numbered_primary_statements(self, source_code: str) -> list[tuple[str, int, int, str]]:
        if "PRIMARY SOURCE" not in (source_code or ""):
            return []

        in_primary = False
        numbered_lines: list[tuple[int, str]] = []
        for raw_line in (source_code or "").splitlines():
            marker = raw_line.strip().upper()
            if marker == "PRIMARY SOURCE":
                in_primary = True
                continue
            if marker == "CONTEXT-ONLY SOURCE":
                in_primary = False
                continue
            if not in_primary:
                continue

            match = re.match(r"^\s*(\d{1,6}):\s?(.*)$", raw_line)
            if not match:
                continue
            numbered_lines.append((int(match.group(1)), self._strip_sequence_number(match.group(2)).strip()))

        statements: list[tuple[str, int, int, str]] = []
        buffer: list[str] = []
        start_line = 0
        end_line = 0
        current_paragraph = "PRIMARY"

        for line_no, line in numbered_lines:
            if not line or line.upper().startswith(("*", "*>")):
                continue
            paragraph_match = re.match(r"^([A-Z0-9][A-Z0-9-]*)\.\s*$", line, flags=re.IGNORECASE)
            if paragraph_match:
                current_paragraph = paragraph_match.group(1).upper()
                continue

            starts_new = bool(
                buffer
                and re.match(
                    r"^(IF|EVALUATE|WHEN|ELSE|END-IF|END-EVALUATE|PERFORM|ADD|SUBTRACT|"
                    r"MULTIPLY|DIVIDE|COMPUTE|MOVE|SET|CALL|READ|WRITE|REWRITE|DELETE|"
                    r"DISPLAY|INITIALIZE|EXEC)\b",
                    line,
                    flags=re.IGNORECASE,
                )
            )
            if starts_new and not re.search(r"\b(IS|TO|THAN|ALSO|AND|OR|NOT|=|>|<)\s*$", buffer[-1], flags=re.IGNORECASE):
                text = re.sub(r"\s+", " ", " ".join(buffer)).strip().rstrip(".")
                if text:
                    statements.append((current_paragraph, start_line, end_line, text))
                buffer = []

            if not buffer:
                start_line = line_no
            end_line = line_no
            buffer.append(line.rstrip("."))

            if line.rstrip().endswith("."):
                text = re.sub(r"\s+", " ", " ".join(buffer)).strip().rstrip(".")
                if text:
                    statements.append((current_paragraph, start_line, end_line, text))
                buffer = []

        if buffer:
            text = re.sub(r"\s+", " ", " ".join(buffer)).strip().rstrip(".")
            if text:
                statements.append((current_paragraph, start_line, end_line, text))

        return statements

    def _local_rules_from_yaml(
        self,
        technical_yaml: str,
        domain: dict[str, str],
    ) -> list[dict[str, Any]]:
        rules = []
        allowed_section = ""
        current: dict[str, str] = {}

        for line_no, raw_line in enumerate((technical_yaml or "").splitlines(), start=1):
            line = raw_line.strip()
            section_match = re.match(r"^(decisions|validations|calculations|state_changes|data_rules):\s*$", line)
            if section_match:
                if current:
                    rules.extend(self._rule_from_structured_yaml(current, allowed_section, domain, line_no))
                    current = {}
                allowed_section = section_match.group(1)
                continue

            if not allowed_section:
                continue

            item_match = re.match(r"^-\s+([A-Za-z_]+):\s*(.*)$", line)
            field_match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
            if item_match:
                if current:
                    rules.extend(self._rule_from_structured_yaml(current, allowed_section, domain, line_no))
                current = {item_match.group(1): item_match.group(2).strip().strip("'\"")}
            elif field_match and current is not None:
                current[field_match.group(1)] = field_match.group(2).strip().strip("'\"")

        if current:
            rules.extend(self._rule_from_structured_yaml(current, allowed_section, domain, line_no if "line_no" in locals() else 1))

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
        if re.search(r"(?im)^\s*CALL\s+", source_code or ""):
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
        if re.search(r"(?im)^\s*CALL\s+", source_code or ""):
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
            amount, target = self._extract_add_parts(stripped)
            specific = self._specific_add_rule(amount, target)
            if specific:
                return (specific, "calculation")
            if target:
                return (f"The system must add {self._business_phrase(amount)} into {self._business_phrase(target)}.", "calculation")
            return ("", "")

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

        set_match = re.search(
            r"\bSET\s+([A-Z0-9_-]+)(?:\s+TO\s+([A-Z0-9_-]+))?",
            stripped,
            flags=re.IGNORECASE,
        )
        if set_match:
            target = set_match.group(1)
            value = set_match.group(2) or "true"
            return (
                f"the {self._business_phrase(target)} condition must be set to {self._business_phrase(value)}",
                "state_transition",
            )

        if upper.startswith("CALL "):
            service = self._extract_called_service(stripped)
            return (f"{service} must be invoked", "external_dependency")

        return self._line_to_business_rule(stripped, domain)

    def _actions_from_control_statement(
        self,
        statement: str,
        domain: dict[str, str],
    ) -> list[tuple[str, str]]:
        actions: list[tuple[str, str]] = []
        for action_match in re.finditer(
            r"\b(PERFORM\s+[A-Z0-9-]+|ADD\s+.+?\s+TO\s+[A-Z0-9-]+|"
            r"SET\s+[A-Z0-9-]+(?:\s+TO\s+[A-Z0-9-]+)?|"
            r"MOVE\s+.+?\s+TO\s+[A-Z0-9-]+|DISPLAY\s+.+?|CALL\s+['\"]?[A-Z0-9-]+)",
            statement,
            flags=re.IGNORECASE,
        ):
            action_text, rule_type = self._action_to_business_outcome(action_match.group(1), domain)
            if action_text:
                actions.append((action_text, rule_type))
        return actions

    def _rules_from_evaluate(
        self,
        statement: str,
        paragraph_name: str,
        start_line: int,
        end_line: int,
    ) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = []
        subjects = re.sub(r"(?i)^\s*EVALUATE\s+", "", statement).split(" WHEN ", 1)[0]
        for branch in re.findall(r"(?i)\bWHEN\s+(.+?)(?=\bWHEN\b|\bEND-EVALUATE\b|$)", statement):
            branch_text = re.sub(r"\s+", " ", branch).strip()
            if not branch_text:
                continue
            rules.append(
                {
                    "rule_text": (
                        f"When {self._business_phrase(subjects)} matches "
                        f"{self._business_phrase(branch_text)}, apply the branch outcome."
                    ),
                    "rule_type": "decision",
                    "technical_ref": f"{paragraph_name} lines {start_line}-{end_line}",
                    "paragraph": paragraph_name,
                    "source_start_line": start_line,
                    "source_end_line": end_line,
                    "source_excerpt": statement,
                    "confidence": 0.58,
                    "derivation": "deterministic",
                    "evidence_status": "verified",
                }
            )
        return rules

    @staticmethod
    def _scope_rule_text(paragraph_name: str, rule_text: str) -> str:
        if "REVERSE" in str(paragraph_name or "").upper():
            return f"When applying the reverse result, {rule_text[0].lower() + rule_text[1:] if rule_text else rule_text}"
        return rule_text

    def _rule_from_structured_yaml(
        self,
        item: dict[str, str],
        section: str,
        domain: dict[str, str],
        line_no: int,
    ) -> list[dict[str, Any]]:
        if not item or section not in {"decisions", "validations", "calculations", "state_changes", "data_rules"}:
            return []

        paragraph = item.get("paragraph", "")
        source_ref = f"{paragraph} technical_yaml line {line_no}".strip()
        statement = item.get("statement") or item.get("condition") or item.get("description") or item.get("business_meaning") or ""

        if section in {"decisions", "validations"} and item.get("condition"):
            rule_text = f"If {self._condition_to_business_text('IF ' + item['condition'])}, apply the verified outcome."
            rule_type = "decision" if section == "decisions" else "validation"
        elif section == "calculations":
            rule_text, rule_type = self._line_to_business_rule(statement, domain)
        elif section == "state_changes":
            action_text, action_type = self._action_to_business_outcome(statement, domain)
            rule_text = f"When the legacy workflow reaches this step, {action_text}." if action_text else ""
            rule_type = action_type or "state_transition"
        elif section == "data_rules":
            meaning = item.get("business_meaning") or item.get("field_or_record") or ""
            rule_text = f"The system must preserve the data rule for {self._business_phrase(meaning)}." if meaning else ""
            rule_type = "data_rule"
        else:
            rule_text = ""
            rule_type = "other"

        if not rule_text:
            return []

        return [
            {
                "rule_text": rule_text,
                "rule_type": rule_type,
                "technical_ref": source_ref,
                "paragraph": paragraph,
                "source_excerpt": statement,
                "confidence": 0.54,
                "derivation": "deterministic",
                "evidence_status": "verified" if paragraph or statement else "unresolved",
            }
        ]

    def _semantic_chunks(self, context: BusinessLogicFileContext) -> list[dict[str, Any]]:
        paragraphs = context.paragraphs or self.preprocessor.assemble_cobol_paragraphs(context.source_code or "")
        chunks: list[dict[str, Any]] = []
        current: list[Any] = []
        current_chars = 0

        for paragraph in paragraphs:
            paragraph_text = self._paragraph_text(paragraph)
            paragraph_chars = len(paragraph_text)
            if current and current_chars + paragraph_chars > self.chunk_max_chars:
                chunks.append(self._build_semantic_chunk(current))
                current = []
                current_chars = 0

            current.append(paragraph)
            current_chars += paragraph_chars

            if current_chars >= self.chunk_min_chars:
                chunks.append(self._build_semantic_chunk(current))
                current = []
                current_chars = 0

        if current:
            chunks.append(self._build_semantic_chunk(current))

        if not chunks and context.source_code:
            chunks.append(
                {
                    "source_code": context.source_code[: self.chunk_max_chars],
                    "paragraph_names": ["FILE"],
                    "paragraphs": [],
                }
            )

        return chunks

    def _build_semantic_chunk(self, paragraphs: list[Any]) -> dict[str, Any]:
        return {
            "source_code": "\n\n".join(self._paragraph_text(paragraph) for paragraph in paragraphs),
            "paragraph_names": [getattr(paragraph, "name", "FILE") for paragraph in paragraphs],
            "paragraphs": paragraphs,
        }

    @staticmethod
    def _paragraph_text(paragraph: Any) -> str:
        lines = [f"{getattr(paragraph, 'name', 'FILE')}."]
        for statement in getattr(paragraph, "statements", []) or []:
            lines.append(f"{getattr(statement, 'text', '')}.")
        return "\n".join(line for line in lines if line.strip())

    def _chunk_technical_yaml(
        self,
        context: BusinessLogicFileContext,
        chunk: dict[str, Any],
        paragraph_names: str,
    ) -> str:
        return (
            f"file_role: {context.file_role or 'unknown'}\n"
            f"artifact_type: {context.artifact_type or 'unknown'}\n"
            f"chunk_paragraphs: {paragraph_names}\n"
            f"{context.technical_yaml or ''}"
        )

    def _execution_metadata(
        self,
        context: BusinessLogicFileContext,
        agent_key: str,
        extraction_mode: str,
        llm_called: bool,
        fallback_used: bool,
        fallback_reason: str = "",
    ) -> dict[str, Any]:
        return {
            "selected_agent": self._agent_name(agent_key),
            "agent_name": self._agent_name(agent_key),
            "agent_key": agent_key,
            "extraction_mode": extraction_mode,
            "llm_called": llm_called,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "model": self.llm_config.get("model") or self.llm_config.get("llm_model") or "llama3",
            "source_character_count": context.source_character_count or len(context.source_code or ""),
            "detected_language": context.detected_language or "unknown",
            "artifact_type": context.artifact_type or self._infer_artifact_type(context, agent_key),
            "file_role": context.file_role or "domain_program",
        }

    def _coverage_summary(
        self,
        context: BusinessLogicFileContext,
        rules: list[dict[str, Any]],
    ) -> dict[str, Any]:
        paragraphs = [
            paragraph
            for paragraph in (context.paragraphs or [])
            if getattr(paragraph, "name", "FILE") not in {"FILE"}
        ]
        if not paragraphs:
            return {
                "paragraphs_total": 0,
                "paragraphs_analyzed": 0,
                "paragraphs_with_rules": 0,
                "paragraphs_without_business_rules": 0,
                "source_coverage": 0.0,
            }

        paragraph_names = {getattr(paragraph, "name", "") for paragraph in paragraphs}
        rule_text = "\n".join(
            str(rule.get("paragraph") or rule.get("technical_ref") or rule.get("technical_reference") or "")
            for rule in rules
            if isinstance(rule, dict)
        ).upper()
        with_rules = {name for name in paragraph_names if name and name.upper() in rule_text}
        analyzed = len(paragraphs)
        without_rules = max(0, analyzed - len(with_rules))
        return {
            "paragraphs_total": len(paragraphs),
            "paragraphs_analyzed": analyzed,
            "paragraphs_with_rules": len(with_rules),
            "paragraphs_without_business_rules": without_rules,
            "source_coverage": round(analyzed / len(paragraphs), 4) if paragraphs else 0.0,
        }

    def _infer_artifact_type(self, context: BusinessLogicFileContext, agent_key: str) -> str:
        if agent_key == "cobol_procedural_copybook":
            return "procedural_copybook"
        if agent_key == "copybook":
            return "data_copybook"
        if agent_key == "jcl":
            return "jcl_job"
        if agent_key == "sql":
            return "sql_script"
        return "domain_program"

    @staticmethod
    def _extract_add_parts(line: str) -> tuple[str, str]:
        match = re.search(r"\bADD\s+(.+?)\s+TO\s+([A-Z0-9_-]+)", line, flags=re.IGNORECASE)
        if not match:
            return "", ""
        return match.group(1).strip(), match.group(2).strip()

    def _specific_add_rule(self, amount: str, target: str) -> str:
        amount_norm = str(amount or "").strip().strip("'\"").upper()
        target_norm = str(target or "").strip().upper()
        is_one = amount_norm in {"1", "+1", "ONE"}

        if target_norm.endswith("NUMBER-PASSED") and is_one:
            return "When a test passes, increment the passed-test counter by one."
        if target_norm.endswith("NUMBER-FAILED") and is_one:
            return "When a test fails, increment the failed-test counter by one."
        if target_norm.endswith("MOCK-COUNT") and is_one:
            return "When no matching mock exists, create a new mock entry."
        return ""

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

        condition = re.sub(r"\bIS\s+GREATER\s+THAN\s+OR\s+EQUAL\s+TO\b", "is at least", condition, flags=re.IGNORECASE)
        condition = re.sub(r"\bIS\s+LESS\s+THAN\s+OR\s+EQUAL\s+TO\b", "is no more than", condition, flags=re.IGNORECASE)
        condition = condition.replace("<=", " is no more than ")
        condition = condition.replace(">=", " is at least ")
        condition = re.sub(r"\bNOT\s*=\b", " is not equal to ", condition, flags=re.IGNORECASE)
        condition = re.sub(r"(?<![<>=])=(?![<>=])", " is equal to ", condition)
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
        normalized["business_rules"], rejected = self.quality_service.filter_rules(
            normalized["business_rules"]
        )
        normalized["business_rules"] = self._dedupe_rules(normalized["business_rules"])
        if rejected:
            normalized["unresolved_items"].extend(
                {
                    "item": item.get("rule_text", ""),
                    "reason": item.get("reason", "quality_gate_rejected"),
                    "technical_reference": context.file_name,
                }
                for item in rejected
            )
        normalized["source_character_count"] = (
            context.source_character_count or len(context.source_code or "")
        )
        normalized["detected_language"] = context.detected_language or agent_key
        normalized["artifact_type"] = context.artifact_type or self._infer_artifact_type(context, agent_key)
        normalized["file_role"] = context.file_role or "domain_program"
        normalized["coverage"] = self._coverage_summary(context, normalized["business_rules"])

        return normalized

    @staticmethod
    def _dedupe_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for rule in rules:
            text = str(rule.get("rule_text") or "").strip().lower()
            evidence = str(rule.get("source_excerpt") or rule.get("technical_ref") or rule.get("technical_reference") or "").strip().lower()
            key = f"{text}|{evidence}"
            if not text or key in seen:
                continue
            seen.add(key)
            unique.append(rule)
        return unique

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
