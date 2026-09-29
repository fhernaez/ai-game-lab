"""Crew member and referee domain objects."""

PARAM_KEYS = [
    "temperature",
    "max_tokens",
    "top_p",
    "frequency_penalty",
    "presence_penalty",
    "stop",
    "response_format",
]


class CrewMember:
    """A crew member: role + speak order + model + full parameters."""

    def __init__(self, role, speak_order, is_speaker, config):
        self.role = role
        self.speak_order = speak_order
        self.is_speaker = is_speaker
        self.config = config or {}
        self.name = self.config.get("name") or role.title()
        self.model = self.config.get("model") or ""
        self.instructions = self.config.get("instructions") or ""

    @property
    def params(self):
        """Model parameters to pass through to the LLM provider."""
        params = {}
        for key in PARAM_KEYS:
            if key in self.config and self.config[key] is not None:
                params[key] = self.config[key]
        return params

    @property
    def skills(self):
        return self.config.get("selected_skills") or self.config.get("skills") or []


class Crew:
    """A crew (team of LLM agents) owned by one player."""

    def __init__(self, name, members, instructions=""):
        self.name = name
        self.members = members
        self.instructions = instructions or ""

    def members_in_order(self):
        return sorted(self.members, key=lambda m: (m.speak_order, m.role))

    def speaker(self):
        for member in self.members:
            if member.is_speaker:
                return member
        return self.members_in_order()[0] if self.members else None
