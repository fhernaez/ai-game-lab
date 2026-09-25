import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResult:
    content: str
    tokens_input: int = 0
    tokens_output: int = 0
    model: str = ""

    def parse_json(self, default=None):
        """Best-effort extraction of a JSON object from the model output."""
        if not self.content:
            return default
        text = self.content.strip()
        # Strip markdown fences if present.
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return default
        return default


class LLMProvider(ABC):
    name = "base"

    @abstractmethod
    def complete(self, messages, **kwargs) -> LLMResult:
        raise NotImplementedError
