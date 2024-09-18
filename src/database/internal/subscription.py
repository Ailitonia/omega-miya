"""
@Author         : Ailitonia
@Date           : 2022/12/04 17:18
@FileName       : subscription.py
@Project        : nonebot2_miya 
@Description    : Subscription DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import update, delete
from sqlalchemy.future import select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import SubscriptionOrm


class Subscription(BaseDataQueryResultModel):
    """订阅 Model"""
    id: int
    sub_source_index_id: int
    entity_index_id: int
    sub_info: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SubscriptionDAL(BaseDataAccessLayerModel[Subscription]):
    """订阅 数据库操作对象"""

    async def query_unique(self, sub_source_index_id: int, entity_index_id: int) -> Subscription:
        stmt = (select(SubscriptionOrm)
                .where(SubscriptionOrm.sub_source_index_id == sub_source_index_id)
                .where(SubscriptionOrm.entity_index_id == entity_index_id))
        session_result = await self.db_session.execute(stmt)
        return Subscription.model_validate(session_result.scalar_one())

    async def query_all(self) -> list[Subscription]:
        stmt = select(SubscriptionOrm).order_by(SubscriptionOrm.sub_source_index_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Subscription], session_result.scalars().all())

    async def add(self, sub_source_index_id: int, entity_index_id: int, sub_info: Optional[str] = None) -> None:
        new_obj = SubscriptionOrm(sub_source_index_id=sub_source_index_id, entity_index_id=entity_index_id,
                                  sub_info=sub_info, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            sub_source_index_id: Optional[int] = None,
            entity_index_id: Optional[int] = None,
            sub_info: Optional[str] = None
    ) -> None:
        stmt = update(SubscriptionOrm).where(SubscriptionOrm.id == id_)
        if sub_source_index_id is not None:
            stmt = stmt.values(sub_source_index_id=sub_source_index_id)
        if entity_index_id is not None:
            stmt = stmt.values(entity_index_id=entity_index_id)
        if sub_info is not None:
            stmt = stmt.values(sub_info=sub_info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(SubscriptionOrm).where(SubscriptionOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'Subscription',
    'SubscriptionDAL',
]
