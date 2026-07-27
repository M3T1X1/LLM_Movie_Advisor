from django.core.cache import cache
from redis import Redis
from django.conf import settings
import hashlib
import json


redis_client = Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_timeout=2,
    socket_connect_timeout=2,
)

def tmdb_cache_key(endpoint: str, **params) -> str:
    payload = json.dumps(
        {
            "endpoint": endpoint,
            "params": params,
        },
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return f"apiTMDB:response:{digest}"


def get_cached_tmdb(client,
                    endpoint: str,
                    *,
                    timeout: int = 60*60,
                    force_refresh: bool = False,
                    **params
                    ) -> dict:
    key = tmdb_cache_key(endpoint, **params)
    if not force_refresh:
        cached_response = cache.get(key)
        if cached_response is not None:
            return cached_response

    response = client.get(endpoint, **params)
    cache.set(key, response, timeout)

    return response
