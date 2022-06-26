"""
@Author         : Ailitonia
@Date           : 2022/03/20 18:43
@FileName       : statistic.py
@Project        : nonebot2_miya 
@Description    : Statistic model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import update, delete, desc
from sqlalchemy.future import select
from sqlalchemy.sql.expression import func
from pydantic import parse_obj_as

from omega_miya.result import BoolResult
from .base_model import (BaseDatabaseModel, BaseDatabase, Select, Update, Delete,
                         DatabaseModelResult, DatabaseModelListResult)
from ..model import StatisticOrm


class StatisticUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    module_name: str
    plugin_name: str
    bot_self_id: str
    call_id: str
    call_time: datetime


class StatisticRequireModel(StatisticUniqueModel):
    """数据库对象变更请求必须数据模型"""
    call_info: Optional[str]


class StatisticModel(StatisticRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class StatisticModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["StatisticModel"]


class StatisticModelListResult(DatabaseModelListResult):
    """Statistic 查询结果类"""
    result: List["StatisticModel"]


class CountStatisticModel(BaseDatabaseModel):
    """查询统计信息结果类"""
    custom_name: str
    call_count: int


class Statistic(BaseDatabase):
    orm_model = StatisticOrm
    unique_model = StatisticUniqueModel
    require_model = StatisticRequireModel
    data_model = StatisticModel
    self_model: StatisticUniqueModel

    def __init__(self, module_name: str, plugin_name: str, bot_self_id: str, call_id: str, call_time: datetime):
        self.self_model = StatisticUniqueModel(
            module_name=module_name,
            plugin_name=plugin_name,
            bot_self_id=bot_self_id,
            call_id=call_id,
            call_time=call_time)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(desc(cls.orm_model.call_time))
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).\
            where(self.orm_model.module_name == self.self_model.module_name).\
            where(self.orm_model.plugin_name == self.self_model.plugin_name).\
            where(self.orm_model.bot_self_id == self.self_model.bot_self_id).\
            where(self.orm_model.call_id == self.self_model.call_id).\
            where(self.orm_model.call_time == self.self_model.call_time).\
            order_by(desc(self.orm_model.call_time))
        return stmt

    def _make_unique_self_update(self, new_model: StatisticRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.module_name == self.self_model.module_name).\
            where(self.orm_model.plugin_name == self.self_model.plugin_name).\
            where(self.orm_model.bot_self_id == self.self_model.bot_self_id).\
            where(self.orm_model.call_id == self.self_model.call_id).\
            where(self.orm_model.call_time == self.self_model.call_time).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.module_name == self.self_model.module_name).\
            where(self.orm_model.plugin_name == self.self_model.plugin_name).\
            where(self.orm_model.bot_self_id == self.self_model.bot_self_id).\
            where(self.orm_model.call_id == self.self_model.call_id).\
            where(self.orm_model.call_time == self.self_model.call_time).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, call_info: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            module_name=self.self_model.module_name,
            plugin_name=self.self_model.plugin_name,
            bot_self_id=self.self_model.bot_self_id,
            call_id=self.self_model.call_id,
            call_time=self.self_model.call_time,
            call_info=call_info
        ))

    async def add_upgrade_unique_self(self, call_info: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            module_name=self.self_model.module_name,
            plugin_name=self.self_model.plugin_name,
            bot_self_id=self.self_model.bot_self_id,
            call_id=self.self_model.call_id,
            call_time=self.self_model.call_time,
            call_info=call_info
        ))

    async def query(self) -> StatisticModelResult:
        return StatisticModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> StatisticModelListResult:
        return StatisticModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_by_condition(
            cls,
            bot_self_id: Optional[str] = None,
            call_id: Optional[str] = None,
            start_time: Optional[datetime] = None) -> list[CountStatisticModel]:
        """按条件查询统计信息

        :param bot_self_id: bot id, 为空则返回全部
        :param call_id: 调用id, 为空则返回全部
        :param start_time: 统计起始时间, 为空则返回全部
        """
        stmt = select(func.count(cls.orm_model.plugin_name), cls.orm_model.plugin_name).with_for_update(read=True)
        if bot_self_id:
            stmt = stmt.where(cls.orm_model.bot_self_id == bot_self_id)
        if call_id:
            stmt = stmt.where(cls.orm_model.call_id == call_id)
        if start_time:
            stmt = stmt.where(cls.orm_model.call_time >= start_time)
        stmt = stmt.group_by(cls.orm_model.plugin_name)

        result = await cls._query_custom_all(stmt=stmt, scalar=False)
        data = [{'custom_name': plugin_name, 'call_count': count} for count, plugin_name in result]
        return parse_obj_as(list[CountStatisticModel], data)


__all__ = [
    'Statistic'
]
