"""The brain's decision protocol: message + ball hit + own movement."""

from . import skills, tools
from .sensors import render_sensors

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


def build_decision_prompt(brain, team_name, player_name, slot, state, action_hint, rally_history, team_index=None):
    """Assemble the brain's prompt from persona/goal/task/skills/tools/sensors."""
    tool_list = ", ".join(brain.get("tools") or list(tools.TOOL_KEYS))
    skill_text = skills.render_skills(brain.get("skills") or skills.load_default_skills())
    sensor_text = render_sensors(brain.get("sensors"))

    half_line = ""
    if team_index is not None:
        own_half = state.sides[team_index]
        side = "LEFT (y 0..8)" if own_half == 0 else "RIGHT (y 8..16)"
        half_line = f"YOUR HALF: you are on the {side}. Your move_to must stay inside your own half.\n\n"

    system = (
        "You are an AI beach-volleyball player. Return a JSON object with a short "
        "natural-language message explaining what you will do, the ball hit you make, "
        "and your own movement (destination + speed)."
    )
    user = "\n\n".join(
        [
            f"TEAM: {team_name}",
            f"YOU ARE: {player_name} (slot {slot})",
            half_line + f"PERSONA\n{brain.get('persona', '')}",
            f"GOAL\n{brain.get('goal', '')}",
            f"TASK\n{action_hint}",
            f"SKILLS (what you know)\n{skill_text}",
            f"TOOLS (what you can do)\n{tool_list}",
            f"SENSORS (what you can see)\n{sensor_text}",
            "CURRENT MATCH STATE:\n" + _render_state(state),
            "WHAT HAS HAPPENED THIS RALLY:\n" + ("\n".join(rally_history[-10:]) or "(start of rally)"),
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
