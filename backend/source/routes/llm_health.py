import time
import httpx
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/llm-health", tags=["LLM Health"])


class LocalLLMCheckRequest(BaseModel):
    provider: str = "auto"
    model: str
    base_url: str = "http://localhost:11434"


class LocalLLMCheckResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ok: bool
    provider: str
    model: str
    status: str
    message: str
    model_installed: bool = False
    server_reachable: bool = False
    latency_ms: int | None = None
    sample_output: str | None = None
    error_detail: str | None = None


def openai_base_url(base_url: str) -> str:
    return base_url if base_url.endswith("/v1") else f"{base_url}/v1"


def parse_openai_output(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return (message.get("content") or choices[0].get("text") or "").strip()


async def check_ollama(client: httpx.AsyncClient, model: str, base_url: str, started: float) -> LocalLLMCheckResponse:
    tags_response = await client.get(f"{base_url}/api/tags")
    if tags_response.status_code != 200:
        return LocalLLMCheckResponse(
            ok=False,
            provider="ollama",
            model=model,
            status="SERVER_ERROR",
            message="Ollama endpoint is reachable but returned an error.",
            server_reachable=True,
            error_detail=f"GET {base_url}/api/tags returned HTTP {tags_response.status_code}: {tags_response.text[:1000]}",
        )

    tags_data = tags_response.json()
    installed_models = [
        item.get("name") or item.get("model")
        for item in tags_data.get("models", [])
        if item.get("name") or item.get("model")
    ]

    if model not in installed_models:
        installed = ", ".join(installed_models) if installed_models else "none"
        return LocalLLMCheckResponse(
            ok=False,
            provider="ollama",
            model=model,
            status="MODEL_NOT_FOUND",
            message=f"Model '{model}' is not installed on this machine.",
            server_reachable=True,
            model_installed=False,
            error_detail=f"Installed models: {installed}",
        )

    generate_response = await client.post(
        f"{base_url}/api/generate",
        json={
            "model": model,
            "prompt": "Reply with exactly: OK",
            "stream": False,
            "options": {"temperature": 0, "num_predict": 8},
        },
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    if generate_response.status_code != 200:
        return LocalLLMCheckResponse(
            ok=False,
            provider="ollama",
            model=model,
            status="GENERATION_FAILED",
            message="The model is installed but failed to generate output.",
            server_reachable=True,
            model_installed=True,
            latency_ms=latency_ms,
            error_detail=generate_response.text[:1000],
        )

    output = (generate_response.json().get("response") or "").strip()
    if not output:
        return LocalLLMCheckResponse(
            ok=False,
            provider="ollama",
            model=model,
            status="EMPTY_OUTPUT",
            message="The model responded, but the output was empty.",
            server_reachable=True,
            model_installed=True,
            latency_ms=latency_ms,
            sample_output="",
            error_detail="Ollama returned an empty response field.",
        )

    return LocalLLMCheckResponse(
        ok=True,
        provider="ollama",
        model=model,
        status="READY",
        message=f"Local model '{model}' is available and generated output successfully.",
        server_reachable=True,
        model_installed=True,
        latency_ms=latency_ms,
        sample_output=output[:500],
    )


async def check_openai_compatible(client: httpx.AsyncClient, model: str, base_url: str, started: float) -> LocalLLMCheckResponse:
    api_base = openai_base_url(base_url)
    models_response = await client.get(f"{api_base}/models")
    if models_response.status_code != 200:
        return LocalLLMCheckResponse(
            ok=False,
            provider="openai-compatible",
            model=model,
            status="SERVER_ERROR",
            message="Local OpenAI-compatible endpoint is reachable but the model list failed.",
            server_reachable=True,
            error_detail=f"GET {api_base}/models returned HTTP {models_response.status_code}: {models_response.text[:1000]}",
        )

    models_data = models_response.json()
    installed_models = [
        item.get("id") or item.get("name")
        for item in models_data.get("data", [])
        if item.get("id") or item.get("name")
    ]

    if model not in installed_models:
        installed = ", ".join(installed_models) if installed_models else "none"
        return LocalLLMCheckResponse(
            ok=False,
            provider="openai-compatible",
            model=model,
            status="MODEL_NOT_FOUND",
            message=f"Model '{model}' is not available from the local server.",
            server_reachable=True,
            model_installed=False,
            error_detail=f"Available models: {installed}",
        )

    chat_response = await client.post(
        f"{api_base}/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "temperature": 0,
            "max_tokens": 8,
            "stream": False,
        },
    )
    latency_ms = int((time.perf_counter() - started) * 1000)

    if chat_response.status_code != 200:
        return LocalLLMCheckResponse(
            ok=False,
            provider="openai-compatible",
            model=model,
            status="GENERATION_FAILED",
            message="The model is available but failed to generate output.",
            server_reachable=True,
            model_installed=True,
            latency_ms=latency_ms,
            error_detail=chat_response.text[:1000],
        )

    output = parse_openai_output(chat_response.json())
    if not output:
        return LocalLLMCheckResponse(
            ok=False,
            provider="openai-compatible",
            model=model,
            status="EMPTY_OUTPUT",
            message="The model responded, but the output was empty.",
            server_reachable=True,
            model_installed=True,
            latency_ms=latency_ms,
            sample_output="",
            error_detail="The local server returned no chat completion text.",
        )

    return LocalLLMCheckResponse(
        ok=True,
        provider="openai-compatible",
        model=model,
        status="READY",
        message=f"Local model '{model}' is available and generated output successfully.",
        server_reachable=True,
        model_installed=True,
        latency_ms=latency_ms,
        sample_output=output[:500],
    )


@router.post("/local/check", response_model=LocalLLMCheckResponse)
async def check_local_llm(payload: LocalLLMCheckRequest):
    provider = (payload.provider or "auto").lower().strip()
    model = (payload.model or "").strip()
    base_url = (payload.base_url or "http://localhost:11434").rstrip("/")

    if provider in {"lmstudio", "lm-studio", "openai", "openai-compatible", "custom"}:
        provider = "openai-compatible"

    if provider not in {"auto", "ollama", "openai-compatible"}:
        return LocalLLMCheckResponse(
            ok=False,
            provider=provider,
            model=model,
            status="UNSUPPORTED_PROVIDER",
            message="Unsupported local LLM provider. Use auto, Ollama, or OpenAI-compatible.",
            error_detail=f"Unsupported provider: {provider}",
        )

    if not model:
        return LocalLLMCheckResponse(
            ok=False,
            provider=provider,
            model=model,
            status="MODEL_REQUIRED",
            message="Please select or enter a local model name.",
            error_detail="Model name is empty.",
        )

    started = time.perf_counter()
    timeout = httpx.Timeout(connect=4.0, read=45.0, write=8.0, pool=4.0)
    errors: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if provider == "ollama":
                return await check_ollama(client, model, base_url, started)

            if provider == "openai-compatible":
                return await check_openai_compatible(client, model, base_url, started)

            try:
                ollama_result = await check_ollama(client, model, base_url, started)
                if ollama_result.ok or ollama_result.status in {"MODEL_NOT_FOUND", "GENERATION_FAILED", "EMPTY_OUTPUT"}:
                    return ollama_result
            except Exception as exc:
                errors.append(f"Ollama check failed: {type(exc).__name__}: {str(exc)[:300]}")

            try:
                return await check_openai_compatible(client, model, base_url, started)
            except Exception as exc:
                errors.append(f"OpenAI-compatible check failed: {type(exc).__name__}: {str(exc)[:300]}")
                raise

    except httpx.ConnectError as exc:
        return LocalLLMCheckResponse(
            ok=False,
            provider=provider,
            model=model,
            status="SERVER_NOT_RUNNING",
            message="The local LLM server is not running or cannot be reached from the backend.",
            server_reachable=False,
            model_installed=False,
            error_detail="\n".join(errors + [str(exc)]),
        )
    except httpx.TimeoutException as exc:
        return LocalLLMCheckResponse(
            ok=False,
            provider=provider,
            model=model,
            status="TIMEOUT",
            message="The local LLM did not respond before timeout.",
            server_reachable=False,
            model_installed=False,
            error_detail="\n".join(errors + [str(exc)]),
        )
    except Exception as exc:
        return LocalLLMCheckResponse(
            ok=False,
            provider=provider,
            model=model,
            status="UNKNOWN_ERROR",
            message="Unexpected error while checking local LLM.",
            error_detail="\n".join(errors + [str(exc)]),
        )

