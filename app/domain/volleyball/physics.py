"""Deterministic simulation core for beach volleyball.

The core adds a seeded random component to every shot, computes the ball flight
time from distance and shot power, and simulates whether a player can reach the
ball before it lands. All randomness uses a seeded ``random.Random`` so a match is
reproducible.
"""

import math
import random

from . import rules
from .attributes import slider_to_float

# Physical constants (meters / seconds).
BASE_BALL_SPEED = 11.0     # base ball velocity for a set/serve
POWER_SPEED_BONUS = 9.0    # extra velocity at full shoot_max_power


def _f(attrs, key):
    return slider_to_float(attrs.get(key, 1))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def move_speed(attrs):
    """Player sprint speed in m/s from transition_speed (0.1..1.0 -> ~2..7 m/s)."""
    return 1.5 + 5.5 * _f(attrs, "transition_speed")


def ball_speed(action, power, attrs):
    """Ball velocity for a given action (m/s)."""
    power = max(0.0, min(1.0, power))
    if action in ("SPIKE", "PLACE", "SERVE"):
        return BASE_BALL_SPEED + POWER_SPEED_BONUS * _f(attrs, "shoot_max_power") * power
    # SET / DIG are soft touches.
    return BASE_BALL_SPEED * 0.5


def flight_time(origin, target, action, power, attrs):
    return distance(origin, target) / max(1.0, ball_speed(action, power, attrs))


def reach_time(distance_, attrs):
    """Time (s) for a player to cover a distance on the sand."""
    return distance_ / max(0.5, move_speed(attrs))


def can_reach(player_pos, landing, attrs, t_flight, margin=0.1):
    return reach_time(distance(player_pos, landing), attrs) <= t_flight + margin


def offset_sigma(action, power, attrs):
    """Spread (meters) of the random landing offset for a shot."""
    power = max(0.0, min(1.0, power))
    if action in ("SPIKE", "PLACE"):
        acc_power = _f(attrs, "shoot_accuracy_power")
        acc_dist = _f(attrs, "shoot_accuracy_distance")
        return (1.0 - acc_power) * power * 1.8 + (1.0 - acc_dist) * 0.5 + 0.08
    if action == "SERVE":
        return (1.0 - _f(attrs, "shoot_accuracy_power")) * power * 1.2 + 0.15
    if action == "SET":
        return (1.0 - _f(attrs, "passing_accuracy")) * 0.9 + 0.1
    if action == "DIG":
        return (1.0 - _f(attrs, "receiving_accuracy")) * 1.2 + 0.15
    return 0.2


def resolve_shot(action, attrs, power, target, rng):
    """Return (landing, fault, offset).

    ``landing`` is [x, y]; ``fault`` is None or one of "net"/"out".
    """
    sigma = offset_sigma(action, power, attrs)
    x = target[0] + rng.gauss(0, sigma)
    y = target[1] + rng.gauss(0, sigma)
    offset = math.hypot(x - target[0], y - target[1])

    # Net risk: a low-power serve, or a low-jump attack, may clip the net.
    if action in ("SPIKE", "PLACE"):
        net_risk = max(0.0, (1.0 - _f(attrs, "jumping_height")) * 0.25 * power)
        if rng.random() < net_risk:
            return None, "net", offset
    if action == "SERVE" and rng.random() < max(0.0, 0.18 - power * 0.15):
        return None, "net", offset

    x = max(0.0, min(rules.COURT_WIDTH, x))
    y = max(0.0, min(rules.COURT_LENGTH, y))
    if not rules.in_bounds(x, y):
        return None, "out", offset
    return [x, y], None, offset
