from Agents.infrastructure.llm_api_client import LocalLLMClient, OpenRouterClient
from Config.llm_config import settings


class ChatClientFactory:
    @staticmethod
    def get_client(provider_or_config=None, api_key: str = None, base_url: str = None, model: str = None):
        config = ChatClientFactory._normalize_config(provider_or_config, api_key, base_url, model)
        mode = (config.get("mode") or config.get("provider") or "local").lower()

        if mode in {"local", "ollama"}:
            return LocalLLMClient(
                base_url=config.get("url") or config.get("base_url") or "http://localhost:11434",
                model=config.get("model") or "llama3",
            )

        if mode in {"custom", "api", "openrouter", "cloud"}:
            return OpenRouterClient(
                api_key=config.get("key") or settings.OPENROUTER_API_KEY,
                base_url=config.get("url") or config.get("base_url") or settings.OPENROUTER_BASE_URL,
                model=config.get("model") or settings.OPENROUTER_MODEL,
            )

        raise ValueError(f"Unsupported provider: {mode}")

    @staticmethod
    def _normalize_config(provider_or_config=None, api_key: str = None, base_url: str = None, model: str = None):
        if isinstance(provider_or_config, dict):
            return dict(provider_or_config)

        provider = (provider_or_config or "local")
        config = {"mode": provider, "provider": provider}
        if api_key:
            config["key"] = api_key
        if base_url:
            config["url"] = base_url
        if model:
            config["model"] = model
        return config
