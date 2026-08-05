from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any
import requests

from Agents.infrastructure.prompt_store import PromptStore

class AgenticCodeConversionOrchestrator:
    """
    ORCHESTRATOR: Owns the end-to-end code conversion pipeline.
    
    Instead of using hardcoded prompts, it uses Generic Blueprints from the PromptStore
    and injects language-specific constraints and project context.
    """

    def __init__(self, llm_config: dict[str, Any]):
        self.llm_config = llm_config or {}
        self.prompt_store = PromptStore()

    def convert(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        The main entry point for converting source code to target language.
        """
        # 1. Context Normalization
        target_lang = self._normalize_target_language(context.get("target_language"))
        project_id = context.get("project_id", "default")
        agent_key = self._select_agent(target_lang)

        try:
            # 2. Orchestrated LLM Call
            result = self._convert_with_agent(context=context, agent_key=agent_key, project_id=project_id)
            
            # Add metadata
            result["agent_key"] = agent_key
            result["agent_name"] = self._agent_name(agent_key)
            result["fallback_used"] = False
            
            # 3. Final Normalization & Semantic Validation
            normalized = self._normalize_result(result, context, agent_key)
            self._assert_semantic_completeness(normalized, context)
            
            return normalized

        except Exception as exc:
            # 4. Deterministic Fallback (The safety net)
            fallback = self._deterministic_fallback(
                context=context,
                agent_key=agent_key,
                reason=str(exc),
            )
            fallback["agent_key"] = "generic"
            fallback["agent_name"] = self._agent_name("generic")
            fallback["fallback_used"] = True
            fallback["fallback_reason"] = str(exc)
            return self._normalize_result(fallback, context, "generic")

    def _convert_with_agent(self, context: dict[str, Any], agent_key: str, project_id: str) -> dict[str, Any]:
        """
        Orchestrates the prompt by combining a system blueprint 
        with a rendered user template.
        """
        # A. Fetch Blueprints from PromptStore
        # We use 'gen_system' and 'gen_user' as generic blueprints
        system_prompt = self.prompt_store.get_prompt("gen_system", project_id)
        user_template = self.prompt_store.get_prompt("gen_user", project_id)

        # B. Define Token Budgets based on LLM type (Local vs Cloud)
        budgets = self._prompt_budgets()

        # C. Orchestrate the User Prompt
        # We inject all project-specific data into the generic template
        user_prompt = self.prompt_store.render(user_template, {
            "target_language": context.get("target_language", ""),
            "target_framework": context.get("target_framework", ""),
            "agent_key": agent_key,
            "file_id": context.get("file_id", ""),
            "file_name": context.get("file_name", ""),
            "source_language": context.get("source_language", ""),
            "conversion_plan": self._trim_json(context.get("conversion_plan"), budgets["conversion_plan"]),
            "technical_yaml": self._trim(context.get("technical_yaml"), budgets["technical_yaml"]),
            "business_rules_json": self._trim_json(context.get("business_rules"), budgets["business_rules"]),
            "procedural_flow_json": self._trim_json(context.get("procedural_flow"), budgets["procedural_flow"]),
            "dependencies_json": self._trim_json(context.get("dependencies"), budgets["dependencies"]),
            "locked_symbols_json": self._trim_json(context.get("locked_symbols"), budgets["locked_symbols"]),
            "source_code": self._trim(context.get("source_code"), budgets["source_code"]),
        })

        # D. Execution
        response = self._call_llm(system_prompt, user_prompt)
        return self._parse_json(response)

    # ===========================================================================
    # LLM COMMUNICATION LAYER
    # ===========================================================================

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        mode = (self.llm_config.get("mode") or self.llm_config.get("provider") or "local").lower()
        base_url = (self.llm_config.get("url") or self.llm_config.get("base_url") or "http://127.0.0.1:11434")
        model = (self.llm_config.get("model") or self.llm_config.get("llm_model") or "llama3")
        api_key = (self.llm_config.get("key") or self.llm_config.get("api_key"))
        
        # Determine timeout
        local_like = mode == "local" or "127.0.0.1" in base_url or "localhost" in base_url
        timeout = int(self.llm_config.get("timeout") or (90 if local_like else 180))

        if mode in {"openrouter", "api", "cloud", "custom", "local"} and "/v1" in base_url:
            return self._call_openai_compatible(base_url, model, api_key, system_prompt, user_prompt, timeout)

        # Ollama Native
        response = requests.post(
            f"{base_url.rstrip('/')}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                "stream": False, "options": {"temperature": 0.1},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "")

    def _call_openai_compatible(self, base_url, model, api_key, system_prompt, user_prompt, timeout) -> str:
        headers = {"Content-Type": "application/json"}
        # Use provided API key when available (OpenAI-compatible services expect 'Authorization: Bearer <key>').
        if api_key:
            key_str = str(api_key).strip()
            if key_str.lower().startswith("bearer "):
                headers["Authorization"] = key_str
            else:
                headers["Authorization"] = f"Bearer {key_str}"
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.1,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"} # Standard OpenAI JSON mode
        }
        response = requests.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    # ===========================================================================
    # UTILITIES & NORMALIZATION
    # ===========================================================================

    def _select_agent(self, target_language: str) -> str:
        target = self._normalize_target_language(target_language)
        return target if target in {"java", "python", "csharp"} else "generic"

    def _agent_name(self, agent_key: str) -> str:
        return f"{agent_key.title()}ConversionAgent"

    def _normalize_target_language(self, value: Any) -> str:
        text = str(value or "").lower().strip()
        if text in {"python", "py", "fastapi"}: return "python"
        if text in {"csharp", "c#", "cs", "dotnet", "aspnet", ".net"}: return "csharp"
        if text in {"java", "quarkus"}: return "java"
        return text or "java"

    def _parse_json(self, text: str) -> dict[str, Any]:
        raw = str(text or "").strip()
        raw = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE)
        try:
            return json.loads(raw)
        except Exception:
            match = re.search(r"(\{.*\}", raw, flags=re.DOTALL)
            if match: return json.loads(match.group(0))
        raise ValueError(f"Invalid JSON response: {raw[:500]}")

    def _normalize_result(self, payload: dict[str, Any], context: dict[str, Any], agent_key: str) -> dict[str, Any]:
        files = payload.get("files") if isinstance(payload, dict) else []
        normalized_files = []
        for item in (files if isinstance(files, list) else []):
            if not isinstance(item, dict): continue
            content = str(item.get("content") or "").strip()
            normalized_files.append({
                "file_path": str(item.get("file_path") or item.get("path") or "").replace("\\", "/"),
                "file_type": item.get("file_type", "other"),
                "language": self._normalize_target_language(item.get("language") or context.get("target_language")),
                "content": self._strip_code_fences(content),
                "description": str(item.get("description") or ""),
                "source_references": item.get("source_references", []) if isinstance(item.get("source_references"), list) else [],
            })

        return {
            "target_language": self._normalize_target_language(context.get("target_language")),
            "files": normalized_files,
            "summary": str(payload.get("summary") or ""),
            "warnings": payload.get("warnings", []),
            "unresolved_items": payload.get("unresolved_items", []),
            "agent_key": agent_key
        }

    def _assert_semantic_completeness(self, result: dict[str, Any], context: dict[str, Any]) -> None:
        """
        Ensures the LLM didn't skip critical literals or logic.
        This is the 'Quality Gate'.
        """
        content = "\n".join([f.get("content", "") for f in result.get("files", [])])
        source = str(context.get("source_code") or "").upper()
        content_upper = content.upper()
        
        # Check for missing critical literals from source in generated code
        literals = re.findall(r"['\"]([^'\"]{2,50})['\"]", str(context.get("source_code") or ""))
        missing = [l for l in literals if l.upper() not in content_upper]
        
        if len(missing) > 10: # Threshold for warning
             print(f"Warning: Semantic gap detected. Missing {len(missing)} source literals.")

    def _strip_code_fences(self, content: str) -> str:
        return re.sub(r"^```[a-zA-Z0-9_+-]*\s*|\s*```$", "", content, flags=re.MULTILINE).strip()

    def _trim(self, text: Any, max_chars: int) -> str:
        v = str(text or "")
        return v if len(v) <= max_chars else v[:max_chars] + "\n...[TRUNCATED]..."

    def _trim_json(self, value: Any, max_chars: int) -> str:
        try:
            text = json.dumps(value or {}, indent=2, ensure_ascii=False)
        except: text = str(value or "")
        return self._trim(text, max_chars)

    def _prompt_budgets(self) -> dict[str, int]:
        # Dynamic budget based on local vs cloud
        is_local = "localhost" in str(self.llm_config.get("url", "")) or self.llm_config.get("mode") == "local"
        if is_local:
            return {
                "conversion_plan": 2400,
                "technical_yaml": 3200,
                "business_rules": 2200,
                "procedural_flow": 2200,
                "dependencies": 1200,
                "locked_symbols": 800,
                "source_code": 7000,
            }
        return {
            "conversion_plan": 9000,
            "technical_yaml": 12000,
            "business_rules": 8000,
            "procedural_flow": 8000,
            "dependencies": 4000,
            "locked_symbols": 2000,
            "source_code": 16000,
        }

    def _deterministic_fallback(self, context: dict[str, Any], agent_key: str, reason: str) -> dict[str, Any]:
        # Simplified fallback: creates a basic class shell if LLM fails
        file_name = context.get("file_name", "LegacyProgram")
        return {
            "files": [{"file_path": f"fallback_{file_name}.txt", "content": f"Fallback generated due to: {reason}", "file_type": "other"}],
            "summary": "Deterministic fallback triggered."
        }
