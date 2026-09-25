import json
import random

from .base import LLMProvider, LLMResult


class MockLLMProvider(LLMProvider):
    """Deterministic, offline provider used for demos and tests.

    It produces a plausible structured action based on the prompt payload,
    so the full runtime can be exercised without an API key. The action is
    chosen by an injected "expected_action" hint embedded in the prompt,
    with a seeded jitter so results are reproducible.
    """

    name = "mock"

    def complete(self, messages, **kwargs):
        action_hint = kwargs.get("action_hint")
        seed = kwargs.get("seed", 0)
        role = kwargs.get("role", "agent")
        actions = kwargs.get("allowed_actions", [])

        if action_hint:
            action = dict(action_hint)
        elif actions:
            rng = random.Random(seed)
            action = {"action": rng.choice(actions)}
        else:
            action = {"action": "NOOP"}

        # Optional message payload for communication turns.
        message = kwargs.get("message")
        if message:
            action["message"] = message

        content = json.dumps(action)
        return LLMResult(
            content=content,
            tokens_input=kwargs.get("tokens_input", 0),
            tokens_output=len(content) // 4,
            model=kwargs.get("model", "mock-model"),
        )
