import logging

from django.contrib.sessions.backends.cached_db import (
    SessionStore as CachedDatabaseSessionStore,
)
from django.contrib.sessions.backends.db import (
    SessionStore as DatabaseSessionStore,
)


logger = logging.getLogger(__name__)


class SessionStore(CachedDatabaseSessionStore):
    def _log_cache_failure(self, operation: str, error: Exception) -> None:
        logger.warning(
            "Session cache %s failed; using PostgreSQL: %s",
            operation,
            error,
        )

    def load(self):
        try:
            data = self._cache.get(self.cache_key)
        except Exception as error:
            self._log_cache_failure("read", error)
            return DatabaseSessionStore.load(self)

        if data is not None:
            return data

        session = self._get_session_from_db()
        if session is None:
            return {}

        data = self.decode(session.session_data)
        try:
            self._cache.set(
                self.cache_key,
                data,
                self.get_expiry_age(expiry=session.expire_date),
            )
        except Exception as error:
            self._log_cache_failure("write", error)
        return data

    async def aload(self):
        try:
            data = await self._cache.aget(await self.acache_key())
        except Exception as error:
            self._log_cache_failure("read", error)
            return await DatabaseSessionStore.aload(self)

        if data is not None:
            return data

        session = await self._aget_session_from_db()
        if session is None:
            return {}

        data = self.decode(session.session_data)
        try:
            await self._cache.aset(
                await self.acache_key(),
                data,
                await self.aget_expiry_age(expiry=session.expire_date),
            )
        except Exception as error:
            self._log_cache_failure("write", error)
        return data

    def exists(self, session_key):
        if not session_key:
            return False

        try:
            if self.cache_key_prefix + session_key in self._cache:
                return True
        except Exception as error:
            self._log_cache_failure("existence check", error)
        return DatabaseSessionStore.exists(self, session_key)

    async def aexists(self, session_key):
        if not session_key:
            return False

        try:
            if await self._cache.ahas_key(
                self.cache_key_prefix + session_key
            ):
                return True
        except Exception as error:
            self._log_cache_failure("existence check", error)
        return await DatabaseSessionStore.aexists(self, session_key)

    def save(self, must_create=False):
        if self.session_key is None:
            return self.create()

        DatabaseSessionStore.save(self, must_create)
        try:
            self._cache.set(
                self.cache_key,
                self._session,
                self.get_expiry_age(),
            )
        except Exception as error:
            self._log_cache_failure("write", error)

    async def asave(self, must_create=False):
        if self.session_key is None:
            return await self.acreate()

        await DatabaseSessionStore.asave(self, must_create)
        try:
            await self._cache.aset(
                await self.acache_key(),
                self._session,
                await self.aget_expiry_age(),
            )
        except Exception as error:
            self._log_cache_failure("write", error)

    def delete(self, session_key=None):
        resolved_session_key = session_key or self.session_key
        DatabaseSessionStore.delete(self, resolved_session_key)
        if resolved_session_key is None:
            return

        try:
            self._cache.delete(self.cache_key_prefix + resolved_session_key)
        except Exception as error:
            self._log_cache_failure("delete", error)

    async def adelete(self, session_key=None):
        resolved_session_key = session_key or self.session_key
        await DatabaseSessionStore.adelete(self, resolved_session_key)
        if resolved_session_key is None:
            return

        try:
            await self._cache.adelete(
                self.cache_key_prefix + resolved_session_key
            )
        except Exception as error:
            self._log_cache_failure("delete", error)
