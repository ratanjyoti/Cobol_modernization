try:
    import openai
except ImportError:
    openai = None

from Config.llm_config import settings


class OpenRouterClient:
    def __init__(self, api_key=None):
        if openai is None:
            raise RuntimeError("openai package is not installed")
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")
        self.client = openai.OpenAI(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=self.api_key,
            timeout=45,
        )

    def generate(self, system_prompt, user_prompt, model=None):
        selected_model = model or settings.OPENROUTER_MODEL
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
                    "X-Title": "ModernizerAI Business Logic Extraction",
                },
            )
            return response.choices[0].message.content
        except Exception as exc:
            print(f"API Error: {exc}")
            return ""
