try:
    import openai
except ImportError:
    openai = None

import requests

from Config.llm_config import settings


class LocalLLMClient:
    def __init__(self, base_url="http://localhost:11434", model="llama3"):
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model or "llama3"

    def generate(self, system_prompt, user_prompt, model=None):
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model or self.model,
                    "prompt": f"{system_prompt}\n\n{user_prompt}",
                    "stream": False,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as exc:
            print(f"Local LLM Error: {exc}")
            return ""


class OpenRouterClient:
    def __init__(self, api_key=None, base_url=None, model=None):
        if openai is None:
            raise RuntimeError("openai package is not installed")
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = base_url or settings.OPENROUTER_BASE_URL
        self.model = model or settings.OPENROUTER_MODEL
        if not self.api_key:
            raise RuntimeError("API key is not configured. Add an OpenRouter key in AI Configuration or backend/.env.")
        self.client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=45,
        )

    def generate(self, system_prompt, user_prompt, model=None):
        selected_model = model or self.model
        try:
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=1200,
                extra_headers={
                    "HTTP-Referer": "http://localhost:5173",
                    "X-Title": "ModernizerAI",
                },
            )
            return response.choices[0].message.content
        except Exception as exc:
            print(f"AI API Error: {exc}")
            return ""
