"""Event type constants and helper constructors."""

GAME_CREATED = "GAME_CREATED"
GAME_STARTED = "GAME_STARTED"
ROUND_STARTED = "ROUND_STARTED"
CREW_MESSAGE = "CREW_MESSAGE"
ACTION_PROPOSED = "ACTION_PROPOSED"
REFEREE_VERDICT = "REFEREE_VERDICT"
STATE_CHANGED = "STATE_CHANGED"
SCORE_CHANGED = "SCORE_CHANGED"
ROUND_FINISHED = "ROUND_FINISHED"
GAME_FINISHED = "GAME_FINISHED"


def make_event(event_type, actor_id=None, **payload):
    return {"event_type": event_type, "actor_id": actor_id, "payload": payload}
