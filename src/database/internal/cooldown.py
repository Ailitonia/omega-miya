"""
@Author         : Ailitonia
@Date           : 2022/12/04 15:36
@FileName       : cooldown.py
@Project        : nonebot2_miya 
@Description    : Cooldown DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import update, delete
from sqlalchemy.future import select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel
from ..schema import CoolDownOrm


class CoolDown(BaseModel):
    """冷却事件 Model"""
    id: int
    entity_index_id: int
    event: str
    stop_at: datetime
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(extra='ignore', from_attributes=True, frozen=True)


class CoolDownDAL(BaseDataAccessLayerModel):
    """冷却事件 数据库操作对象"""

    async def query_unique(self, entity_index_id: int, event: str) -> CoolDown:
        stmt = select(CoolDownOrm).\
            where(CoolDownOrm.entity_index_id == entity_index_id).\
            where(CoolDownOrm.event == event)
        session_result = await self.db_session.execute(stmt)
        return CoolDown.model_validate(session_result.scalar_one())

    async def query_all(self) -> list[CoolDown]:
        stmt = select(CoolDownOrm).order_by(CoolDownOrm.entity_index_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[CoolDown], session_result.scalars().all())

    async def add(
            self,
            entity_index_id: int,
            event: str,
            stop_at: datetime,
            description: Optional[str] = None
    ) -> None:
        new_obj = CoolDownOrm(entity_index_id=entity_index_id, event=event, stop_at=stop_at,
                              description=description, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            entity_index_id: Optional[int] = None,
            event: Optional[str] = None,
            stop_at: Optional[datetime] = None,
            description: Optional[str] = None
    ) -> None:
        stmt = update(CoolDownOrm).where(CoolDownOrm.id == id_)
        if entity_index_id is not None:
            stmt = stmt.values(entity_index_id=entity_index_id)
        if event is not None:
            stmt = stmt.values(event=event)
        if stop_at is not None:
            stmt = stmt.values(stop_at=stop_at)
        if description is not None:
            stmt = stmt.values(description=description)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(CoolDownOrm).where(CoolDownOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def clear_expired(self) -> None:
        """清理所有已过期的冷却事件"""
        stmt = delete(CoolDownOrm).where(CoolDownOrm.stop_at <= datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'CoolDown',
    'CoolDownDAL',
]
