"""
@Author         : Ailitonia
@Date           : 2022/03/26 17:40
@FileName       : subscription_source.py
@Project        : nonebot2_miya 
@Description    : SubscriptionSource Model
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
from ..model import SubscriptionSourceOrm, SubscriptionOrm


class SubscriptionSourceUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    sub_type: str
    sub_id: str


class SubscriptionSourceRequireModel(SubscriptionSourceUniqueModel):
    """数据库对象变更请求必须数据模型"""
    sub_user_name: str
    sub_info: Optional[str]


class SubscriptionSourceModel(SubscriptionSourceRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class SubscriptionSourceModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["SubscriptionSourceModel"]


class SubscriptionSourceModelListResult(DatabaseModelListResult):
    """SubscriptionSource 查询结果类"""
    result: List["SubscriptionSourceModel"]


class SubscriptionSource(BaseDatabase):
    orm_model = SubscriptionSourceOrm
    unique_model = SubscriptionSourceUniqueModel
    require_model = SubscriptionSourceRequireModel
    data_model = SubscriptionSourceModel
    self_model: SubscriptionSourceUniqueModel

    def __init__(self, sub_type: str, sub_id: str):
        self.self_model = SubscriptionSourceUniqueModel(sub_type=sub_type, sub_id=sub_id)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.sub_type)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.sub_type == self.self_model.sub_type).\
            where(self.orm_model.sub_id == self.self_model.sub_id).\
            order_by(self.orm_model.sub_id)
        return stmt

    def _make_unique_self_update(self, new_model: SubscriptionSourceRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.sub_type == self.self_model.sub_type).\
            where(self.orm_model.sub_id == self.self_model.sub_id).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.sub_type == self.self_model.sub_type).\
            where(self.orm_model.sub_id == self.self_model.sub_id).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, sub_user_name: str, sub_info: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            sub_type=self.self_model.sub_type,
            sub_id=self.self_model.sub_id,
            sub_user_name=sub_user_name,
            sub_info=sub_info
        ))

    async def add_upgrade_unique_self(self, sub_user_name: str, sub_info: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            sub_type=self.self_model.sub_type,
            sub_id=self.self_model.sub_id,
            sub_user_name=sub_user_name,
            sub_info=sub_info
        ))

    async def query(self) -> SubscriptionSourceModelResult:
        return SubscriptionSourceModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> SubscriptionSourceModelListResult:
        return SubscriptionSourceModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_all_by_type(cls, sub_type: str) -> SubscriptionSourceModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.sub_type == sub_type).order_by(cls.orm_model.sub_id)
        return SubscriptionSourceModelListResult.parse_obj(await cls._query_all(stmt=stmt))

    @classmethod
    async def query_all_by_subscribed_entity_index_id(
            cls, id_: int, *, sub_type: Optional[str] = None) -> SubscriptionSourceModelListResult:
        """根据 RelatedEntity 的索引 id 查询所有订阅了的来源

        :param id_: RelatedEntity 索引 id
        :param sub_type: 筛选 sub_type
        """
        stmt = select(cls.orm_model).with_for_update(read=True).\
            join(SubscriptionOrm).\
            where(SubscriptionOrm.entity_id == id_).\
            order_by(cls.orm_model.id)
        if sub_type is not None:
            stmt = stmt.where(cls.orm_model.sub_type == sub_type)
        return SubscriptionSourceModelListResult.parse_obj(await cls._query_all(stmt=stmt))


__all__ = [
    'SubscriptionSource',
    'SubscriptionSourceModel'
]
