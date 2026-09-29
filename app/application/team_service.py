"""Team configuration: athlete attributes, point-buy budget, archetypes."""

from ..domain.volleyball import attributes


def default_player_configuration(slot):
    return {
        "name": f"Player {slot}",
        "attributes": attributes.default_attributes(),
        "model": "",
        "temperature": 0.7,
        "max_tokens": 256,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stop": [],
        "response_format": "json",
        "instructions": "",
    }


def apply_archetype(config, archetype_id):
    arch = attributes.archetype_attributes(archetype_id)
    if arch is not None:
        config = dict(config)
        config["attributes"] = arch
    return config


def team_cost(team):
    """Compute the total point-buy cost for a team's two players."""
    return sum(
        attributes.attributes_cost(p.configuration_json.get("attributes", {}))
        for p in team.players
    )


def budget_ok(team, difficulty):
    return team_cost(team) <= attributes.difficulty_budget(difficulty)
