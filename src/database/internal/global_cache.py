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

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import GlobalCacheOrm


class GlobalCache(BaseDataOutModel):
    """全局缓存数据"""
    cache_name: str
    cache_key: str
    cache_value: str
    expired_at: datetime
    created_at: datetime | None
    updated_at: datetime | None


class GlobalCacheDAL(BaseDataAccessLayer[GlobalCacheOrm, GlobalCache]):
    """全局缓存"""

    async def _count_all(self) -> int:
        """查询全表行数"""
        stmt = select(func.count()).select_from(GlobalCacheOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表, 敏感操作, 方法内不执行 commit, 可由外层事务 rollback"""
        await self.db_session.execute(delete(GlobalCacheOrm))
        self.db_session.expunge_all()

    async def _select_unique(
            self,
            cache_name: str,
            cache_key: str,
            *,
            include_expired: bool = False,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> GlobalCacheOrm:
        stmt = (select(GlobalCacheOrm)
                .where(GlobalCacheOrm.cache_name == cache_name)
                .where(GlobalCacheOrm.cache_key == cache_key))

        if not include_expired:
            stmt = stmt.where(GlobalCacheOrm.expired_at >= datetime.now())

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_unique(
            self,
            cache_name: str,
            cache_key: str,
            *,
            include_expired: bool = False,
            populate_existing: bool = False,
    ) -> GlobalCache:
        item = await self._select_unique(
            cache_name,
            cache_key,
            include_expired=include_expired,
            populate_existing=populate_existing,
        )
        return GlobalCache.model_validate(item)

    async def query_series(
            self,
            cache_name: str,
            *,
            include_expired: bool = False,
            populate_existing: bool = False,
    ) -> list[GlobalCache]:
        stmt = select(GlobalCacheOrm).where(GlobalCacheOrm.cache_name == cache_name)

        if not include_expired:
            stmt = stmt.where(GlobalCacheOrm.expired_at >= datetime.now())

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[GlobalCache], (await self.db_session.execute(stmt)).scalars().all())

    async def add(
            self,
            cache_name: str,
            cache_key: str,
            cache_value: str,
            expired_time: datetime | timedelta | None = None,
    ) -> GlobalCache:
        """向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        """
        if expired_time is None:
            expired_at = datetime(year=9999, month=12, day=31)
        elif isinstance(expired_time, datetime):
            expired_at = expired_time
        else:
            expired_at = datetime.now() + expired_time
        new_obj = GlobalCacheOrm(
            cache_name=cache_name,
            cache_key=cache_key,
            cache_value=cache_value,
            expired_at=expired_at,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        await self.db_session.refresh(new_obj)
        return GlobalCache.model_validate(new_obj)

    async def add_update_exist(
            self,
            cache_name: str,
            cache_key: str,
            cache_value: str,
            expired_time: datetime | timedelta | None = None,
    ) -> GlobalCache:
        """向数据库插入新行, 存在则更新

        通过捕获异常实现, 性能较差, 且并发时仍可能出现死锁或需要重试
        """
        if expired_time is None:
            expired_at = datetime(year=9999, month=12, day=31)
        elif isinstance(expired_time, datetime):
            expired_at = expired_time
        else:
            expired_at = datetime.now() + expired_time

        new_obj = GlobalCacheOrm(
            cache_name=cache_name,
            cache_key=cache_key,
            cache_value=cache_value,
            expired_at=expired_at,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
            await session.refresh(new_obj)
            return GlobalCache.model_validate(new_obj)
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_unique(
                    cache_name,
                    cache_key,
                    include_expired=True,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.cache_value = cache_value
                exist_obj.expired_at = expired_at
                await session.flush()
            await session.refresh(exist_obj)
            return GlobalCache.model_validate(exist_obj)

    async def delete_series_expired(self, cache_name: str) -> None:
        stmt = (delete(GlobalCacheOrm)
                .where(GlobalCacheOrm.cache_name == cache_name)
                .where(GlobalCacheOrm.expired_at <= datetime.now()))
        await self.db_session.execute(stmt)

    async def delete_all_expired(self) -> None:
        stmt = delete(GlobalCacheOrm).where(GlobalCacheOrm.expired_at <= datetime.now())
        await self.db_session.execute(stmt)


__all__ = [
    'GlobalCache',
    'GlobalCacheDAL',
]
