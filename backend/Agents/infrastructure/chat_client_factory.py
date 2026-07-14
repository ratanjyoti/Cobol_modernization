class LocalFallbackChatClient:
    def generate(self, system_prompt, user_prompt):
        return "[]"


from Agents.infrastructure.llm_api_client import OpenRouterClient


class ChatClientFactory:
    @staticmethod
    def get_client(provider: str, api_key: str = None):
        provider_name = (provider or "local").lower()
        if provider_name == "openrouter":
            return OpenRouterClient(api_key=api_key)
        if provider_name in {"local", "fallback"}:
            return LocalFallbackChatClient()
        raise ValueError(f"Unsupported provider: {provider}")
