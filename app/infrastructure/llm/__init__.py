from flask import current_app

from . import registry
from .base import LLMProvider, LLMResult  # noqa: F401
from .mock import MockLLMProvider  # noqa: F401
from .openai_compatible import OpenAICompatibleProvider  # noqa: F401

_REGISTRY_KEY = "llm_registry"


def get_registry():
    """Return the cached provider registry ({id: ProviderSpec})."""
    if _REGISTRY_KEY not in current_app.extensions:
        current_app.extensions[_REGISTRY_KEY] = registry.build_registry(
            current_app.config
        )
    return current_app.extensions[_REGISTRY_KEY]


def get_provider(provider_id):
    spec = get_registry().get(provider_id)
    return spec.provider if spec else None


def resolve_model(model_ref):
    """Resolve a model reference into (provider_instance, model_name)."""
    reg = get_registry()
    return registry.resolve_model(
        reg,
        model_ref,
        default_provider=current_app.config.get("DEFAULT_PROVIDER", "mock"),
        default_model=current_app.config.get("DEFAULT_MODEL", "mock-model"),
    )


def provider_ids():
    return registry.provider_ids(get_registry())


def models_for(provider_id):
    return registry.models_for(get_registry(), provider_id)
