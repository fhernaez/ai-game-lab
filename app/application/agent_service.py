"""Agent configuration helpers: default configurations derived from a blueprint."""


def roles_for_blueprint(blueprint):
    return blueprint.get("teams", {}).get("roles", [])


def expand_agents(blueprint):
    """Return the ordered list of role ids per team from the blueprint."""
    agents = []
    for role in roles_for_blueprint(blueprint):
        for _ in range(role.get("count", 1)):
            agents.append(role["id"])
    return agents


def default_agent_configuration(blueprint, role_id):
    skills = sorted((blueprint.get("markdown", {}).get("skills") or {}).keys())
    return {
        "role": role_id,
        "instructions": "",
        "objective": "",
        "skills": skills,
        "selected_skills": [],
        "model": "mock-model",
        "temperature": 0.2,
        "max_tokens": 256,
        "memory": "short",
        "behavior": {
            "risk": "balanced",
            "independence": "collaborative",
            "verbosity": "concise",
        },
        "communication": {
            "team": True,
            "trainee": True,
            "referee": "action_only",
            "opponents": False,
        },
    }


def default_team_configuration(blueprint):
    return {
        "instructions": "",
        "strategy": "",
        "token_allocation": {},
        "memory_allocation": {},
    }
