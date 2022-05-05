"""
@Author         : Ailitonia
@Date           : 2022/03/23 21:38
@FileName       : friendship.py
@Project        : nonebot2_miya 
@Description    : Friendship model
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
from ..model import FriendshipOrm


class FriendshipUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    entity_id: int


class FriendshipRequireModel(FriendshipUniqueModel):
    """数据库对象变更请求必须数据模型"""
    status: str
    mood: float
    friend_ship: float
    energy: float
    currency: float
    response_threshold: float


class FriendshipModel(FriendshipRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class FriendshipModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["FriendshipModel"]


class FriendshipModelListResult(DatabaseModelListResult):
    """Friendship 查询结果类"""
    result: List["FriendshipModel"]


class Friendship(BaseDatabase):
    orm_model = FriendshipOrm
    unique_model = FriendshipUniqueModel
    require_model = FriendshipRequireModel
    data_model = FriendshipModel
    self_model: FriendshipUniqueModel

    def __init__(self, entity_id: int):
        self.self_model = FriendshipUniqueModel(entity_id=entity_id)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.entity_id)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            order_by(self.orm_model.entity_id)
        return stmt

    def _make_unique_self_update(self, new_model: FriendshipRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(
            self,
            status: str,
            mood: float,
            friend_ship: float,
            energy: float,
            currency: float,
            response_threshold: float) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            status=status,
            mood=mood,
            friend_ship=friend_ship,
            energy=energy,
            currency=currency,
            response_threshold=response_threshold
        ))

    async def add_upgrade_unique_self(
            self,
            status: str,
            mood: float,
            friend_ship: float,
            energy: float,
            currency: float,
            response_threshold: float) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            status=status,
            mood=mood,
            friend_ship=friend_ship,
            energy=energy,
            currency=currency,
            response_threshold=response_threshold
        ))

    async def add_only(
            self,
            status: str,
            mood: float,
            friend_ship: float,
            energy: float,
            currency: float,
            response_threshold: float) -> BoolResult:
        return await self._add_only_without_upgrade_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            status=status,
            mood=mood,
            friend_ship=friend_ship,
            energy=energy,
            currency=currency,
            response_threshold=response_threshold
        ))

    async def query(self) -> FriendshipModelResult:
        return FriendshipModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> FriendshipModelListResult:
        return FriendshipModelListResult.parse_obj(await cls._query_all())


__all__ = [
    'Friendship',
    'FriendshipModel'
]
