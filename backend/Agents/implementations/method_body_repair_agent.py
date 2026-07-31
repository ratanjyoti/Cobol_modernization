import json
import re
from typing import Any

from Agents.infrastructure.prompt_store import PromptStore


class MethodBodyRepairAgent:
    """
    Repairs comment-only generated Java methods by asking the configured LLM
    to return only the executable replacement method body.
    """

    def __init__(self, llm_config: dict, prompt_store: PromptStore | None = None):
        self.llm_config = llm_config or {}
        self.prompt_store = prompt_store or PromptStore()

    def repair_method_body(
        self,
        file_path: str,
        class_name: str,
        method_name: str,
        method_header: str,
        current_body: str,
        source_evidence: str,
        business_rules: list[dict[str, Any]],
        locked_symbols: dict[str, Any],
    ) -> dict[str, Any]:
        system_prompt = """
You are a senior legacy modernization engineer.

You repair Java method bodies generated from COBOL/Telon logic.

Rules:
- Return valid JSON only.
- Do not return markdown.
- Do not return the full class.
- Return only the replacement method body, without the outer method signature.
- The body must contain executable Java statements.
- Do not return comments-only logic.
- Use locked symbol names when available.
- Preserve the business rule intent.
- If exact logic is uncertain, implement a safe deterministic equivalent and add a warning.
"""

        user_prompt = f"""
Repair this generated Java method.

File:
{file_path}

Class:
{class_name}

Method:
{method_name}

Method header:
{method_header}

Current bad body:
{current_body}

Source COBOL/Telon evidence:
{source_evidence}

Business rules:
{json.dumps(business_rules[:20], indent=2, ensure_ascii=False)}

Locked symbols:
{json.dumps(locked_symbols, indent=2, ensure_ascii=False)}

Return JSON in this exact shape:
{{
  "method_name": "{method_name}",
  "replacement_body": "Java statements only, no outer method signature",
  "warnings": []
}}
"""

        response_text = self._call_llm(system_prompt, user_prompt)

        payload = self._parse_json(response_text)

        replacement_body = str(payload.get("replacement_body") or "").strip()

        if not replacement_body:
            raise ValueError(f"LLM returned empty replacement body for {method_name}")

        if self._is_comment_only(replacement_body):
            raise ValueError(f"LLM returned comment-only replacement body for {method_name}")

        return {
            "method_name": method_name,
            "replacement_body": replacement_body,
            "warnings": payload.get("warnings") or [],
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

    def _is_comment_only(self, body: str) -> bool:
        text = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)

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

        cleaned = "\n".join(lines).strip()

        if not cleaned:
            return True

        executable_patterns = [
            r"\bif\s*\(",
            r"\bfor\s*\(",
            r"\bwhile\s*\(",
            r"\bswitch\s*\(",
            r"\breturn\b",
            r"\bthrow\b",
            r"\bnew\b",
            r"=",
            r"\.\w+\s*\(",
        ]

        return not any(re.search(pattern, cleaned) for pattern in executable_patterns)