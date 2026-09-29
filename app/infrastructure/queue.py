"""Thin Redis/rq queue wrapper.

When no Redis URL is configured, ``enqueue`` runs the job synchronously so the
application keeps working in local development and tests without a Redis server.
"""

from flask import current_app


def get_redis_url():
    return (
        current_app.config.get("REDIS_URL")
        or current_app.config.get("RQ_REDIS_URL")
        or ""
    )


def enqueue(queue_name, fn, *args, **kwargs):
    redis_url = get_redis_url()
    if not redis_url:
        # Synchronous fallback (no Redis available).
        fn(*args, **kwargs)
        return None

    from redis import Redis
    from rq import Queue

    connection = Redis.from_url(redis_url)
    queue = Queue(queue_name, connection=connection)
    return queue.enqueue(fn, *args, **kwargs)
