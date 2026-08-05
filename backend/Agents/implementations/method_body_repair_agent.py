# Agents/implementations/method_body_repair_agent.py

import json
import re
from typing import Any
from Agents.infrastructure.prompt_store import PromptStore

class MethodBodyRepairAgent:
    """
    ORCHESTRATOR: Manages method repair by combining 
    Generic Blueprints from PromptStore with Language-Specific Rules.
    """

    # Only these rules change per language. The Prompt logic remains constant.
    LANGUAGE_RULES = {
        "java": {
            "name": "Java",
            "body_instruction": "Return Java statements only. No method signature, no enclosing braces.",
            "bad_patterns": [r"return\s+true\s*;", r"UnsupportedOperationException", r"\bTODO\b"],
        },
        "python": {
            "name": "Python",
            "body_instruction": "Return Python statements only. No def line. Use correct indentation.",
            "bad_patterns": [r"\bpass\b", r"return\s+None\b", r"NotImplementedError", r"\bTODO\b"],
        },
        "csharp": {
            "name": "C#",
            "body_instruction": "Return C# statements only. No method signature, no enclosing braces.",
            "bad_patterns": [r"return\s+true\s*;", r"NotImplementedException", r"\bTODO\b"],
        },
    }

    def __init__(self, llm_config: dict, prompt_store: PromptStore | None = None):
        self.llm_config = llm_config or {}
        self.prompt_store = prompt_store or PromptStore()

    def repair_method_body(self, file_path: str, class_name: str, method_name: str, 
                           method_header: str, current_body: str, source_evidence: str, 
                           business_rules: list[dict[str, Any]], locked_symbols: dict[str, Any], 
                           target_language: str = "java", project_id: str = "default") -> dict[str, Any]:
        
        target = self._normalize_target(target_language)
        rules = self.LANGUAGE_RULES.get(target, self.LANGUAGE_RULES["java"])

        # 1. Fetch Generic Blueprints
        system_prompt = self.prompt_store.get_prompt("method_repair_system", project_id)
        user_template = self.prompt_store.get_prompt("method_repair_user", project_id)

        # 2. Orchestrate: Inject Language Personality into the Blueprint
        user_prompt = self.prompt_store.render(user_template, {
            "lang_name": rules["name"],
            "body_instruction": rules["body_instruction"],
            "file_path": file_path,
            "class_name": class_name,
            "method_name": method_name,
            "method_header": method_header,
            "current_body": current_body,
            "source_evidence": source_evidence,
            "business_rules": json.dumps(business_rules[:20], indent=2),
            "locked_symbols": json.dumps(self._trim_locked_symbols(locked_symbols), indent=2),
        })

        response_text = self._call_llm(system_prompt, user_prompt)
        payload = self._parse_json(response_text)

    
        replacement_body = str(payload.get("replacement_body") or "").strip()

        if not replacement_body:
            raise ValueError(f"LLM returned empty replacement body for {method_name}")

        if self._is_comment_only_or_placeholder(replacement_body, target):
            raise ValueError(
                f"LLM returned weak/comment-only/placeholder replacement body for {method_name}"
            )

        return {
            "method_name": method_name,
            "replacement_body": str(payload.get("replacement_body") or "").strip(),
            "warnings": payload.get("warnings") or [],
            "target_language": target,
        }

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        mode = (
            self.llm_config.get("mode")
            or self.llm_config.get("provider")
            or "local"
        ).lower()

        if mode in {"openrouter", "api", "custom", "cloud"}:
            return self._call_openrouter(system_prompt, user_prompt)

        return self._call_local(system_prompt, user_prompt)

    def _call_openrouter(self, system_prompt: str, user_prompt: str) -> str:
        import requests

        api_key = self.llm_config.get("key")
        base_url = self.llm_config.get("url") or "https://openrouter.ai/api/v1"
        model = self.llm_config.get("model")

        if not api_key:
            raise ValueError("Missing API key for method body repair.")

        if not model:
            raise ValueError("Missing model for method body repair.")

        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            },
            timeout=120,
        )

        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"]

    def _call_local(self, system_prompt: str, user_prompt: str) -> str:
        import requests

        base_url = self.llm_config.get("url") or "http://localhost:11434"
        model = self.llm_config.get("model") or "llama3"

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
            timeout=180,
        )

        response.raise_for_status()
        data = response.json()

        return data.get("message", {}).get("content", "")

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = str(text or "").strip()

        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except Exception:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match:
                return json.loads(match.group(0))

        raise ValueError(f"Could not parse method repair JSON: {cleaned[:500]}")

    def _is_comment_only_or_placeholder(self, body: str, target_language: str) -> bool:
        target = self._normalize_target(target_language)
        text = str(body or "")

        for pattern in self.LANGUAGE_RULES[target]["bad_patterns"]:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True

        cleaned = self._remove_comments_and_blank_lines(text, target)

        if not cleaned.strip():
            return True

        executable_patterns = {
            "java": [
                r"\bif\s*\(",
                r"\bfor\s*\(",
                r"\bwhile\s*\(",
                r"\breturn\b",
                r"\bthrow\b",
                r"\bnew\b",
                r"=",
                r"\.\w+\s*\(",
            ],
            "python": [
                r"\bif\s+",
                r"\bfor\s+",
                r"\bwhile\s+",
                r"\breturn\b",
                r"\braise\b",
                r"=",
                r"\.\w+\s*\(",
                r"\w+\s*\(",
            ],
            "csharp": [
                r"\bif\s*\(",
                r"\bfor\s*\(",
                r"\bforeach\s*\(",
                r"\bwhile\s*\(",
                r"\breturn\b",
                r"\bthrow\b",
                r"\bnew\b",
                r"=",
                r"\.\w+\s*\(",
                r"\bawait\b",
            ],
        }

        return not any(
            re.search(pattern, cleaned)
            for pattern in executable_patterns.get(target, [])
        )

    def _remove_comments_and_blank_lines(
        self,
        text: str,
        target_language: str,
    ) -> str:
        target = self._normalize_target(target_language)

        if target in {"java", "csharp"}:
            text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

            lines = []
            for line in text.splitlines():
                stripped = line.strip()

                if not stripped:
                    continue

                if stripped.startswith("//"):
                    continue

                stripped = re.sub(r"//.*$", "", stripped).strip()

                if stripped:
                    lines.append(stripped)

            return "\n".join(lines)

        lines = []
        for line in text.splitlines():
            stripped = line.strip()

            if not stripped:
                continue

            if stripped.startswith("#"):
                continue

            stripped = re.sub(r"#.*$", "", stripped).strip()

            if stripped:
                lines.append(stripped)

        return "\n".join(lines)

    def _trim_locked_symbols(self, locked_symbols: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(locked_symbols, dict):
            return {}

        trimmed = dict(locked_symbols)

        for key in ["type_mappings", "signatures"]:
            value = trimmed.get(key)

            if isinstance(value, list) and len(value) > 40:
                trimmed[key] = value[:40]
                trimmed[f"{key}_truncated"] = True

        return trimmed

    def _normalize_target(self, target_language: str) -> str:
        value = str(target_language or "").lower().strip()

        if value in {"python", "py", "fastapi"}:
            return "python"

        if value in {"csharp", "c#", "cs", "dotnet"}:
            return "csharp"

        return "java"