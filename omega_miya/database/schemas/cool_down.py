"""
@Author         : Ailitonia
@Date           : 2022/03/27 12:33
@FileName       : cool_down.py
@Project        : nonebot2_miya 
@Description    : CoolDown Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import update, delete
from sqlalchemy.future import select
from omega_miya.result import BoolResult
from .base_model import (BaseDatabaseModel, BaseDatabase, Select, Update, Delete,
                         DatabaseModelResult, DatabaseModelListResult)
from ..model import CoolDownOrm


class CoolDownUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    entity_id: int
    event: str


class CoolDownRequireModel(CoolDownUniqueModel):
    """数据库对象变更请求必须数据模型"""
    stop_at: datetime
    description: Optional[str]


class CoolDownModel(CoolDownRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class CoolDownModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["CoolDownModel"]


class CoolDownModelListResult(DatabaseModelListResult):
    """CoolDown 查询结果类"""
    result: List["CoolDownModel"]


class CoolDown(BaseDatabase):
    orm_model = CoolDownOrm
    unique_model = CoolDownUniqueModel
    require_model = CoolDownRequireModel
    data_model = CoolDownModel
    self_model: CoolDownUniqueModel

    def __init__(self, entity_id: int, event: str):
        self.self_model = CoolDownUniqueModel(entity_id=entity_id, event=event)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.entity_id)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.event == self.self_model.event).\
            order_by(self.orm_model.entity_id)
        return stmt

    def _make_unique_self_update(self, new_model: CoolDownRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.event == self.self_model.event).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.event == self.self_model.event).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, stop_at: datetime, description: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            event=self.self_model.event,
            stop_at=stop_at,
            description=description
        ))

    async def add_upgrade_unique_self(self, stop_at: datetime, description: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            event=self.self_model.event,
            stop_at=stop_at,
            description=description
        ))

    async def query(self) -> CoolDownModelResult:
        return CoolDownModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> CoolDownModelListResult:
        return CoolDownModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def clear_expired(cls) -> BoolResult:
        stmt = delete(cls.orm_model).\
            where(cls.orm_model.stop_at <= datetime.now()).\
            execution_options(synchronize_session="fetch")
        return await cls._execute(stmt=stmt)


__all__ = [
    'CoolDown',
    'CoolDownModel'
]
