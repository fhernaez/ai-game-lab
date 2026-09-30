"""The body: 7 parameters (sliders 1..10) + point-buy + archetypes + what/effect."""

# Each parameter carries `label` (UI), `what` (definition) and `effect` (what it changes).
ATTRIBUTES = {
    "jumping_height": {
        "label": "Vertical Leap",
        "what": "How high the player jumps at the net.",
        "effect": "Higher jump lets you block hard spikes and hit down over the block; lower jump risks net touches on hard swings.",
    },
    "transition_speed": {
        "label": "Sand Speed",
        "what": "How fast the player sprints across the sand.",
        "effect": "Faster movement shortens reach time, so the player covers more court and digs more balls.",
    },
    "receiving_accuracy": {
        "label": "Dig & Serve Receive",
        "what": "How cleanly the player controls serves and hard attacks on the first touch.",
        "effect": "Higher accuracy keeps first touches in play; lower accuracy shanks balls out or gives the opponent an easy attack.",
    },
    "passing_accuracy": {
        "label": "Set Precision",
        "what": "How accurately the player sets the ball to the partner.",
        "effect": "Higher accuracy delivers the ball near the net for a clean attack; lower accuracy forces the partner to reach.",
    },
    "shoot_accuracy_distance": {
        "label": "Sniper Vision",
        "what": "How precisely the player aims soft shots at open sand.",
        "effect": "Higher precision places shots in empty areas; lower precision drifts shots and lands them out.",
    },
    "shoot_accuracy_power": {
        "label": "Power Control",
        "what": "How well the player keeps control when hitting at full power.",
        "effect": "Higher control keeps hard hits in bounds; lower control makes hard hits fly out.",
    },
    "shoot_max_power": {
        "label": "Spike Power",
        "what": "How hard the player can hit the ball.",
        "effect": "Harder hits travel faster (less reaction time for the opponent) but are harder to control.",
    },
}

ATTRIBUTE_KEYS = list(ATTRIBUTES.keys())
ATTRIBUTE_LABELS = {k: v["label"] for k, v in ATTRIBUTES.items()}
ATTRIBUTE_DESCRIPTIONS = {k: v["what"] for k, v in ATTRIBUTES.items()}
ATTRIBUTE_EFFECTS = {k: v["effect"] for k, v in ATTRIBUTES.items()}

SLIDER_MIN = 1
SLIDER_MAX = 10

DIFFICULTY_BUDGETS = {"easy": 45, "medium": 25, "hard": 12}
AI_BUDGETS = {"easy": 12, "medium": 25, "hard": 32}

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


def default_parameters():
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
    return sum(attributes_cost(p.get("attributes", p.get("parameters", {}))) for p in players)


def difficulty_budget(difficulty):
    return DIFFICULTY_BUDGETS.get(difficulty, DIFFICULTY_BUDGETS["medium"])


def ai_budget(difficulty):
    return AI_BUDGETS.get(difficulty, AI_BUDGETS["medium"])


def archetype_attributes(archetype_id):
    arch = ARCHETYPES.get(archetype_id)
    if arch is None:
        return None
    merged = default_parameters()
    merged.update(arch["attributes"])
    return merged


def ai_team_attributes(difficulty, rng):
    budget = ai_budget(difficulty)
    attrs = default_parameters()
    while budget > 0:
        key = rng.choice(ATTRIBUTE_KEYS)
        if attrs[key] < SLIDER_MAX:
            attrs[key] += 1
            budget -= 1
    return attrs
