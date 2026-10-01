"""The brain's decision protocol: a message + a structured ball hit + movement.

This module has two jobs:

1. ``parse_decision`` — validate and clamp whatever JSON the LLM returns so a
   malformed or out-of-range decision can never crash the engine.
2. ``build_decision_prompt`` — assemble the prompt the LLM receives. It is built
   from labelled sections (persona, goal, task, skills, tools, sensors, memory)
   plus an explicit **court-coordinate guide**, because models otherwise swap the
   x/y axes and produce out-of-range coordinates.
"""

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

# Court-coordinate guide, injected into every prompt. The axes are spelled out
# **side-specifically** because LLMs otherwise confuse which half they defend and aim
# into their own side (e.g. a right-side player targeting y = 14 instead of the
# opponent's y 0..8). See VOLLEYBALL_SPEC.md §2 for the canonical coordinate system.
def _coordinate_guide(own_half=None):
    """Return the coordinate guide for the given half (0 = LEFT, 1 = RIGHT)."""
    if own_half == 1:
        own, end_line, opponent = "RIGHT (y 8..16)", "y = 16", "y 0..8"
    else:
        own, end_line, opponent = "LEFT (y 0..8)", "y = 0", "y 8..16"
    return (
        "COURT COORDINATES (meters):\n"
        "- x = across the court: 0 (left sideline) to 8 (right sideline).\n"
        "- y = down the court: 0 to 16. The net is at y = 8 (2.43 m high).\n"
        f"- YOU defend the {own}. Your end line is {end_line}.\n"
        f"- The OPPONENT's half is {opponent} — aim every target there.\n"
        "- Ball positions are written (x, y, z) where z is the height above the sand.\n"
        "- target = where the ball should land: always in the OPPONENT's half.\n"
        "- move_to = where you run: always in YOUR half (never cross y = 8)."
    )


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def parse_decision(parsed, fallback=None):
    """Validate and clamp a parsed LLM output; never raises.

    Returns a fully-formed decision dict, substituting ``fallback`` (or the
    DEFAULT_DECISION) for any missing or invalid field.
    """
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
    """Coerce a JSON value into an in-bounds [x, y] court point."""
    if not (isinstance(value, (list, tuple)) and len(value) >= 2):
        return [default[0], default[1]]
    try:
        x = _clamp(float(value[0]), 0.0, 8.0)
        y = _clamp(float(value[1]), 0.0, 16.0)
    except (TypeError, ValueError):
        return [default[0], default[1]]
    return [x, y]


def build_decision_prompt(brain, team_name, player_name, slot, state, action_hint, rally_history, team_index=None):
    """Assemble the brain's prompt as (system, user) messages.

    The user message is built from short, labelled sections so the model always
    knows who it is, what it can do/know/see, where it is on the court, and the
    exact JSON it must return.
    """
    tool_list = ", ".join(brain.get("tools") or list(tools.TOOL_KEYS))
    skill_text = skills.render_skills(brain.get("skills") or skills.load_default_skills())
    sensor_text = render_sensors(brain.get("sensors"))

    # Which half the team defends; the model's move_to must stay inside it.
    own_half = state.sides[team_index] if team_index is not None else None
    half_line = ""
    if own_half is not None:
        side = "LEFT (y 0..8)" if own_half == 0 else "RIGHT (y 8..16)"
        half_line = f"YOUR HALF: you defend the {side}. Keep move_to inside your own half.\n\n"

    system = (
        "You are an AI beach-volleyball player. Return a JSON object with a short "
        "natural-language message explaining what you will do, the ball hit you make, "
        "and your own movement (destination + speed)."
    )
    user = "\n\n".join(
        [
            f"TEAM: {team_name}",
            f"YOU ARE: {player_name} (slot {slot})",
            half_line + _coordinate_guide(own_half),
            f"PERSONA\n{brain.get('persona', '')}",
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
        f"ball (x={state.ball['x']:.1f}, y={state.ball['y']:.1f}, z={state.ball['z']:.1f}), "
        f"flight time {state.flight_time:.2f}s"
    )
