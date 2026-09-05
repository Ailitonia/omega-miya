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

from nonebot.log import logger
from sqlalchemy.exc import NoResultFound

from src.database import GlobalCacheDAL

_REGISTERED_CACHE: set[str] = set()
"""缓存全局已注册的缓存项"""
_CACHE_NAME_MAX_LENGTH = 64
"""缓存名称最大长度 (与数据库表字段 String(64) 一致)"""
_CACHE_KEY_MAX_LENGTH = 64
"""缓存键最大长度 (与数据库表字段 String(64) 一致)"""


class OmegaGlobalCache:
    """Omega 全局缓存

    Note: cache_name 与 cache_key 的长度受数据库表字段 String(64) 限制, 注册与读写时将主动校验, 超长抛出 ValueError
    """

    def __init__(self, cache_name: str, *, default_ttl: int = 86400):
        self._cache_name = cache_name.strip()
        self._ttl = default_ttl

        # 校验 cache_name 有效性
        if not self._cache_name:
            raise ValueError('Invalid cache_name')
        if len(self._cache_name) > _CACHE_NAME_MAX_LENGTH:
            raise ValueError(f'Invalid cache_name: length exceeds {_CACHE_NAME_MAX_LENGTH}')

        # 检查 cache_name 是否已被注册
        if self._cache_name in _REGISTERED_CACHE:
            raise ValueError(f'OmegaGlobalCache {self._cache_name!r} already registered')
        _REGISTERED_CACHE.add(self._cache_name)
        logger.info(f'OmegaGlobalCache | {self._cache_name!r} has been registered')

        # 内存级缓存, 对象存续期间永不失效
        self._cache: dict[str, str] = {}

    @property
    def expired_at(self) -> datetime:
        """默认过期时间"""
        return datetime.now() + timedelta(seconds=self._ttl)

    def set_expired_at(self, ttl_delta: int = 0) -> datetime:
        """手动调整过期时间"""
        return self.expired_at + timedelta(seconds=ttl_delta)

    @staticmethod
    def _validate_cache_key(key: str) -> None:
        """校验 cache_key 有效性, 非法键抛出 ValueError"""
        if not key:
            raise ValueError('Invalid cache_key')
        if len(key) > _CACHE_KEY_MAX_LENGTH:
            raise ValueError(f'Invalid cache_key: length exceeds {_CACHE_KEY_MAX_LENGTH}')

    async def _query_key_value(self, key: str, *, include_expired: bool = False) -> str:
        """从数据库查询键值对的值, 不存在则会抛出 NoResultFound"""
        async with GlobalCacheDAL.create() as dal:
            result = await dal.query_unique(self._cache_name, key, include_expired=include_expired)
        return result.cache_value

    async def _query_all_values(self, *, include_expired: bool = False) -> dict[str, str]:
        """从数据库查询所有的键值对"""
        async with GlobalCacheDAL.create() as dal:
            result = await dal.query_series(self._cache_name, include_expired=include_expired)
        return {x.cache_key: x.cache_value for x in result}

    async def _clean_db_expired(self) -> None:
        """清理数据库中已过期的键值对"""
        async with GlobalCacheDAL.create() as dal:
            await dal.delete_series_expired(cache_name=self._cache_name)

    async def _upsert_key_value(self, key: str, value: str, *, ttl_delta: int = 0) -> str:
        """向数据库中写入键值对"""
        async with GlobalCacheDAL.create() as dal:
            result = await dal.add_update_exist(
                cache_name=self._cache_name,
                cache_key=key,
                cache_value=value,
                expired_time=self.set_expired_at(ttl_delta=ttl_delta),
            )
        return result.cache_value

    async def load(self, key: str) -> str | None:
        """读取缓存值"""
        self._validate_cache_key(key)
        if (value := self._cache.get(key, None)) is not None:
            return value

        try:
            value = await self._query_key_value(key=key)
            self._cache[key] = value
            return value
        except NoResultFound:
            return None

    async def save(self, key: str, value: str, *, ttl_delta: int = 0) -> str:
        """写入缓存值"""
        self._validate_cache_key(key)
        value = await self._upsert_key_value(key=key, value=value, ttl_delta=ttl_delta)
        self._cache[key] = value
        return value

    async def sync_internal(self) -> None:
        """同步内部内存缓存与数据库缓存一致"""
        await self._clean_db_expired()
        self._cache.clear()
        self._cache.update(await self._query_all_values())


__all__ = [
    'OmegaGlobalCache'
]
