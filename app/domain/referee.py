"""The referee: an LLM model whose structured verdict is fenced by a guard."""


def clamp_score(verdict_score, blueprint):
    """Clamp a referee score to the scoring rules (min 0, max from scoring)."""
    scoring = (blueprint.get("dialogue") or {}).get("scoring") or []
    max_score = 0
    for rule in scoring:
        if rule.get("kind") == "criteria":
            max_score += int(rule.get("max", 0)) * len(rule.get("criteria", []))
        elif rule.get("kind") == "event":
            max_score = max(max_score, int(rule.get("points", 0)))
    try:
        score = int(verdict_score)
    except (TypeError, ValueError):
        score = 0
    return max(0, min(score, max_score))


class Verdict:
    def __init__(self, accepted, score, explanation):
        self.accepted = bool(accepted)
        self.score = score
        self.explanation = explanation or ""

    def to_dict(self):
        return {
            "accepted": self.accepted,
            "score": self.score,
            "explanation": self.explanation,
        }


class Referee:
    """Wraps an LLM provider + model/parameters and returns guarded verdicts."""

    def __init__(self, provider, model, params=None):
        self.provider = provider
        self.model = model
        self.params = params or {}

    def evaluate(self, blueprint, action, state, round_messages, mock_output=None):
        from .prompts import build_referee_prompt

        messages = build_referee_prompt(blueprint, action, state, round_messages)
        result = self.provider.complete(
            messages, model=self.model, mock_output=mock_output, **self.params
        )
        raw = result.content
        parsed = result.parse_json(default={})
        return raw, parsed, result


def apply_guard(blueprint, parsed):
    """Validate and clamp a parsed referee verdict; returns a Verdict (never None)."""
    if not isinstance(parsed, dict):
        return Verdict(False, 0, "Invalid verdict format.")
    accepted = parsed.get("accepted")
    if not isinstance(accepted, bool):
        accepted = False
    score = clamp_score(parsed.get("score"), blueprint)
    explanation = str(parsed.get("explanation", ""))
    return Verdict(accepted, score, explanation)
