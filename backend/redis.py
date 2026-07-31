import hashlib
import json
import logging
from collections.abc import Callable

from django.conf import settings
from django.core.cache import cache
from redis import Redis
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)
CATALOG_SEARCH_VERSION_KEY = "catalog:search:version"
DEFAULT_CATALOG_SEARCH_VERSION = 1
TMDB_CATALOG_LOCK_KEY = "lock:tmdb:catalog"
EMBEDDING_SYNC_LOCK_KEY = "lock:embeddings:catalog"

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


def catalog_search_cache_key(params: dict, *, version: int) -> str:
    payload = json.dumps(
        params,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"catalog:search:v{version}:{digest}"


def llm_catalog_context_cache_key(params: dict, *, version: int) -> str:
    payload = json.dumps(
        params,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"llm:catalog-context:v{version}:{digest}"


def get_cached_catalog_search(params: dict) -> tuple[str, dict | None]:
    try:
        version = cache.get(CATALOG_SEARCH_VERSION_KEY)
        if not isinstance(version, int) or version < 1:
            version = DEFAULT_CATALOG_SEARCH_VERSION
        key = catalog_search_cache_key(params, version=version)
        payload = cache.get(key)
    except RedisError as error:
        logger.warning("Catalog cache read failed! %s", error)
        key = catalog_search_cache_key(
            params,
            version=DEFAULT_CATALOG_SEARCH_VERSION,
        )
        return key, None
    return key, payload if isinstance(payload, dict) else None


def set_cached_catalog_search(
    key: str,
    payload: dict,
    *,
    timeout: int | None = None,
) -> None:
    try:
        cache.set(key, payload, timeout=timeout)
    except RedisError as error:
        logger.warning("Catalog cache write failed! %s", error)


def get_cached_llm_catalog_context(params: dict) -> tuple[str, dict | None]:
    try:
        version = cache.get(CATALOG_SEARCH_VERSION_KEY)
        if not isinstance(version, int) or version < 1:
            version = DEFAULT_CATALOG_SEARCH_VERSION
        key = llm_catalog_context_cache_key(params, version=version)
        payload = cache.get(key)
    except RedisError as error:
        logger.warning("LLM catalog context cache read failed! %s", error)
        key = llm_catalog_context_cache_key(
            params,
            version=DEFAULT_CATALOG_SEARCH_VERSION,
        )
        return key, None
    return key, payload if isinstance(payload, dict) else None


def set_cached_llm_catalog_context(
    key: str,
    payload: dict,
    *,
    timeout: int | None = None,
) -> None:
    try:
        cache.set(key, payload, timeout=timeout)
    except RedisError as error:
        logger.warning("LLM catalog context cache write failed! %s", error)


def invalidate_catalog_search_cache() -> int | None:
    try:
        if cache.add(CATALOG_SEARCH_VERSION_KEY, 2, timeout=None):
            return 2
        try:
            return cache.incr(CATALOG_SEARCH_VERSION_KEY)
        except ValueError:
            cache.set(CATALOG_SEARCH_VERSION_KEY, 2, timeout=None)
            return 2
    except RedisError as error:
        logger.warning("Catalog cache invalidation failed! %s", error)
        return None


def get_cached_tmdb(
    client,
    endpoint: str,
    *,
    timeout: int = 60 * 60,
    force_refresh: bool = False,
    **params,
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
        cache.set(key, response, timeout=timeout)
    except RedisError as error:
        logger.warning("Redis cache write failed! %s", error)

    return response


def run_with_redis_lock(
    lock_key: str,
    operation: Callable[[], None],
    *,
    timeout: int | None = None,
) -> bool:
    lock = redis_client.lock(
        lock_key,
        timeout=timeout or settings.REDIS_LOCK_TIMEOUT,
        blocking_timeout=settings.REDIS_LOCK_BLOCKING_TIMEOUT,
    )

    try:
        acquired = lock.acquire(blocking=True)
    except RedisError as error:
        logger.warning("Redis lock acquire failed! %s", error)
        operation()
        return True

    if not acquired:
        logger.warning("Operation protected by %s is already running!", lock_key)
        return False

    try:
        operation()
        return True
    finally:
        try:
            lock.release()
        except RedisError as error:
            logger.warning("Redis lock release failed! %s", error)


def sync_from_tmdb(sync_operation: Callable[[], None]) -> bool:
    return run_with_redis_lock(TMDB_CATALOG_LOCK_KEY, sync_operation)
