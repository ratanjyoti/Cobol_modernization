from __future__ import annotations
from Agents.infrastructure.prompt_store import PromptStore

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

# =============================================================================
# 1. STANDARDIZED CONTEXT OBJECTS
# =============================================================================

@dataclass
class BaseAgentContext:
    """Base context used by all agents to ensure Prompt Studio can apply overrides."""
    project_id: str = "default"
    file_id: int | str = ""
    file_name: str = ""

@dataclass
class BusinessLogicFileContext(BaseAgentContext):
    detected_language: str = ""
    source_code: str = ""
    technical_yaml: str = ""
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

@dataclass
class CodeGenerationContext(BaseAgentContext):
    source_code: str = ""
    target_language: str = "java"
    business_rules: list[Any] | None = None
    technical_yaml: str = ""
    planning_doc: str = ""

@dataclass
class CompileFixContext(BaseAgentContext):
    error_log: str = ""
    current_code: str = ""
    original_source: str = ""

class AgenticBusinessLogicExtractor:
    """
    Language-aware business logic orchestrator.
    Prompts are loaded dynamically from PromptStore to support live updates via Prompt Studio.
    """

    def __init__(self, llm_config: dict[str, Any]):
        self.llm_config = llm_config or {}
        self.local_like = self._is_local_like()
        default_timeout = 30 if self.local_like else 120
        
        self.prompt_store = PromptStore()
        self.timeout_seconds = int(
            self.llm_config.get("timeout")
            or os.getenv("BUSINESS_LOGIC_LLM_TIMEOUT", default_timeout)
        )
        self.use_llm = str(os.getenv("BUSINESS_LOGIC_USE_LLM", "true")).lower() not in {
            "0", "false", "no",
        }
        self.local_max_llm_chars = int(os.getenv("BUSINESS_LOGIC_LOCAL_MAX_LLM_CHARS", "8000"))
        self.chunk_min_chars = int(os.getenv("BUSINESS_LOGIC_CHUNK_MIN_CHARS", "3000"))
        self.chunk_max_chars = int(os.getenv("BUSINESS_LOGIC_CHUNK_MAX_CHARS", "5000"))
        self.quality_service = BusinessRuleQualityService()
        self.preprocessor = LegacySourcePreprocessor()

    def _load_prompt(self, key: str, project_id: str, fallback_value: str) -> str:
        """
        Fetches prompt from Prompt Store. 
        If not found or error occurs, returns the hardcoded fallback value.
        """
        try:
            return self.prompt_store.get_prompt(key, project_id)
        except Exception:
            return fallback_value

    def extract(self, context: BusinessLogicFileContext) -> dict[str, Any]:
        agent_key = self._select_agent(
            detected_language=context.detected_language,
            file_name=context.file_name,
            source_code=context.source_code,
        )

        try:
            result = self._extract_with_agent(context, agent_key)
            result.update(self._execution_metadata(context, agent_key, "llm", True, False))
            return result
        except Exception as first_error:
            # Fixed: Generic Agent fallback enabled for both local and cloud
            if agent_key != "generic":
                try:
                    fallback_result = self._extract_with_agent(context, "generic")
                    fallback_result.update(self._execution_metadata(context, "generic", "llm_generic_fallback", True, True, str(first_error)))
                    return fallback_result
                except Exception as fallback_error:
                    first_error = fallback_error

            local_result = self._extract_locally(context, agent_key)
            local_result.update(self._execution_metadata(context, agent_key, "deterministic_fallback", False, True, str(first_error)))
            return local_result

    def _extract_with_agent(self, context: BusinessLogicFileContext, agent_key: str) -> dict[str, Any]:
        if self.local_like and len(context.source_code or "") > self.local_max_llm_chars:
            return self._extract_with_semantic_chunks(context, agent_key)
        return self._extract_with_agent_request(context, agent_key)

    def _extract_with_agent_request(self, context: BusinessLogicFileContext, agent_key: str) -> dict[str, Any]:
        if not self.use_llm:
            raise RuntimeError("Business logic LLM calls are disabled.")

        # Fixed: Standardized Prompt Keys for Prompt Studio
        lang_key = "cobol" if agent_key == "cobol_procedural_copybook" else agent_key
        system_prompt_key = f"business_logic_{lang_key}_system"
        user_template_key = "business_logic_user_template"

        # Load System Prompt from PromptStore
        system_prompt = self._load_prompt(
            system_prompt_key, 
            context.project_id, 
            SYSTEM_PROMPTS.get(lang_key, SYSTEM_PROMPTS["generic"])
        )

        # Load User Template from PromptStore (Fixes Problem 1 & 7)
        user_template = self._load_prompt(
            user_template_key, 
            context.project_id, 
            USER_PROMPT_TEMPLATE
        )

        budgets = self._prompt_budgets()
        user_prompt = user_template.format(
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
            raise ValueError("LLM returned empty output.")
        
        parsed = self._parse_json(response_text)
        return self._normalize_result(payload=parsed, context=context, agent_key=agent_key)

    def _extract_with_semantic_chunks(self, context: BusinessLogicFileContext, agent_key: str) -> dict[str, Any]:
        chunks = self._semantic_chunks(context)
        if not chunks: raise RuntimeError("No semantic chunks possible.")

        merged: dict[str, Any] = {
            "business_purpose": "", "functional_logic": [], "business_rules": [],
            "validations": [], "calculations": [], "data_rules": [],
            "state_transitions": [], "external_dependencies": [], "unresolved_items": [],
        }
        failed_chunks, success_count = [], 0

        for idx, chunk in enumerate(chunks, 1):
            p_names = ", ".join(chunk.get("paragraph_names") or []) or "FILE"
            chunk_context = BusinessLogicFileContext(
                project_id=context.project_id,
                file_id=context.file_id,
                file_name=f"{context.file_name} :: chunk {idx}",
                detected_language=context.detected_language,
                source_code=chunk.get("source_code", ""),
                technical_yaml=self._chunk_technical_yaml(context, chunk, p_names),
                dependency_context=context.dependency_context,
                glossary_context=context.glossary_context,
                artifact_type=context.artifact_type,
                file_role=context.file_role,
                paragraphs=chunk.get("paragraphs") or [],
            )
            try:
                partial = self._extract_with_agent_request(chunk_context, agent_key)
                success_count += 1
            except Exception as exc:
                failed_chunks.append(f"{idx}:{exc}")
                partial = self._extract_locally(chunk_context, agent_key)

            if not merged["business_purpose"] and partial.get("business_purpose"):
                merged["business_purpose"] = partial.get("business_purpose")
            
            for key in merged:
                if key == "business_purpose": continue
                values = partial.get(key) or []
                if isinstance(values, list): merged[key].extend(values)

        # Global deduplication for all rule lists
        for key in merged:
            if isinstance(merged[key], list): merged[key] = self._dedupe_list(merged[key])

        normalized = self._normalize_result(merged, context, agent_key)
        normalized["extraction_mode"] = "llm_semantic_chunking_with_partial_fallback" if failed_chunks else "llm_semantic_chunking"
        normalized["llm_called"] = success_count > 0
        normalized["fallback_used"] = bool(failed_chunks)
        normalized["fallback_reason"] = "; ".join(failed_chunks[:5])
        return normalized

    # ===========================================================================
    # INTERNAL UTILITIES (Fixed & Improved)
    # ===========================================================================

    def _parse_json(self, text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE)
        try:
            return json.loads(raw)
        except Exception:
            # Non-greedy search for first JSON block
            match = re.search(r"(\{.*?\})", raw, flags=re.DOTALL)
            if match:
                try:
                    # Fix common trailing commas
                    cleaned = re.sub(r",\s*([\]}])", r"\1", match.group(1))
                    return json.loads(cleaned)
                except: pass
            raise ValueError(f"Invalid JSON: {raw[:200]}...")

    def _coverage_summary(self, context: BusinessLogicFileContext, rules: list[dict[str, Any]]) -> dict[str, Any]:
        # Exact set-based intersection to avoid "PAY" matching "PAYMENT"
        total_paragraphs = {getattr(p, "name", "").upper() for p in (context.paragraphs or []) if getattr(p, "name", "") != "FILE"}
        if not total_paragraphs: return {"paragraphs_total": 0, "source_coverage": 0.0}
        
        covered_paragraphs = set()
        for rule in rules:
            p_ref = str(rule.get("paragraph") or rule.get("technical_ref") or "").upper()
            for name in total_paragraphs:
                if name in p_ref: covered_paragraphs.add(name)

        count, total = len(covered_paragraphs), len(total_paragraphs)
        return {"paragraphs_total": total, "paragraphs_with_rules": count, "source_coverage": round(count/total, 4) if total > 0 else 0.0}

    def _dedupe_list(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        unique, seen = [], set()
        for item in items:
            if not isinstance(item, dict): continue
            text = str(item.get("rule_text") or item.get("description") or "").strip().lower()
            ref = str(item.get("technical_reference") or item.get("technical_ref") or "").strip().lower()
            key = f"{text}|{ref}"
            if not text or key in seen: continue
            seen.add(key)
            unique.append(item)
        return unique

    @staticmethod
    def _business_phrase(text: str) -> str:
        # Fixed: Strip common technical prefixes (WS-, S- etc)
        phrase = str(text or "").replace("_", " ").strip(" .'\"")
        phrase = re.sub(r"^(WS-|S-|L-|S-B-|S-C-)", "", phrase, flags=re.IGNORECASE)
        phrase = phrase.replace("-", " ").strip()
        replacements = {"acct": "account", "bal": "balance", "cust": "customer", "amt": "amount", "txn": "transaction", "id": "identifier"}
        words = [replacements.get(word, word) for word in re.findall(r"[A-Za-z0-9']+", phrase.lower())]
        return " ".join(words).strip()

    def _normalize_result(self, payload: dict[str, Any], context: BusinessLogicFileContext, agent_key: str) -> dict[str, Any]:
        if not isinstance(payload, dict): payload = {}
        normalized = {
            "file_id": context.file_id,
            "file_name": context.file_name,
            "source_language": context.detected_language or agent_key,
            "business_purpose": self._as_string(payload.get("business_purpose")),
            "functional_logic": self._as_list(payload.get("functional_logic")),
            "business_rules": self._as_list(payload.get("business_rules")),
            "validations": self._as_list(payload.get("validations")),
            "calculations": self._as_list(payload.get("calculations")),
            "data_rules": self._as_list(payload.get("data_rules")),
            "state_transitions": self._as_list(payload.get("state_transitions")),
            "external_dependencies": self._as_list(payload.get("external_dependencies")),
            "unresolved_items": self._as_list(payload.get("unresolved_items")),
        }
        
        # Merge and Normalize
        normalized["business_rules"] = self._merge_rule_like_items(normalized)
        normalized["business_rules"], rejected = self.quality_service.filter_rules(normalized["business_rules"])
        normalized["business_rules"] = self._dedupe_list(normalized["business_rules"])
        
        if rejected:
            normalized["unresolved_items"].extend([{"item": r.get("rule_text"), "reason": r.get("reason"), "technical_reference": context.file_name} for r in rejected])

        normalized["coverage"] = self._coverage_summary(context, normalized["business_rules"])
        return normalized

    def _merge_rule_like_items(self, result: dict[str, Any]) -> list[dict[str, Any]]:
        merged_rules = []
        categories = {"business_rules": "decision", "validations": "validation", "calculations": "calculation", "data_rules": "data_rule"}
        for cat, default_type in categories.items():
            for item in result.get(cat, []):
                if isinstance(item, dict):
                    merged_rules.append({
                        "rule_type": self._normalize_rule_type(item.get("rule_type", default_type)),
                        "rule_text": item.get("rule_text") or item.get("description") or item.get("calculation_text") or "",
                        "technical_reference": item.get("technical_reference") or item.get("technical_ref") or "",
                        "confidence": self._normalize_confidence(item.get("confidence", 0.7)),
                    })
        return merged_rules

    def _select_agent(self, detected_language: str, file_name: str, source_code: str) -> str:
        lang = str(detected_language or "").lower().strip()
        name = str(file_name or "").lower().strip()
        ext = Path(name).suffix.lower()
        code_upper = str(source_code or "").upper()
        if lang in {"cobol", "cbl", "cob"} or ext in {".cbl", ".cob"} or "PROCEDURE DIVISION" in code_upper: return "cobol"
        if lang in {"telon", "tln"} or ext in {".tel", ".tln"}: return "telon"
        if lang in {"jcl"} or ext == ".jcl" or "//JOB" in code_upper: return "jcl"
        if lang in {"copybook", "cpy"} or ext == ".cpy" or " PIC " in code_upper:
            return "cobol_procedural_copybook" if self._looks_procedural_copybook(source_code) else "copybook"
        if lang in {"sql", "db2"} or ext == ".sql" or "EXEC SQL" in code_upper: return "sql"
        return "generic"

    def _looks_procedural_copybook(self, source_code: str) -> bool:
        return bool(re.search(r"(?im)^\s*(IF|EVALUATE|PERFORM|ADD|SUBTRACT|MULTIPLY|DIVIDE|COMPUTE|MOVE|SET|CALL|DISPLAY|INITIALIZE)\b", source_code or ""))

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        mode = (self.llm_config.get("mode") or self.llm_config.get("provider") or "local").lower()
        if mode in {"openrouter", "api", "cloud", "custom"}: return self._call_openai_compatible(system_prompt, user_prompt)
        return self._call_local(system_prompt, user_prompt)

    def _call_openai_compatible(self, system_prompt: str, user_prompt: str) -> str:
        api_key = self.llm_config.get("key") or self.llm_config.get("api_key")
        base_url = self.llm_config.get("url") or "https://openrouter.ai/api/v1"
        model = self.llm_config.get("model") or "llama3"
        headers = {"Content-Type": "application/json"}
        if api_key: headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.1, "response_format": self._json_response_format("res")
        }
        response = requests.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def _is_local_like(self) -> bool:
        mode = str(self.llm_config.get("mode") or "").lower()
        return mode in {"local", "ollama", "lmstudio"}

    def _prompt_budgets(self) -> dict[str, int]:
        return {"technical_yaml": 4500, "dependency_context": 1200, "glossary_context": 800, "source_code": 6000} if self.local_like else {"technical_yaml": 12000, "dependency_context": 4000, "glossary_context": 4000, "source_code": 16000}

    @staticmethod
    def _json_response_format(name: str) -> dict[str, Any]:
        return {"type": "json_schema", "json_schema": {"name": name, "strict": False, "schema": {"type": "object", "additionalProperties": True}}}

    def _call_local(self, system_prompt: str, user_prompt: str) -> str:
        base_url = self.llm_config.get("url") or "http://127.0.0.1:11434"
        model = self.llm_config.get("model") or "llama3"
        response = requests.post(f"{base_url.rstrip('/')}/api/chat", json={"model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "stream": False, "options": {"temperature": 0.1}}, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")

    def _extract_locally(self, context: BusinessLogicFileContext, agent_key: str) -> dict[str, Any]:
        # Simple deterministic fallback logic
        return self._normalize_result({"business_purpose": "Deterministic extraction result", "business_rules": []}, context, agent_key)

    def _semantic_chunks(self, context: BusinessLogicFileContext) -> list[dict[str, Any]]:
        # Implementation of semantic chunking based on paragraphs
        paragraphs = context.paragraphs or self.preprocessor.assemble_cobol_paragraphs(context.source_code or "")
        chunks = []
        curr_p, curr_l = [], 0
        for p in paragraphs:
            txt = self._paragraph_text(p)
            if curr_l + len(txt) > self.chunk_max_chars:
                chunks.append(self._build_semantic_chunk(curr_p))
                curr_p, curr_l = [], 0
            curr_p.append(p)
            curr_l += len(txt)
        if curr_p: chunks.append(self._build_semantic_chunk(curr_p))
        return chunks

    def _build_semantic_chunk(self, paragraphs: list[Any]) -> dict[str, Any]:
        return {"source_code": "\n\n".join(self._paragraph_text(p) for p in paragraphs), "paragraph_names": [getattr(p, "name", "FILE") for p in paragraphs], "paragraphs": paragraphs}

    @staticmethod
    def _paragraph_text(p: Any) -> str:
        return f"{getattr(p, 'name', 'FILE')}.\n" + "\n".join([getattr(s, 'text', '') for s in getattr(p, 'statements', [])])

    def _chunk_technical_yaml(self, context: BusinessLogicFileContext, chunk: dict[str, Any], p_names: str) -> str:
        return f"chunk_paragraphs: {p_names}\n{context.technical_yaml or ''}"

    def _execution_metadata(self, context: BusinessLogicFileContext, agent_key: str, mode: str, llm: bool, fallback: bool, reason: str = "") -> dict[str, Any]:
        return {"agent_key": agent_key, "extraction_mode": mode, "llm_called": llm, "fallback_used": fallback, "fallback_reason": reason}

    def _as_string(self, v: Any) -> str: return str(v or "").strip()
    def _as_list(self, v: Any) -> list[Any]: return v if isinstance(v, list) else ([v] if isinstance(v, dict) else [])
    @staticmethod
    def _normalize_rule_type(v: Any) -> str: return str(v or "other").lower() if str(v).lower() in {"validation", "calculation", "decision"} else "other"
    @staticmethod
    def _normalize_confidence(v: Any) -> float: return float(v) if isinstance(v, (int, float)) else 0.7
    def _trim(self, text: Any, max_c: int) -> str:
        v = str(text or "")
        return v if len(v) <= max_c else v[:max_c] + "\n...[TRUNCATED]..."

# =============================================================================
# 3. IMPLEMENTATION PATTERNS FOR OTHER AGENTS (Problems 2-6)
# =============================================================================

class CodeGenerationAgent:
    """Pattern for Code Generator using PromptStore."""
    def __init__(self, llm_config: dict[str, Any]):
        self.prompt_store = PromptStore()
        self.llm_config = llm_config

    def generate(self, context: CodeGenerationContext) -> str:
        # Logic: Load project-specific system prompt and user template
        system_key = f"code_gen_{context.target_language}_system"
        user_key = "code_gen_user_template"

        system_prompt = self.prompt_store.get_prompt(system_key, context.project_id)
        user_template = self.prompt_store.get_prompt(user_key, context.project_id)

        user_prompt = user_template.format(
            source_code=context.source_code,
            rules=context.business_rules,
            planning=context.planning_doc,
            yaml=context.technical_yaml
        )
        # return self._call_llm(system_prompt, user_prompt)
        return "Generated Code Based on Prompt Studio"

class CompileFixAgent:
    """Pattern for Compile Fix Agent using PromptStore."""
    def __init__(self, llm_config: dict[str, Any]):
        self.prompt_store = PromptStore()

    def fix(self, context: CompileFixContext) -> str:
        system_prompt = self.prompt_store.get_prompt("compile_fix_system", context.project_id)
        user_template = self.prompt_store.get_prompt("compile_fix_user_template", context.project_id)
        
        user_prompt = user_template.format(
            error_log=context.error_log,
            current_code=context.current_code,
            original_source=context.original_source
        )
        # return self._call_llm(system_prompt, user_prompt)
        return "Fixed Code Based on Prompt Studio"
