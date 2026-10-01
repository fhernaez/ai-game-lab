"""Sensors: what the brain may read (the perception / sandbox boundary)."""

SENSORS = ["ball", "own_half", "own_attributes", "rally_history", "score"]

SENSOR_LABELS = {
    "ball": "Ball position and flight time",
    "own_half": "Which half of the court is yours",
    "own_attributes": "Your own body parameters",
    "rally_history": "What has happened this rally",
    "score": "Sets and points",
}


def render_sensors(sensors):
    return ", ".join(sensors or SENSORS)
