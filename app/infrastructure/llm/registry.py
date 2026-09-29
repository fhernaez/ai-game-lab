"""LLM provider registry.

Builds a set of named providers from configuration and resolves a model
reference (either "provider:model" or a bare model name) into a
(provider, model) pair.

Providers are configured via the ``LLM_PROVIDERS`` JSON environment variable;
the ``mock`` provider is always available offline.
"""

from dataclasses import dataclass, field

from .base import LLMProvider
from .mock import MockLLMProvider
from .openai_compatible import OpenAICompatibleProvider

MOCK_MODELS = ["mock-model"]


@dataclass
class ProviderSpec:
    provider: LLMProvider
    models: list = field(default_factory=list)


def build_registry(config):
    registry = {}
    registry["mock"] = ProviderSpec(MockLLMProvider(), list(MOCK_MODELS))

    entries = config.get("LLM_PROVIDERS") or []

    # Backward compatibility: if no registry is configured but the legacy
    # single-provider variables point at OpenAI, synthesize one entry.
    if not entries and config.get("LLM_PROVIDER") == "openai":
        entries = [
            {
                "id": "openai",
                "type": "openai",
                "base_url": config.get("LLM_BASE_URL", ""),
                "api_key": config.get("LLM_API_KEY", ""),
                "models": [config.get("LLM_MODEL", "gpt-4o-mini")],
            }
        ]

    for entry in entries:
        provider_id = entry.get("id")
        if not provider_id:
            raise RuntimeError("Each LLM_PROVIDERS entry needs an 'id'.")
        provider_type = entry.get("type", "openai")
        models = entry.get("models") or []

        if provider_type == "openai":
            provider = OpenAICompatibleProvider(
                api_key=entry.get("api_key", ""),
                base_url=entry.get("base_url", ""),
                model=models[0] if models else "gpt-4o-mini",
            )
        elif provider_type == "mock":
            provider = MockLLMProvider()
            models = models or list(MOCK_MODELS)
        else:
            raise RuntimeError(f"Unknown LLM provider type: {provider_type!r}")

        registry[provider_id] = ProviderSpec(provider, models)

    return registry


def resolve_model(registry, model_ref, default_provider="mock", default_model="mock-model"):
    """Resolve a model reference into (provider_instance, model_name)."""
    if not model_ref:
        model_ref = f"{default_provider}:{default_model}"

    if ":" in model_ref:
        provider_id, _, model = model_ref.partition(":")
        spec = registry.get(provider_id)
        if spec is None:
            spec = registry.get("mock")
            model = "mock-model"
        return spec.provider, model

    # Bare model name -> use the default provider.
    spec = registry.get(default_provider) or registry.get("mock")
    return spec.provider, model_ref


def provider_ids(registry):
    return list(registry.keys())


def models_for(registry, provider_id):
    spec = registry.get(provider_id)
    return list(spec.models) if spec else []
