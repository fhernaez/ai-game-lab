"""Presence: track which users are currently online."""

from datetime import datetime, timedelta, timezone

from ..extensions import db
from ..models import User

ONLINE_WINDOW_SECONDS = 60


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def touch(user):
    """Update last_seen_at for an authenticated user."""
    if user and not user.is_anonymous:
        user.last_seen_at = datetime.now(timezone.utc)
        db.session.commit()


def is_online(user):
    if user is None:
        return False
    seen = _as_utc(user.last_seen_at)
    if seen is None:
        return False
    return (datetime.now(timezone.utc) - seen).total_seconds() < ONLINE_WINDOW_SECONDS


def online_users(exclude_id=None):
    query = User.query.filter(User.last_seen_at.isnot(None))
    if exclude_id is not None:
        query = query.filter(User.id != exclude_id)
    return [u for u in query.all() if is_online(u)]
