"""Deterministic validation shared by the compiler and the importer."""

REQUIRED_TOP_LEVEL = [
    "game",
    "competition",
    "crew",
    "referee",
    "resources",
    "dialogue",
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
    if not isinstance(competition.get("default_round_budget"), int) or competition.get("default_round_budget", 0) <= 0:
        errors.append("competition.default_round_budget must be a positive integer")

    crew = blueprint.get("crew") or {}
    roles = crew.get("roles") or []
    if not isinstance(roles, list) or not roles:
        errors.append("crew.roles must be a non-empty list")
    role_ids = set()
    speaker_count = 0
    for role in roles:
        if not role.get("id"):
            errors.append("each crew role needs an id")
            continue
        if role.get("id") in role_ids:
            errors.append(f"duplicate role id: {role['id']}")
        role_ids.add(role.get("id"))
        if not isinstance(role.get("speak_order"), int):
            errors.append(f"role {role.get('id')} needs an integer speak_order")
        if role.get("speaker"):
            speaker_count += 1
    if speaker_count != 1:
        errors.append("crew.roles must have exactly one speaker")

    resources = blueprint.get("resources") or {}
    for key in ("team_token_budget", "team_memory_budget"):
        if not isinstance(resources.get(key), int) or resources.get(key, 0) < 0:
            errors.append(f"resources.{key} must be a non-negative integer")

    dialogue = blueprint.get("dialogue") or {}
    actions = dialogue.get("actions") or []
    action_ids = set()
    if not isinstance(actions, list) or not actions:
        errors.append("dialogue.actions must be a non-empty list")
    for action in actions:
        if not action.get("id"):
            errors.append("each dialogue action needs an id")
            continue
        if action.get("id") in action_ids:
            errors.append(f"duplicate action id: {action['id']}")
        action_ids.add(action.get("id"))

    scoring = dialogue.get("scoring") or []
    for rule in scoring:
        if rule.get("kind") == "event" and rule.get("event") not in action_ids:
            errors.append(
                f"scoring rule {rule.get('id')} references unknown action {rule.get('event')}"
            )
        if rule.get("kind") == "criteria" and not rule.get("criteria"):
            errors.append(f"criteria scoring rule {rule.get('id')} needs criteria")

    markdown = blueprint.get("markdown") or {}
    for required in ("game", "rules", "scoring", "referee"):
        if required not in markdown:
            errors.append(f"markdown.{required} is required")
    if not isinstance(markdown.get("agents"), dict) or not markdown.get("agents"):
        errors.append("markdown.agents must be a non-empty mapping")

    playground = blueprint.get("playground") or {}
    for key in ("editable", "locked"):
        if key not in playground:
            errors.append(f"playground.{key} is required")

    return errors
