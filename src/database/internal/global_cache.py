"""
@Author         : Ailitonia
@Date           : 2024/11/12 17:16:22
@FileName       : global_cache.py
@Project        : omega-miya
@Description    : Global Cache DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import GlobalCacheOrm


class GlobalCache(BaseDataQueryResultModel):
    """全局缓存 Model"""
    cache_name: str
    cache_key: str
    cache_value: str
    expired_at: datetime
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class GlobalCacheDAL(BaseDataAccessLayerModel[GlobalCacheOrm, GlobalCache]):
    """全局缓存 数据库操作对象"""

    async def query_unique(self, cache_name: str, cache_key: str, *, include_expired: bool = False) -> GlobalCache:
        stmt = (select(GlobalCacheOrm)
                .where(GlobalCacheOrm.cache_name == cache_name)
                .where(GlobalCacheOrm.cache_key == cache_key))

        if not include_expired:
            stmt = stmt.where(GlobalCacheOrm.expired_at >= datetime.now())

        session_result = await self.db_session.execute(stmt)
        return GlobalCache.model_validate(session_result.scalar_one())

    async def query_series(self, cache_name: str, *, include_expired: bool = False) -> list[GlobalCache]:
        stmt = select(GlobalCacheOrm).where(GlobalCacheOrm.cache_name == cache_name)

        if not include_expired:
            stmt = stmt.where(GlobalCacheOrm.expired_at >= datetime.now())

        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[GlobalCache], session_result.scalars().all())

    async def query_all(self, *, include_expired: bool = False) -> list[GlobalCache]:
        stmt = select(GlobalCacheOrm).order_by(GlobalCacheOrm.cache_name)

        if not include_expired:
            stmt = stmt.where(GlobalCacheOrm.expired_at >= datetime.now())

        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[GlobalCache], session_result.scalars().all())

    async def add(
            self,
            cache_name: str,
            cache_key: str,
            cache_value: str,
            expired_time: Optional[datetime | timedelta] = None,
    ) -> None:
        if expired_time is None:
            expired_at = datetime(year=9999, month=12, day=31)
        elif isinstance(expired_time, datetime):
            expired_at = expired_time
        else:
            expired_at = datetime.now() + expired_time
        new_obj = GlobalCacheOrm(cache_name=cache_name, cache_key=cache_key,
                                 cache_value=cache_value, expired_at=expired_at, created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(
            self,
            cache_name: str,
            cache_key: str,
            cache_value: str,
            expired_time: Optional[datetime | timedelta] = None,
    ) -> None:
        if expired_time is None:
            expired_at = datetime(year=9999, month=12, day=31)
        elif isinstance(expired_time, datetime):
            expired_at = expired_time
        else:
            expired_at = datetime.now() + expired_time
        new_obj = GlobalCacheOrm(cache_name=cache_name, cache_key=cache_key,
                                 cache_value=cache_value, expired_at=expired_at, updated_at=datetime.now())
        await self._merge(new_obj)

    async def update(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def delete(self, cache_name: str, cache_key: str) -> None:
        stmt = (delete(GlobalCacheOrm)
                .where(GlobalCacheOrm.cache_name == cache_name)
                .where(GlobalCacheOrm.cache_key == cache_key))
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete_series_expired(self, cache_name: str) -> None:
        stmt = (delete(GlobalCacheOrm)
                .where(GlobalCacheOrm.cache_name == cache_name)
                .where(GlobalCacheOrm.expired_at <= datetime.now()))
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete_all_expired(self) -> None:
        stmt = delete(GlobalCacheOrm).where(GlobalCacheOrm.expired_at <= datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'GlobalCache',
    'GlobalCacheDAL',
]
