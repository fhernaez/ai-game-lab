"""Beach volleyball rules: win condition, court switch, possession."""

SET_TARGETS = {1: 21, 2: 21, 3: 15}
SWITCH_INTERVALS = {1: 7, 2: 7, 3: 5}

NET_HEIGHT = 2.43
COURT_WIDTH = 8.0
COURT_LENGTH = 16.0
NET_Y = 8.0


def set_target(current_set):
    return SET_TARGETS.get(current_set, 21)


def is_set_won(points_a, points_b, current_set):
    target = set_target(current_set)
    return (points_a >= target or points_b >= target) and abs(points_a - points_b) >= 2


def switch_interval(current_set):
    return SWITCH_INTERVALS.get(current_set, 7)


def in_bounds(x, y):
    return 0.0 <= x <= COURT_WIDTH and 0.0 <= y <= COURT_LENGTH


def in_half(x, y, half):
    """half 0 = y in [0, 8], half 1 = y in [8, 16]."""
    if half == 0:
        return 0.0 <= y <= NET_Y
    return NET_Y <= y <= COURT_LENGTH
