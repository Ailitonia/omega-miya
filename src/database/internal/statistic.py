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
from typing import Optional

from sqlalchemy import update, delete, desc
from sqlalchemy.future import select
from sqlalchemy.sql.expression import func

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import StatisticOrm


class Statistic(BaseDataQueryResultModel):
    """统计信息 Model"""
    id: int
    module_name: str
    plugin_name: str
    bot_self_id: str
    parent_entity_id: str
    entity_id: str
    call_time: datetime
    call_info: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CountStatisticModel(BaseDataQueryResultModel):
    """查询统计信息结果 Model"""
    custom_name: str
    call_count: int


class StatisticDAL(BaseDataAccessLayerModel[Statistic]):
    """统计信息 数据库操作对象"""

    async def query_unique(self):
        raise NotImplementedError('method not supported')

    async def count_by_condition(
            self,
            bot_self_id: Optional[str] = None,
            parent_entity_id: Optional[str] = None,
            entity_id: Optional[str] = None,
            start_time: Optional[datetime] = None
    ) -> list[CountStatisticModel]:
        """按条件查询统计信息

        :param bot_self_id: bot id, 为空则返回全部
        :param parent_entity_id: 父对象 id, 为空则返回全部
        :param entity_id: 调用对象 id, 为空则返回全部
        :param start_time: 统计起始时间, 为空则返回全部
        """
        stmt = select(func.count(StatisticOrm.plugin_name), StatisticOrm.plugin_name)
        if bot_self_id is not None:
            stmt = stmt.where(StatisticOrm.bot_self_id == bot_self_id)
        if parent_entity_id is not None:
            stmt = stmt.where(StatisticOrm.parent_entity_id == parent_entity_id)
        if entity_id is not None:
            stmt = stmt.where(StatisticOrm.entity_id == entity_id)
        if start_time is not None:
            stmt = stmt.where(StatisticOrm.call_time >= start_time)
        stmt = stmt.group_by(StatisticOrm.plugin_name)
        session_result = await self.db_session.execute(stmt)
        data = [{'custom_name': plugin_name, 'call_count': count} for count, plugin_name in session_result.all()]
        return parse_obj_as(list[CountStatisticModel], data)

    async def query_all(self) -> list[Statistic]:
        stmt = select(StatisticOrm).order_by(desc(StatisticOrm.call_time))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Statistic], session_result.scalars().all())

    async def add(
            self,
            module_name: str,
            plugin_name: str,
            bot_self_id: str,
            parent_entity_id: str,
            entity_id: str,
            call_time: datetime,
            call_info: Optional[str] = None
    ) -> None:
        new_obj = StatisticOrm(module_name=module_name, plugin_name=plugin_name, bot_self_id=bot_self_id,
                               parent_entity_id=parent_entity_id, entity_id=entity_id,
                               call_time=call_time, call_info=call_info, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            module_name: Optional[str] = None,
            plugin_name: Optional[str] = None,
            bot_self_id: Optional[str] = None,
            parent_entity_id: Optional[str] = None,
            entity_id: Optional[str] = None,
            call_time: Optional[datetime] = None,
            call_info: Optional[str] = None
    ) -> None:
        stmt = update(StatisticOrm).where(StatisticOrm.id == id_)
        if module_name is not None:
            stmt = stmt.values(module_name=module_name)
        if plugin_name is not None:
            stmt = stmt.values(plugin_name=plugin_name)
        if bot_self_id is not None:
            stmt = stmt.values(bot_self_id=bot_self_id)
        if parent_entity_id is not None:
            stmt = stmt.values(parent_entity_id=parent_entity_id)
        if entity_id is not None:
            stmt = stmt.values(entity_id=entity_id)
        if call_time is not None:
            stmt = stmt.values(call_time=call_time)
        if call_info is not None:
            stmt = stmt.values(call_info=call_info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(StatisticOrm).where(StatisticOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'CountStatisticModel',
    'Statistic',
    'StatisticDAL',
]
