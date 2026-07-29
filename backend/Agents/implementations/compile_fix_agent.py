import json
import re
from typing import Any

import requests

from Agents.infrastructure.constitution_loader import ConstitutionLoader
from Agents.infrastructure.prompt_store import PromptStore
from Config.llm_config import settings


class CompileFixAgent:
    """
    Fixes generated code using:
    - compiler/syntax error
    - current generated file content
    - conversion plan
    - technical YAML
    - business rules
    - target constitution
    - editable Prompt Studio compile-fix prompt
    """

    def __init__(
        self,
        llm_config: dict,
        prompt_store: PromptStore | None = None,
        constitution_loader: ConstitutionLoader | None = None,
    ):
        self.llm_config = llm_config or {}
        self.prompt_store = prompt_store or PromptStore()
        self.constitution_loader = constitution_loader or ConstitutionLoader()

    def fix_file(
        self,
        target_language: str,
        project_id: str,
        file_path: str,
        current_code: str,
        error_text: str,
        conversion_plan: dict[str, Any],
        technical_yaml: str,
        business_rules: list[dict[str, Any]],
    ) -> dict[str, Any]:
        profile = self.constitution_loader.load_profile(target_language)

        system_template = self.prompt_store.get_prompt(
            "compile_fix_system",
            project_id=project_id,
        )
        user_template = self.prompt_store.get_prompt(
            "compile_fix_user",
            project_id=project_id,
        )

        variables = {
            "constitution": ConstitutionLoader.to_prompt_block(profile),
            "file_path": file_path,
            "current_code": current_code,
            "error_text": error_text,
            "conversion_plan_json": json.dumps(conversion_plan, indent=2, ensure_ascii=False),
            "technical_yaml": technical_yaml,
            "business_rules_json": json.dumps(business_rules, indent=2, ensure_ascii=False),
        }

        system_prompt = self.prompt_store.render(system_template, variables)
        user_prompt = self.prompt_store.render(user_template, variables)

        response_text = self._call_llm(system_prompt, user_prompt)
        payload = self._parse_json(response_text)

        fixed_content = str(payload.get("content") or "").strip()

        if not fixed_content:
            raise RuntimeError("CompileFixAgent returned empty corrected content.")

        return {
            "path": str(payload.get("path") or file_path),
            "content": fixed_content,
            "fix_summary": str(payload.get("fix_summary") or "Generated file was corrected."),
            "warnings": list(payload.get("warnings") or []),
        }

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        mode = (
            self.llm_config.get("mode")
            or self.llm_config.get("provider")
            or "openrouter"
        ).lower()

        model = self.llm_config.get("model") or settings.OPENROUTER_MODEL

        if mode == "local":
            return self._call_local_llm(system_prompt, user_prompt, model)

        return self._call_openai_compatible(system_prompt, user_prompt, model)

    def _call_openai_compatible(self, system_prompt: str, user_prompt: str, model: str) -> str:
        api_key = self.llm_config.get("key") or settings.OPENROUTER_API_KEY
        base_url = (
            self.llm_config.get("url")
            or settings.OPENROUTER_BASE_URL
            or "https://openrouter.ai/api/v1"
        ).rstrip("/")

        if not api_key:
            raise RuntimeError("API key missing. Add OpenRouter API key in AI Configuration.")

        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://cobol-modernization-green.vercel.app",
                "X-Title": "ModernizerAI",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.05,
                "max_tokens": 8000,
            },
            timeout=120,
        )

        if response.status_code >= 400:
            raise RuntimeError(
                f"LLM compile-fix failed for model '{model}': {self._api_error_message(response)}"
            )

        content = (
            response.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )

        if not content:
            raise RuntimeError("LLM returned empty compile-fix response.")

        return content

    def _call_local_llm(self, system_prompt: str, user_prompt: str, model: str) -> str:
        base_url = (
            self.llm_config.get("url")
            or self.llm_config.get("base_url")
            or "http://localhost:11434"
        ).rstrip("/")

        local_provider = (
            self.llm_config.get("local_provider")
            or ("openai-compatible" if base_url.endswith("/v1") else "ollama")
        ).lower()

        if local_provider == "openai-compatible" or base_url.endswith("/v1"):
            api_base = base_url if base_url.endswith("/v1") else f"{base_url}/v1"

            response = requests.post(
                f"{api_base}/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.05,
                    "max_tokens": 8000,
                    "stream": False,
                },
                timeout=180,
            )

            if response.status_code >= 400:
                raise RuntimeError(
                    f"Local OpenAI-compatible compile-fix failed: {response.text[:500]}"
                )

            return (
                response.json()
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content")
                or ""
            )

        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": f"{system_prompt}\n\n{user_prompt}",
                "stream": False,
                "options": {
                    "temperature": 0.05,
                    "num_predict": 8000,
                },
            },
            timeout=180,
        )

        if response.status_code >= 400:
            raise RuntimeError(f"Ollama compile-fix failed: {response.text[:500]}")

        return response.json().get("response") or ""

    def _parse_json(self, text: str) -> dict[str, Any]:
        cleaned = self._strip_code_fence(text)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise RuntimeError(f"Could not parse compile-fix JSON: {cleaned[:500]}")

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        value = (text or "").strip()
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
        return value.strip()

    @staticmethod
    def _api_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500] or response.reason

        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or payload)[:500]
        if error:
            return str(error)[:500]
        return str(payload)[:500]