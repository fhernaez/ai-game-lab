"""Athlete attributes: the 7 skills, slider mapping, point-buy, difficulty, archetypes."""

ATTRIBUTE_KEYS = [
    "jumping_height",
    "transition_speed",
    "receiving_accuracy",
    "passing_accuracy",
    "shoot_accuracy_distance",
    "shoot_accuracy_power",
    "shoot_max_power",
]

# Slider 1..10 -> float 0.1..1.0
SLIDER_MIN = 1
SLIDER_MAX = 10

DIFFICULTY_BUDGETS = {"easy": 45, "medium": 25, "hard": 12}
AI_BUDGETS = {"easy": 12, "medium": 25, "hard": 32}

ATTRIBUTE_LABELS = {
    "jumping_height": "Vertical Leap",
    "transition_speed": "Sand Speed",
    "receiving_accuracy": "Dig & Serve Receive",
    "passing_accuracy": "Set Precision",
    "shoot_accuracy_distance": "Sniper Vision",
    "shoot_accuracy_power": "Power Control",
    "shoot_max_power": "Spike Power",
}

ATTRIBUTE_DESCRIPTIONS = {
    "jumping_height": "How high the player jumps at the net — blocks spikes and hits downhill over the block.",
    "transition_speed": "How fast the player sprints across the sand to intercept the ball.",
    "receiving_accuracy": "How cleanly the player controls incoming serves and hard spikes on the first touch.",
    "passing_accuracy": "How accurately the player passes to the partner (diminishes with distance).",
    "shoot_accuracy_distance": "How precisely the player aims soft shots at empty sand on the far side.",
    "shoot_accuracy_power": "How well the player keeps control when hitting at maximum power.",
    "shoot_max_power": "The sheer velocity of attacks — less reaction time for the opponent.",
}

ARCHETYPES = {
    "tower": {
        "name": "The Tower (Net Dominator)",
        "description": "Big blocks and heavy spikes; slow on the ground.",
        "attributes": {
            "jumping_height": 8,
            "shoot_max_power": 8,
            "shoot_accuracy_power": 6,
            "transition_speed": 2,
            "receiving_accuracy": 2,
            "passing_accuracy": 3,
            "shoot_accuracy_distance": 3,
        },
    },
    "ninja": {
        "name": "The Defensive Ninja (Floor Cleaner)",
        "description": "Covers ground, chases everything, puts up perfect sets.",
        "attributes": {
            "transition_speed": 9,
            "receiving_accuracy": 9,
            "passing_accuracy": 6,
            "shoot_accuracy_distance": 3,
            "jumping_height": 2,
            "shoot_accuracy_power": 2,
            "shoot_max_power": 1,
        },
    },
    "sharpshooter": {
        "name": "The Sharp-Shooter (Tactician)",
        "description": "Finesse over force; placements over power.",
        "attributes": {
            "shoot_accuracy_distance": 9,
            "passing_accuracy": 8,
            "receiving_accuracy": 6,
            "transition_speed": 4,
            "shoot_accuracy_power": 2,
            "jumping_height": 2,
            "shoot_max_power": 1,
        },
    },
}


def slider_to_float(value):
    return max(0.1, min(1.0, value / 10.0))


def default_attributes():
    return {key: 1 for key in ATTRIBUTE_KEYS}


def clamp_slider(value):
    try:
        return max(SLIDER_MIN, min(SLIDER_MAX, int(value)))
    except (TypeError, ValueError):
        return SLIDER_MIN


def attributes_cost(attributes):
    """Each slider point above 1 costs 1 point."""
    return sum(max(0, int(attributes.get(k, 1)) - 1) for k in ATTRIBUTE_KEYS)


def team_cost(players):
    """Total point-buy cost across both players of a team."""
    return sum(attributes_cost(p.get("attributes", {})) for p in players)


def difficulty_budget(difficulty):
    return DIFFICULTY_BUDGETS.get(difficulty, DIFFICULTY_BUDGETS["medium"])


def ai_budget(difficulty):
    return AI_BUDGETS.get(difficulty, AI_BUDGETS["medium"])


def archetype_attributes(archetype_id):
    arch = ARCHETYPES.get(archetype_id)
    if arch is None:
        return None
    merged = default_attributes()
    merged.update(arch["attributes"])
    return merged


def ai_team_attributes(difficulty, rng):
    """Build a deterministic AI opponent within its difficulty budget."""
    budget = ai_budget(difficulty)
    attrs = default_attributes()
    # Greedily spend budget on random attributes until exhausted.
    while budget > 0:
        key = rng.choice(ATTRIBUTE_KEYS)
        if attrs[key] < SLIDER_MAX:
            attrs[key] += 1
            budget -= 1
    return attrs
