import json

from .base import LLMProvider, LLMResult


class MockLLMProvider(LLMProvider):
    """Deterministic, offline provider used for demos and tests.

    The dialogue runner passes the deterministic output it wants via the
    ``mock_output`` keyword, and this provider echoes it back as JSON. This lets
    the full crew dialogue run reproducibly without any external LLM.
    """

    name = "mock"

    def complete(self, messages, **kwargs):
        output = kwargs.get("mock_output")
        if output is None:
            output = {"message": ""}
        content = json.dumps(output)
        return LLMResult(
            content=content,
            tokens_input=kwargs.get("tokens_input", 0),
            tokens_output=len(content) // 4,
            model=kwargs.get("model", "mock-model"),
        )
