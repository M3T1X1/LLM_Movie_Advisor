from django.core.cache import cache
from redis import Redis
from redis.exceptions import RedisError
from django.conf import settings
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

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
        try:
            cached_response = cache.get(key)
        except RedisError as error:
            logger.warning("Redis cache read failed! %s", error)
        else:
            if cached_response is not None:
                return cached_response

    response = client.get(endpoint, **params)
    try:
        cache.set(key, response, timeout = timeout)
    except RedisError as error:
        logger.warning("Redis cache write failed! %s", error)

    return response
