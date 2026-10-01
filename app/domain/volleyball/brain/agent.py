"""BrainAgent: wraps the brain config (persona, goal, task, skills, tools, sensors, memory)."""

from . import skills, tools
from .sensors import SENSORS


class BrainAgent:
    def __init__(self, config):
        config = config or {}
        self.persona = config.get("persona", "")
        self.goal = config.get("goal", "")
        self.task = config.get("task", "")
        self.skills = config.get("skills") or skills.load_default_skills()
        self.tools = config.get("tools") or list(tools.TOOL_KEYS)
        self.sensors = config.get("sensors") or list(SENSORS)
        self.memory_size = (config.get("memory") or {}).get("size", 8)
        self.model = config.get("model", "")
        self.params = dict(config.get("params") or {})

    def allowed_actions(self):
        return tools.allowed_actions(self.tools)
