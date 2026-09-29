"""Event type constants and helper constructors."""

GAME_CREATED = "GAME_CREATED"
GAME_STARTED = "GAME_STARTED"
TURN_STARTED = "TURN_STARTED"
AGENT_MESSAGE = "AGENT_MESSAGE"
ACTION_DECLARED = "ACTION_DECLARED"
ACTION_ACCEPTED = "ACTION_ACCEPTED"
ACTION_REJECTED = "ACTION_REJECTED"
STATE_CHANGED = "STATE_CHANGED"
SCORE_CHANGED = "SCORE_CHANGED"
TURN_FINISHED = "TURN_FINISHED"
GAME_FINISHED = "GAME_FINISHED"


def make_event(event_type, actor_id=None, **payload):
    event = {"event_type": event_type, "actor_id": actor_id, "payload": payload}
    return event
