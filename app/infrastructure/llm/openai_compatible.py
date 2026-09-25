import httpx

from .base import LLMProvider, LLMResult


class OpenAICompatibleProvider(LLMProvider):
    """Provider for any OpenAI-compatible chat-completions endpoint."""

    name = "openai"

    def __init__(self, api_key, base_url="", model="gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def complete(self, messages, **kwargs):
        url = (
            (self.base_url + "/chat/completions")
            if self.base_url
            else "https://api.openai.com/v1/chat/completions"
        )
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.2),
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})
        return LLMResult(
            content=choice.get("content", ""),
            tokens_input=usage.get("prompt_tokens", 0),
            tokens_output=usage.get("completion_tokens", 0),
            model=data.get("model", self.model),
        )
