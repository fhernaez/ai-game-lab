"""The body's move library (actuators)."""

ACTUATORS = {
    "run": {
        "what": "Sprint across the sand to reach the ball.",
        "effect": "Uses transition_speed to shorten the time to reach the ball.",
    },
    "jump": {
        "what": "Leap at the net to block or spike.",
        "effect": "Uses jumping_height to reach high balls and block hard spikes.",
    },
    "serve": {
        "what": "Start the rally from behind the end line.",
        "effect": "Hard serves pressure the receiver; soft serves are safer.",
    },
    "pass": {
        "what": "Control the first touch.",
        "effect": "Uses receiving_accuracy to keep the first touch in play.",
    },
    "set": {
        "what": "Deliver the ball to the partner near the net.",
        "effect": "Uses passing_accuracy to give the partner a clean attack.",
    },
    "spike": {
        "what": "Hit the ball hard over the net.",
        "effect": "Fast attack; short flight time, but less control.",
    },
    "place": {
        "what": "A soft, placed shot over the net.",
        "effect": "Aimed at empty sand; uses shoot_accuracy_distance.",
    },
    "block": {
        "what": "Jump at the net to stop the opponent's attack.",
        "effect": "A clean block wins the point; a block touch counts as the first touch.",
    },
    "dig": {
        "what": "Get under a hard, low ball.",
        "effect": "Keeps the ball alive; uses receiving_accuracy.",
    },
}

ACTUATOR_KEYS = list(ACTUATORS.keys())
