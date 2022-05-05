"""
@Author         : Ailitonia
@Date           : 2022/03/26 17:11
@FileName       : history.py
@Project        : nonebot2_miya 
@Description    : HistoryOrm Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import update, delete, desc
from sqlalchemy.future import select
from omega_miya.result import BoolResult
from .base_model import (BaseDatabaseModel, BaseDatabase, Select, Update, Delete,
                         DatabaseModelResult, DatabaseModelListResult)
from ..model import HistoryOrm


class HistoryUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    time: int
    self_id: str
    event_type: str
    event_id: str


class HistoryRequireModel(HistoryUniqueModel):
    """数据库对象变更请求必须数据模型"""
    raw_data: str
    msg_data: Optional[str]


class HistoryModel(HistoryRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class HistoryModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["HistoryModel"]


class HistoryModelListResult(DatabaseModelListResult):
    """History 查询结果类"""
    result: List["HistoryModel"]


class History(BaseDatabase):
    orm_model = HistoryOrm
    unique_model = HistoryUniqueModel
    require_model = HistoryRequireModel
    data_model = HistoryModel
    self_model: HistoryUniqueModel

    def __init__(self, time: int, self_id: str, event_type: str, event_id: str):
        self.self_model = HistoryUniqueModel(time=time, self_id=self_id, event_type=event_type, event_id=event_id)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(desc(cls.orm_model.time))
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.time == self.self_model.time).\
            where(self.orm_model.self_id == self.self_model.self_id). \
            where(self.orm_model.event_type == self.self_model.event_type).\
            where(self.orm_model.event_id == self.self_model.event_id).\
            order_by(desc(self.orm_model.time))
        return stmt

    def _make_unique_self_update(self, new_model: HistoryRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.time == self.self_model.time).\
            where(self.orm_model.self_id == self.self_model.self_id). \
            where(self.orm_model.event_type == self.self_model.event_type).\
            where(self.orm_model.event_id == self.self_model.event_id).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.time == self.self_model.time).\
            where(self.orm_model.self_id == self.self_model.self_id). \
            where(self.orm_model.event_type == self.self_model.event_type).\
            where(self.orm_model.event_id == self.self_model.event_id).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, raw_data: str, msg_data: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            time=self.self_model.time,
            self_id=self.self_model.self_id,
            event_type=self.self_model.event_type,
            event_id=self.self_model.event_id,
            raw_data=raw_data,
            msg_data=msg_data
        ))

    async def add_upgrade_unique_self(self, raw_data: str, msg_data: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            time=self.self_model.time,
            self_id=self.self_model.self_id,
            event_type=self.self_model.event_type,
            event_id=self.self_model.event_id,
            raw_data=raw_data,
            msg_data=msg_data
        ))

    async def query(self) -> HistoryModelResult:
        return HistoryModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> HistoryModelListResult:
        return HistoryModelListResult.parse_obj(await cls._query_all())


__all__ = [
    'History'
]
