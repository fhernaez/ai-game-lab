"""Deterministic referee: authoritative validation and scoring resolution.

The referee is deliberately deterministic. The LLM may interpret ambiguity,
but the authoritative state transition always goes through these functions.
"""


def get_actions(blueprint):
    return blueprint.get("engine", {}).get("actions", [])


def allowed_actions_for(blueprint, role):
    """Return the action ids a given role may declare."""
    allowed = []
    for action in get_actions(blueprint):
        roles = action.get("roles")
        if not roles or role in roles:
            allowed.append(action["id"])
    return allowed


def validate_action(blueprint, role, action):
    if not isinstance(action, dict):
        return False, "action must be a mapping"
    action_id = action.get("action")
    allowed = allowed_actions_for(blueprint, role)
    if action_id not in allowed:
        return False, f"action {action_id!r} is not allowed for role {role!r}"
    return True, ""


def resolve_scoring(blueprint, action_type, rng):
    """Deterministically resolve the score change for an accepted action."""
    engine = blueprint.get("engine", {})
    scoring_rules = engine.get("scoring", [])
    points = 0
    explanations = []

    for rule in scoring_rules:
        kind = rule.get("kind")
        if kind == "event" and rule.get("event") == action_type:
            if rng.random() < float(rule.get("probability", 0.0)):
                earned = int(rule.get("points", 1))
                points += earned
                explanations.append(f"{rule.get('id', action_type)}: +{earned}")
        elif kind == "criteria":
            earned = 0
            for criterion in rule.get("criteria", []):
                earned += rng.randint(0, int(rule.get("max", 10)))
            points += earned
            explanations.append(f"{rule.get('id', 'criteria_score')}: +{earned}")

    return points, ("; ".join(explanations) if explanations else "no score change")
