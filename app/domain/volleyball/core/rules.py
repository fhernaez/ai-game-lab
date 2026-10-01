"""Beach volleyball rules: win condition, court switch, possession.

All functions accept an optional ``core`` dict (the resolved core configuration,
see ``defaults.py``). When omitted they fall back to the defaults, so existing
callers and tests keep working unchanged.
"""

from . import defaults

NET_HEIGHT = defaults.DEFAULTS["net_height"]
COURT_WIDTH = defaults.DEFAULTS["court_width"]
COURT_LENGTH = defaults.DEFAULTS["court_length"]
NET_Y = defaults.net_y()

SET_TARGETS = {1: 21, 2: 21, 3: 15}
SWITCH_INTERVALS = {1: 7, 2: 7, 3: 5}


def _c(core):
    return core or defaults.DEFAULTS


def net_y(core=None):
    return defaults.net_y(core)


def court_width(core=None):
    return _c(core)["court_width"]


def court_length(core=None):
    return _c(core)["court_length"]


def net_height(core=None):
    return _c(core)["net_height"]


def set_target(current_set, core=None):
    if core:
        return _c(core).get(f"set_target_{current_set}", 21)
    return SET_TARGETS.get(current_set, 21)


def is_set_won(points_a, points_b, current_set, core=None):
    target = set_target(current_set, core)
    return (points_a >= target or points_b >= target) and abs(points_a - points_b) >= 2


def switch_interval(current_set, core=None):
    if core:
        return _c(core).get(f"switch_interval_{current_set}", 7)
    return SWITCH_INTERVALS.get(current_set, 7)


def in_bounds(x, y, core=None):
    c = _c(core)
    return 0.0 <= x <= c["court_width"] and 0.0 <= y <= c["court_length"]


def in_half(x, y, half, core=None):
    """half 0 = y in [0, net], half 1 = y in [net, length]."""
    ny = net_y(core)
    if half == 0:
        return 0.0 <= y <= ny
    return ny <= y <= court_length(core)
