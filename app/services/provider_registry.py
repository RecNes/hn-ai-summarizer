"""Provider registry for AI services.

Defines all supported AI providers, their types, default base URLs,
and which environment variable holds their API key.
"""

from typing import Any, Dict, List, Optional
from app.core.config import settings


# Provider definitions
# type: "openai-compat" → uses openai SDK with custom base_url
#       "anthropic"     → uses anthropic SDK
#       "ollama-http"   → uses raw HTTP to Ollama API
PROVIDERS: Dict[str, Dict[str, Any]] = {
    "openai": {
        "name": "OpenAI",
        "type": "openai-compat",
        "base_url": "https://api.openai.com/v1",
        "configurable_url": False,
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "name": "Anthropic",
        "type": "anthropic",
        "base_url": None,
        "configurable_url": False,
        "env_key": "ANTHROPIC_API_KEY",
    },
    "deepseek": {
        "name": "DeepSeek",
        "type": "openai-compat",
        "base_url": "https://api.deepseek.com/v1",
        "configurable_url": False,
        "env_key": "DEEPSEEK_API_KEY",
    },
    "openrouter": {
        "name": "OpenRouter",
        "type": "openai-compat",
        "base_url": "https://openrouter.ai/api/v1",
        "configurable_url": False,
        "env_key": "OPENROUTER_API_KEY",
    },
    "lmstudio": {
        "name": "LM Studio",
        "type": "openai-compat",
        "base_url": "http://localhost:1234/v1",
        "configurable_url": True,
        "env_key": None,  # local, no key needed
    },
    "ollama": {
        "name": "Ollama",
        "type": "ollama-http",
        "base_url": "http://localhost:11434",
        "configurable_url": True,
        "env_key": None,  # local, no key needed
    },
}


def get_provider(provider_id: str) -> Optional[Dict[str, Any]]:
    """Get provider configuration by ID."""
    return PROVIDERS.get(provider_id)


def get_available_providers() -> List[Dict[str, Any]]:
    """Return list of providers that have their API key configured (or are local).

    Each entry: {id, name, has_key, config_required}
    """
    result = []
    for provider_id, config in PROVIDERS.items():
        env_key = config.get("env_key")
        has_key: bool = True

        if env_key:
            # Check if the env variable is set and non-empty
            env_value = getattr(settings, env_key, None)
            has_key = bool(env_value and str(env_value).strip())

        result.append({
            "id": provider_id,
            "name": config["name"],
            "has_key": has_key,
            "config_required": config.get("configurable_url", False),
        })

    return result