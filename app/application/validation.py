"""Deterministic validation shared by the compiler and the importer.

Both directions run the same rules so that a blueprint is valid regardless
of whether it came from the GUI or the Technical view.
"""

REQUIRED_TOP_LEVEL = [
    "game",
    "competition",
    "teams",
    "referee",
    "resources",
    "engine",
    "playground",
    "markdown",
]


def validate_blueprint(blueprint):
    errors = []

    if not isinstance(blueprint, dict):
        return ["Blueprint must be a mapping."]

    for key in REQUIRED_TOP_LEVEL:
        if key not in blueprint:
            errors.append(f"Missing top-level key: {key}")

    game = blueprint.get("game") or {}
    if not game.get("id"):
        errors.append("game.id is required")
    if not game.get("name"):
        errors.append("game.name is required")

    competition = blueprint.get("competition") or {}
    if not competition.get("teams"):
        errors.append("competition.teams is required")
    duration = competition.get("duration") or {}
    if duration.get("type") not in ("turns", "rounds"):
        errors.append("competition.duration.type must be 'turns' or 'rounds'")
    if not isinstance(duration.get("value"), int) or duration.get("value", 0) <= 0:
        errors.append("competition.duration.value must be a positive integer")

    teams = blueprint.get("teams") or {}
    roles = teams.get("roles") or []
    if not isinstance(roles, list) or not roles:
        errors.append("teams.roles must be a non-empty list")
    role_ids = set()
    for role in roles:
        if not role.get("id"):
            errors.append("each role needs an id")
            continue
        if role.get("id") in role_ids:
            errors.append(f"duplicate role id: {role['id']}")
        role_ids.add(role.get("id"))
        if not isinstance(role.get("count"), int) or role.get("count", 0) < 1:
            errors.append(f"role {role.get('id')} must have a positive count")

    resources = blueprint.get("resources") or {}
    for key in ("team_token_budget", "team_memory_budget"):
        if not isinstance(resources.get(key), int) or resources.get(key, 0) < 0:
            errors.append(f"resources.{key} must be a non-negative integer")

    engine = blueprint.get("engine") or {}
    actions = engine.get("actions") or []
    action_ids = set()
    if not isinstance(actions, list) or not actions:
        errors.append("engine.actions must be a non-empty list")
    for action in actions:
        if not action.get("id"):
            errors.append("each engine action needs an id")
            continue
        if action.get("id") in action_ids:
            errors.append(f"duplicate action id: {action['id']}")
        action_ids.add(action.get("id"))

    scoring = engine.get("scoring") or []
    for rule in scoring:
        if rule.get("kind") == "event":
            if rule.get("event") not in action_ids:
                errors.append(
                    f"scoring rule {rule.get('id')} references unknown action "
                    f"{rule.get('event')}"
                )
        if rule.get("kind") == "criteria" and not rule.get("criteria"):
            errors.append(f"criteria scoring rule {rule.get('id')} needs criteria")

    markdown = blueprint.get("markdown") or {}
    for required in ("game", "rules", "scoring", "referee"):
        if required not in markdown:
            errors.append(f"markdown.{required} is required")
    if not isinstance(markdown.get("agents"), dict) or not markdown.get("agents"):
        errors.append("markdown.agents must be a non-empty mapping")
    if not isinstance(markdown.get("skills"), dict):
        errors.append("markdown.skills must be a mapping")

    playground = blueprint.get("playground") or {}
    for key in ("editable", "locked"):
        if key not in playground:
            errors.append(f"playground.{key} is required")

    return errors
