"""Event type constants for the beach-volleyball interaction log."""

MATCH_STARTED = "MATCH_STARTED"
SET_STARTED = "SET_STARTED"
RALLY_STARTED = "RALLY_STARTED"
DECISION = "DECISION"
TRAJECTORY = "TRAJECTORY"
INTERCEPT = "INTERCEPT"
TOUCH = "TOUCH"
FAULT = "FAULT"
POINT = "POINT"
SET_WON = "SET_WON"
COURT_SWITCH = "COURT_SWITCH"
MATCH_FINISHED = "MATCH_FINISHED"


def make_event(event_type, actor_id=None, **payload):
    return {"event_type": event_type, "actor_id": actor_id, "payload": payload}
