"""
@Author         : Ailitonia
@Date           : 2022/12/04 11:57
@FileName       : friendship.py
@Project        : nonebot2_miya 
@Description    : Friendship DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select, update

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import FriendshipOrm


class Friendship(BaseDataQueryResultModel):
    """好感度 Model"""
    id: int
    entity_index_id: int
    status: str
    mood: float
    friendship: float
    energy: float
    currency: float
    response_threshold: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FriendshipDAL(BaseDataAccessLayerModel[FriendshipOrm, Friendship]):
    """好感度 数据库操作对象"""

    async def query_unique(self, entity_index_id: int) -> Friendship:
        stmt = select(FriendshipOrm).where(FriendshipOrm.entity_index_id == entity_index_id)
        session_result = await self.db_session.execute(stmt)
        return Friendship.model_validate(session_result.scalar_one())

    async def query_all(self) -> list[Friendship]:
        stmt = select(FriendshipOrm).order_by(FriendshipOrm.entity_index_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Friendship], session_result.scalars().all())

    async def add(
            self,
            entity_index_id: int,
            status: str,
            mood: float,
            friendship: float,
            energy: float,
            currency: float,
            response_threshold: float
    ) -> None:
        new_obj = FriendshipOrm(entity_index_id=entity_index_id, status=status, mood=mood, friendship=friendship,
                                energy=energy, currency=currency, response_threshold=response_threshold,
                                created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(
            self,
            id_: int,
            *,
            entity_index_id: Optional[int] = None,
            status: Optional[str] = None,
            mood: Optional[float] = None,
            friendship: Optional[float] = None,
            energy: Optional[float] = None,
            currency: Optional[float] = None,
            response_threshold: Optional[float] = None
    ) -> None:
        stmt = update(FriendshipOrm).where(FriendshipOrm.id == id_)
        if entity_index_id is not None:
            stmt = stmt.values(entity_index_id=entity_index_id)
        if status is not None:
            stmt = stmt.values(status=status)
        if mood is not None:
            stmt = stmt.values(mood=mood)
        if friendship is not None:
            stmt = stmt.values(friendship=friendship)
        if energy is not None:
            stmt = stmt.values(energy=energy)
        if currency is not None:
            stmt = stmt.values(currency=currency)
        if response_threshold is not None:
            stmt = stmt.values(response_threshold=response_threshold)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(FriendshipOrm).where(FriendshipOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'Friendship',
    'FriendshipDAL',
]
