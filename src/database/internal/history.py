"""
@Author         : Ailitonia
@Date           : 2022/12/03 11:33
@FileName       : history.py
@Project        : nonebot2_miya 
@Description    : History DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, desc
from typing import Optional

from pydantic import BaseModel, parse_obj_as

from ..model import BaseDataAccessLayerModel, HistoryOrm


class History(BaseModel):
    """系统参数 Model"""
    id: int
    time: int
    bot_self_id: str
    parent_entity_id: str
    entity_id: str
    event_type: str
    event_id: str
    raw_data: str
    msg_data: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class HistoryDAL(BaseDataAccessLayerModel):
    """系统参数 数据库操作对象"""

    def __init__(self, session: AsyncSession):
        self.db_session = session

    async def query_unique(self):
        raise NotImplementedError('method not supported')

    async def query_by_condition(
            self,
            bot_self_id: Optional[str] = None,
            parent_entity_id: Optional[str] = None,
            entity_id: Optional[str] = None,
            event_type: Optional[str] = None,
            start_time: Optional[datetime] = None
    ) -> list[History]:
        """按条件查询历史记录

        :param bot_self_id: bot id, 为空则返回全部
        :param parent_entity_id: 父对象 id, 为空则返回全部
        :param entity_id: 对象 id, 为空则返回全部
        :param event_type: 事件类型, 为空则返回全部
        :param start_time: 起始时间, 为空则返回全部
        """
        stmt = select(HistoryOrm).order_by(desc(HistoryOrm.time))
        if bot_self_id is not None:
            stmt = stmt.where(HistoryOrm.bot_self_id == bot_self_id)
        if parent_entity_id is not None:
            stmt = stmt.where(HistoryOrm.parent_entity_id == parent_entity_id)
        if entity_id is not None:
            stmt = stmt.where(HistoryOrm.event_id == entity_id)
        if event_type is not None:
            stmt = stmt.where(HistoryOrm.event_type == event_type)
        if start_time is not None:
            stmt = stmt.where(HistoryOrm.time >= int(start_time.timestamp()))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[History], session_result.scalars().all())

    async def query_all(self) -> list[History]:
        stmt = select(HistoryOrm).order_by(desc(HistoryOrm.time))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[History], session_result.scalars().all())

    async def add(
            self,
            time: int,
            bot_self_id: str,
            parent_entity_id: str,
            entity_id: str,
            event_type: str,
            event_id: str,
            raw_data: str,
            msg_data: Optional[str] = None
    ) -> None:
        new_obj = HistoryOrm(bot_self_id=bot_self_id, parent_entity_id=parent_entity_id, entity_id=entity_id,
                             event_type=event_type, event_id=event_id, time=time,
                             raw_data=raw_data, msg_data=msg_data, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            time: Optional[int] = None,
            bot_self_id: Optional[str] = None,
            parent_entity_id: Optional[str] = None,
            entity_id: Optional[str] = None,
            event_type: Optional[str] = None,
            event_id: Optional[str] = None,
            raw_data: Optional[str] = None,
            msg_data: Optional[str] = None
    ) -> None:
        stmt = update(HistoryOrm).where(HistoryOrm.id == id_)
        if time is not None:
            stmt = stmt.values(time=time)
        if bot_self_id is not None:
            stmt = stmt.values(bot_self_id=bot_self_id)
        if parent_entity_id is not None:
            stmt = stmt.values(parent_entity_id=parent_entity_id)
        if entity_id is not None:
            stmt = stmt.values(entity_id=entity_id)
        if event_type is not None:
            stmt = stmt.values(event_type=event_type)
        if event_id is not None:
            stmt = stmt.values(event_id=event_id)
        if raw_data is not None:
            stmt = stmt.values(raw_data=raw_data)
        if msg_data is not None:
            stmt = stmt.values(msg_data=msg_data)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(HistoryOrm).where(HistoryOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'History',
    'HistoryDAL'
]
