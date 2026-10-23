"""Tiny in-memory TTL cache so the page refresh doesn't hammer the data source."""

import time
from functools import wraps


def ttl_cache(seconds: int):
    """Cache a function's result per argument tuple for `seconds`."""

    def decorator(func):
        store: dict = {}

        @wraps(func)
        def wrapper(*args):
            now = time.monotonic()
            hit = store.get(args)
            if hit and now - hit[0] < seconds:
                return hit[1]
            value = func(*args)
            store[args] = (now, value)
            return value

        wrapper.cache_clear = store.clear
        return wrapper

    return decorator
