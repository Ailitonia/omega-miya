"""
@Author         : Ailitonia
@Date           : 2022/12/02 22:11
@FileName       : statistic.py
@Project        : nonebot2_miya
@Description    : Statistic DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import Any

from sqlalchemy import delete, desc, func, select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import StatisticOrm


class Statistic(BaseDataOutModel):
    """统计信息数据"""
    id: int
    plugin_name: str
    module_name: str
    call_timestamp: int
    call_entity_meta: dict[str, Any]
    call_data: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None


class StatisticDAL(BaseDataAccessLayer[StatisticOrm, Statistic]):
    """统计信息"""

    async def _count_all(self) -> int:
        """查询全表行数"""
        stmt = select(func.count()).select_from(StatisticOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表, 敏感操作, 方法内不执行 commit, 可由外层事务 rollback"""
        await self.db_session.execute(delete(StatisticOrm))
        self.db_session.expunge_all()

    async def _select_unique(self, *args, **kwargs) -> StatisticOrm:
        """查询单条统计记录无意义, 不予实现"""
        raise NotImplementedError

    async def query_unique(self, *args, **kwargs) -> Statistic:
        """查询单条统计记录无意义, 不予实现"""
        raise NotImplementedError

    async def query_by_condition(
            self,
            *,
            start_timestamp: datetime | int | None = None,
            plugin_name: str | None = None,
            module_name: str | None = None,
            page: int = 1,
            size: int = 500,
    ) -> list[Statistic]:
        """按条件查询统计信息

        :param start_timestamp: 统计起始时间, 为空则返回全部
        :param plugin_name: 插件名, 为空则返回全部
        :param module_name: 插件模块名, 为空则返回全部
        :param page: 分页
        :param size: 每页数量
        """
        stmt = select(StatisticOrm).order_by(desc(StatisticOrm.call_timestamp))

        if start_timestamp is not None:
            if isinstance(start_timestamp, datetime):
                stmt = stmt.where(StatisticOrm.call_timestamp >= int(start_timestamp.timestamp()))
            else:
                stmt = stmt.where(StatisticOrm.call_timestamp >= start_timestamp)

        if plugin_name is not None:
            stmt = stmt.where(StatisticOrm.plugin_name == plugin_name)

        if module_name is not None:
            stmt = stmt.where(StatisticOrm.module_name == module_name)

        # 结果数量限制
        stmt = stmt.limit(size).offset((page - 1) * size)

        return parse_obj_as(list[Statistic], (await self.db_session.execute(stmt)).scalars().all())

    async def count_by_condition(
            self,
            *,
            start_timestamp: datetime | int | None = None,
            plugin_name: str | None = None,
            module_name: str | None = None,
    ) -> int:
        """按条件查询统计信息条数

        :param plugin_name: 插件名, 为空则返回全部
        :param module_name: 插件模块名, 为空则返回全部
        :param start_timestamp: 统计起始时间, 为空则返回全部
        """
        stmt = select(func.count()).select_from(StatisticOrm)

        if start_timestamp is not None:
            if isinstance(start_timestamp, datetime):
                stmt = stmt.where(StatisticOrm.call_timestamp >= int(start_timestamp.timestamp()))
            else:
                stmt = stmt.where(StatisticOrm.call_timestamp >= start_timestamp)

        if plugin_name is not None:
            stmt = stmt.where(StatisticOrm.plugin_name == plugin_name)

        if module_name is not None:
            stmt = stmt.where(StatisticOrm.module_name == module_name)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def add(
            self,
            plugin_name: str,
            module_name: str,
            call_timestamp: int,
            call_entity_meta: dict[str, Any],
            call_data: dict[str, Any],
    ) -> Statistic:
        """向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        """
        call_entity_meta = parse_obj_as(dict[str, Any], call_entity_meta)
        call_data = parse_obj_as(dict[str, Any], call_data)

        new_obj = StatisticOrm(
            plugin_name=plugin_name,
            module_name=module_name,
            call_timestamp=call_timestamp,
            call_entity_meta=call_entity_meta,
            call_data=call_data,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        return Statistic.model_validate(new_obj)

    async def delete_period_older(
            self,
            before_timestamp: int,
            *,
            plugin_name: str | None = None,
            module_name: str | None = None,
    ) -> None:
        stmt = (delete(StatisticOrm).where(StatisticOrm.call_timestamp <= before_timestamp))

        if plugin_name is not None:
            stmt = stmt.where(StatisticOrm.plugin_name == plugin_name)

        if module_name is not None:
            stmt = stmt.where(StatisticOrm.module_name == module_name)

        await self.db_session.execute(stmt)


__all__ = [
    'Statistic',
    'StatisticDAL',
]
