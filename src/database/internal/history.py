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
from typing import Optional

from sqlalchemy import desc, select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import HistoryOrm


class History(BaseDataQueryResultModel):
    """系统参数 Model"""
    id: int
    message_id: str
    bot_self_id: str
    parent_entity_id: str
    entity_id: str
    received_time: int
    message_type: str
    message_raw: str
    message_text: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class HistoryDAL(BaseDataAccessLayerModel[HistoryOrm, History]):
    """系统参数 数据库操作对象"""

    async def query_unique(self, message_id: int, bot_self_id: str, parent_entity_id: str, entity_id: str) -> History:
        stmt = (select(HistoryOrm)
                .where(HistoryOrm.message_id == message_id)
                .where(HistoryOrm.bot_self_id == bot_self_id)
                .where(HistoryOrm.parent_entity_id == parent_entity_id)
                .where(HistoryOrm.entity_id == entity_id))
        session_result = await self.db_session.execute(stmt)
        return History.model_validate(session_result.scalar_one())

    async def query_entity_records(
            self,
            bot_self_id: str,
            parent_entity_id: str,
            entity_id: str,
            *,
            start_time: Optional[datetime] = None,
            end_time: Optional[datetime] = None,
    ) -> list[History]:
        """查询某个实体一段时间内的消息历史记录

        :param bot_self_id: bot id, 为空则返回全部
        :param parent_entity_id: 父对象 id, 为空则返回全部
        :param entity_id: 对象 id, 为空则返回全部
        :param start_time: 起始时间, 为空则返回全部
        :param end_time: 结束时间, 为空则返回全部
        """
        stmt = (select(HistoryOrm)
                .where(HistoryOrm.bot_self_id == bot_self_id)
                .where(HistoryOrm.parent_entity_id == parent_entity_id)
                .where(HistoryOrm.entity_id == entity_id)
                .order_by(desc(HistoryOrm.received_time)))
        if start_time is not None:
            stmt = stmt.where(HistoryOrm.received_time >= int(start_time.timestamp()))
        if end_time is not None:
            stmt = stmt.where(HistoryOrm.received_time <= int(end_time.timestamp()))
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[History], session_result.scalars().all())

    async def query_all(self) -> list[History]:
        raise NotImplementedError

    async def add(
            self,
            message_id: str,
            bot_self_id: str,
            parent_entity_id: str,
            entity_id: str,
            received_time: int,
            message_type: str,
            message_raw: str,
            message_text: str,
    ) -> None:
        new_obj = HistoryOrm(bot_self_id=bot_self_id, parent_entity_id=parent_entity_id, entity_id=entity_id,
                             message_id=message_id, received_time=received_time, message_type=message_type,
                             message_raw=message_raw, message_text=message_text, created_at=datetime.now())
        await self._add(new_obj)

    async def upsert(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def update(self, *args, **kwargs) -> None:
        raise NotImplementedError

    async def delete(self, *args, **kwargs) -> None:
        raise NotImplementedError


__all__ = [
    'History',
    'HistoryDAL',
]
