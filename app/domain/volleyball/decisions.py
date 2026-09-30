"""Structured decision protocol: each agent returns a message, a ball hit, and its own movement."""

ACTIONS = ["SERVE", "DIG", "SET", "SPIKE", "PLACE", "BLOCK"]

DEFAULT_DECISION = {
    "message": "",
    "action": "SET",
    "power": 0.5,
    "target": [4.0, 12.0],
    "move_to": [4.0, 8.0],
    "move_speed": 0.5,
}


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def parse_decision(parsed, fallback=None):
    """Validate and clamp a parsed LLM output; never raises."""
    fallback = fallback or dict(DEFAULT_DECISION)
    if not isinstance(parsed, dict):
        return dict(fallback)

    message = str(parsed.get("message", fallback.get("message", "")))

    action = parsed.get("action")
    if action not in ACTIONS:
        action = fallback["action"]

    try:
        power = float(parsed.get("power", fallback["power"]))
    except (TypeError, ValueError):
        power = fallback["power"]
    power = _clamp(power, 0.0, 1.0)

    target = _point(parsed.get("target"), fallback["target"])
    move_to = _point(parsed.get("move_to"), fallback["move_to"])

    try:
        move_speed = float(parsed.get("move_speed", fallback["move_speed"]))
    except (TypeError, ValueError):
        move_speed = fallback["move_speed"]
    move_speed = _clamp(move_speed, 0.1, 1.0)

    return {
        "message": message,
        "action": action,
        "power": power,
        "target": target,
        "move_to": move_to,
        "move_speed": move_speed,
    }


def _point(value, default):
    if not (isinstance(value, (list, tuple)) and len(value) >= 2):
        return [default[0], default[1]]
    try:
        x = _clamp(float(value[0]), 0.0, 8.0)
        y = _clamp(float(value[1]), 0.0, 16.0)
    except (TypeError, ValueError):
        return [default[0], default[1]]
    return [x, y]


def build_decision_prompt(team_name, player, state, action_hint, rally_history):
    """Assemble the prompt for one player's decision, with shared rally context."""
    attrs = player["attributes"]
    attr_lines = "\n".join(
        f"  {k}: {attrs.get(k, 1)}/10" for k in
        ["jumping_height", "transition_speed", "receiving_accuracy",
         "passing_accuracy", "shoot_accuracy_distance",
         "shoot_accuracy_power", "shoot_max_power"]
    )
    history = "\n".join(rally_history[-10:]) or "(start of rally)"

    system = (
        "You are an AI beach-volleyball player. Return a JSON object with a short "
        "natural-language message explaining what you will do, the ball hit you make, "
        "and your own movement (destination + speed)."
    )
    user = "\n\n".join(
        [
            f"TEAM: {team_name}",
            f"YOU ARE: {player['name']} (slot {player['slot']})",
            "YOUR ATHLETE ATTRIBUTES (1..10):\n" + attr_lines,
            "TEAM STRATEGY:\n" + player.get("instructions", ""),
            "CURRENT MATCH STATE:\n" + _render_state(state),
            "WHAT HAS HAPPENED THIS RALLY:\n" + history,
            f"EXPECTED ACTION: {action_hint}",
            'Return JSON: {"message": "...", "action": "SERVE"|"DIG"|"SET"|"SPIKE"|"PLACE"|"BLOCK", '
            '"power": 0.0..1.0, "target": [x, y], "move_to": [x, y], "move_speed": 0.0..1.0}',
        ]
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _render_state(state):
    return (
        f"set {state.current_set}, points {state.set_points[0]}-{state.set_points[1]}, "
        f"sets {state.sets_won[0]}-{state.sets_won[1]}, server team {state.server}, "
        f"touches {state.touches}, "
        f"ball ({state.ball['x']:.1f}, {state.ball['y']:.1f}, {state.ball['z']:.1f}), "
        f"flight time {state.flight_time:.2f}s"
    )
