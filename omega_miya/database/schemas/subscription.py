"""
@Author         : Ailitonia
@Date           : 2022/03/26 18:50
@FileName       : subscription.py
@Project        : nonebot2_miya 
@Description    : Subscription Model
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
from ..model import SubscriptionOrm


class SubscriptionUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    sub_source_id: int
    entity_id: int


class SubscriptionRequireModel(SubscriptionUniqueModel):
    """数据库对象变更请求必须数据模型"""
    sub_info: Optional[str]


class SubscriptionModel(SubscriptionRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class SubscriptionModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["SubscriptionModel"]


class SubscriptionModelListResult(DatabaseModelListResult):
    """Subscription 查询结果类"""
    result: List["SubscriptionModel"]


class Subscription(BaseDatabase):
    orm_model = SubscriptionOrm
    unique_model = SubscriptionUniqueModel
    require_model = SubscriptionRequireModel
    data_model = SubscriptionModel
    self_model: SubscriptionUniqueModel

    def __init__(self, sub_source_id: int, entity_id: int):
        self.self_model = SubscriptionUniqueModel(sub_source_id=sub_source_id, entity_id=entity_id)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.sub_source_id)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.sub_source_id == self.self_model.sub_source_id).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            order_by(self.orm_model.sub_source_id)
        return stmt

    def _make_unique_self_update(self, new_model: SubscriptionUniqueModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.sub_source_id == self.self_model.sub_source_id).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.sub_source_id == self.self_model.sub_source_id).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, sub_info: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            sub_source_id=self.self_model.sub_source_id,
            entity_id=self.self_model.entity_id,
            sub_info=sub_info
        ))

    async def add_upgrade_unique_self(self, sub_info: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            sub_source_id=self.self_model.sub_source_id,
            entity_id=self.self_model.entity_id,
            sub_info=sub_info
        ))

    async def query(self) -> SubscriptionModelResult:
        return SubscriptionModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> SubscriptionModelListResult:
        return SubscriptionModelListResult.parse_obj(await cls._query_all())


__all__ = [
    'Subscription',
    'SubscriptionModel'
]
