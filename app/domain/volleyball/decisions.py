"""Structured decision protocol for beach-volleyball agents."""

ACTIONS = ["SERVE", "DIG", "SET", "SPIKE", "PLACE", "BLOCK"]

DEFAULT_DECISION = {"action": "SET", "power": 0.5, "target": [4.0, 12.0]}


def parse_decision(parsed, fallback=None):
    """Validate and clamp a parsed LLM decision; never raises."""
    fallback = fallback or dict(DEFAULT_DECISION)
    if not isinstance(parsed, dict):
        return dict(fallback)

    action = parsed.get("action")
    if action not in ACTIONS:
        action = fallback["action"]

    try:
        power = float(parsed.get("power", fallback["power"]))
    except (TypeError, ValueError):
        power = fallback["power"]
    power = max(0.0, min(1.0, power))

    target = parsed.get("target")
    if not (isinstance(target, (list, tuple)) and len(target) >= 2):
        target = fallback["target"]
    try:
        x = max(0.0, min(8.0, float(target[0])))
        y = max(0.0, min(16.0, float(target[1])))
    except (TypeError, ValueError):
        x, y = fallback["target"]
    return {"action": action, "power": power, "target": [x, y]}


def build_decision_prompt(team_name, player, state, action_hint):
    """Assemble the prompt for one player's decision."""
    attrs = player["attributes"]
    attr_lines = "\n".join(
        f"  {k}: {attrs.get(k, 1)}/10" for k in
        ["jumping_height", "transition_speed", "receiving_accuracy",
         "passing_accuracy", "shoot_accuracy_distance",
         "shoot_accuracy_power", "shoot_max_power"]
    )
    system = (
        "You are an AI beach-volleyball player. Return only a structured JSON decision."
    )
    user = "\n\n".join(
        [
            f"TEAM: {team_name}",
            f"YOU ARE: {player['name']} (slot {player['slot']})",
            "YOUR ATHLETE ATTRIBUTES (1..10):\n" + attr_lines,
            "TEAM STRATEGY:\n" + player.get("instructions", ""),
            "CURRENT MATCH STATE:\n" + _render_state(state),
            f"EXPECTED ACTION: {action_hint}",
            'Return JSON: {"action": "SERVE"|"DIG"|"SET"|"SPIKE"|"PLACE"|"BLOCK", '
            '"power": 0.0..1.0, "target": [x, y]}',
        ]
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _render_state(state):
    return (
        f"set {state.current_set}, "
        f"points {state.set_points[0]}-{state.set_points[1]}, "
        f"sets {state.sets_won[0]}-{state.sets_won[1]}, "
        f"server team {state.server}, touches {state.touches}, "
        f"ball ({state.ball['x']:.1f}, {state.ball['y']:.1f}, {state.ball['z']:.1f})"
    )
