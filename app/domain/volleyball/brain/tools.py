"""The brain's connectors: the tool registry (also the permission list)."""

TOOLS = {
    "serve": {
        "action": "SERVE",
        "actuator": "serve",
        "params": ["power", "target"],
        "requires": ["shoot_accuracy_power", "shoot_accuracy_distance"],
        "what": "Start the rally from behind the end line.",
        "effect": "Hard serves pressure the receiver; soft serves are safer.",
    },
    "dig": {
        "action": "DIG",
        "actuator": "dig",
        "params": ["power", "target"],
        "requires": ["transition_speed", "receiving_accuracy"],
        "what": "Get under a hard, low ball.",
        "effect": "Keeps the ball alive on the first touch.",
    },
    "set": {
        "action": "SET",
        "actuator": "set",
        "params": ["power", "target"],
        "requires": ["passing_accuracy"],
        "what": "Deliver the ball to the partner near the net.",
        "effect": "A clean set gives the partner a strong attack.",
    },
    "spike": {
        "action": "SPIKE",
        "actuator": "spike",
        "params": ["power", "target"],
        "requires": ["jumping_height", "shoot_max_power", "shoot_accuracy_power"],
        "what": "Hit the ball hard over the net.",
        "effect": "Fast attack; short flight time, but less control.",
    },
    "place": {
        "action": "PLACE",
        "actuator": "place",
        "params": ["power", "target"],
        "requires": ["shoot_accuracy_distance", "shoot_accuracy_power"],
        "what": "A soft, placed shot over the net.",
        "effect": "Aimed at empty sand; slower but more precise.",
    },
    "block": {
        "action": "BLOCK",
        "actuator": "block",
        "params": ["power", "target"],
        "requires": ["jumping_height"],
        "what": "Jump at the net to stop the opponent's attack.",
        "effect": "A clean block wins the point; a block touch counts as the first touch.",
    },
}

TOOL_KEYS = list(TOOLS.keys())
TOOL_ACTIONS = {t["action"] for t in TOOLS.values()}


def allowed_actions(tool_ids):
    """Return the action strings for the given tool ids (the permission list)."""
    return [TOOLS[t]["action"] for t in (tool_ids or []) if t in TOOLS]
