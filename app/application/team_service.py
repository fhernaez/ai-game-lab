"""Team configuration: the brain/body blueprint, point-buy budget, archetypes."""

from ..domain.volleyball.body import actuators, parameters
from ..domain.volleyball.brain import sensors, skills, tools


def default_player_configuration(slot):
    return {
        "name": f"Player {slot}",
        "brain": {
            "persona": "",
            "goal": "Win the point.",
            "task": "",
            "skills": skills.load_default_skills(),
            "tools": list(tools.TOOL_KEYS),
            "sensors": list(sensors.SENSORS),
            "memory": {"type": "short_term", "size": 8},
            "model": "",
            "params": {
                "temperature": 0.7,
                "max_tokens": 256,
                "top_p": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
            },
        },
        "body": {
            "actuators": list(actuators.ACTUATOR_KEYS),
            "parameters": parameters.default_parameters(),
        },
    }


def default_brain_params():
    return {
        "temperature": 0.7,
        "max_tokens": 256,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    }


def apply_archetype(config, archetype_id):
    arch = parameters.archetype_attributes(archetype_id)
    if arch is not None:
        config = dict(config)
        body = dict(config.get("body") or {})
        body["parameters"] = arch
        config["body"] = body
    return config


def player_parameters(player):
    """Flat slider values for one player's body."""
    cfg = player.configuration_json or {}
    return (cfg.get("body") or {}).get("parameters", {})


def team_cost(team):
    """Total point-buy cost across both players of a team."""
    return sum(parameters.attributes_cost(player_parameters(p)) for p in team.players)


def budget_ok(team, difficulty):
    return team_cost(team) <= parameters.difficulty_budget(difficulty)
