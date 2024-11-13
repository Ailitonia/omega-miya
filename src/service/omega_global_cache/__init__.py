"""
@Author         : Ailitonia
@Date           : 2024/11/13 17:53:20
@FileName       : omega_global_cache.py
@Project        : omega-miya
@Description    : Omega 全局缓存
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime, timedelta

from sqlalchemy.exc import NoResultFound

from src.database import GlobalCacheDAL, begin_db_session


class OmegaGlobalCache(object):
    """Omega 全局缓存"""

    def __init__(self, cache_name: str, *, ttl: int = 86400):
        self._cache_name = cache_name
        self._ttl = ttl

        # 内存级缓存, 对象存续期间永不失效
        self._cache: dict[str, str] = {}

    @property
    def expired_at(self) -> datetime:
        return datetime.now() + timedelta(seconds=self._ttl)

    async def _query_db_unique(self, key: str) -> str:
        async with begin_db_session() as session:
            result = await GlobalCacheDAL(session).query_unique(cache_name=self._cache_name, cache_key=key)
        return result.cache_value

    async def _query_db_series(self) -> dict[str, str]:
        async with begin_db_session() as session:
            result = await GlobalCacheDAL(session).query_series(cache_name=self._cache_name)
        return {x.cache_key: x.cache_value for x in result}

    async def _clean_db_expired(self) -> None:
        async with begin_db_session() as session:
            await GlobalCacheDAL(session).delete_series_expired(cache_name=self._cache_name)

    async def _save_db(self, key: str, value: str) -> None:
        if len(value) > 4096:
            raise ValueError('the length of value must less than 4096')

        async with begin_db_session() as session:
            await GlobalCacheDAL(session).upsert(
                cache_name=self._cache_name, cache_key=key, cache_value=value, expired_time=self.expired_at
            )

    async def load(self, key: str) -> str | None:
        """读取缓存"""
        if (value := self._cache.get(key, None)) is not None:
            return value

        try:
            result = await self._query_db_unique(key=key)
            self._cache.update({key: result})
            return result
        except NoResultFound:
            return None

    async def save(self, key: str, value: str) -> None:
        """更新内部内存缓存及数据库缓存"""
        self._cache.update({key: value})
        await self._save_db(key=key, value=value)

    def update_internal(self, key: str, value: str) -> None:
        """仅更新内部内存缓存"""
        self._cache.update({key: value})

    def clear_internal(self):
        """仅清空内存缓存"""
        self._cache.clear()

    async def sync_internal(self):
        """同步内部内存缓存与数据库缓存"""
        await self._clean_db_expired()
        exists_data = await self._query_db_series()
        exists_data.update(self._cache)

        for key, value in exists_data.items():
            await self.save(key=key, value=value)


__all__ = [
    'OmegaGlobalCache'
]
