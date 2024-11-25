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

from sqlalchemy import desc, select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayerModel, BaseDataQueryResultModel
from ..schema import HistoryOrm


class History(BaseDataQueryResultModel):
    """系统参数 Model"""
    id: int
    message_id: str
    bot_self_id: str
    event_entity_id: str
    user_entity_id: str
    received_time: int
    message_type: str
    message_raw: str
    message_text: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HistoryDAL(BaseDataAccessLayerModel[HistoryOrm, History]):
    """系统参数 数据库操作对象"""

    async def query_unique(
            self,
            message_id: int,
            bot_self_id: str,
            event_entity_id: str,
            user_entity_id: str
    ) -> History:
        stmt = (select(HistoryOrm)
                .where(HistoryOrm.message_id == message_id)
                .where(HistoryOrm.bot_self_id == bot_self_id)
                .where(HistoryOrm.event_entity_id == event_entity_id)
                .where(HistoryOrm.user_entity_id == user_entity_id))
        session_result = await self.db_session.execute(stmt)
        return History.model_validate(session_result.scalar_one())

    async def query_entity_records(
            self,
            bot_self_id: str,
            event_entity_id: str | None = None,
            user_entity_id: str | None = None,
            *,
            start_time: datetime | None = None,
            end_time: datetime | None = None,
            message_type: str | None = None,
            exclude_bot_self_message: bool = False,
    ) -> list[History]:
        """查询某个实体一段时间内的消息历史记录

        :param bot_self_id: 收到消息的机器人ID
        :param event_entity_id: 消息事件实体ID, 为空则返回全部
        :param user_entity_id: 发送对象实体ID, 为空则返回全部
        :param start_time: 起始时间, 为空则返回全部
        :param end_time: 结束时间, 为空则返回全部
        :param message_type: 消息事件类型, 为空则返回全部
        :param exclude_bot_self_message: 是否排除机器人自身的消息
        """
        if event_entity_id is None and user_entity_id is None:
            raise ValueError('need at least one of the event_entity_id and user_entity_id parameters')

        stmt = (select(HistoryOrm)
                .where(HistoryOrm.bot_self_id == bot_self_id)
                .order_by(desc(HistoryOrm.received_time)))
        if event_entity_id is not None:
            stmt = stmt.where(HistoryOrm.event_entity_id == event_entity_id)
        if user_entity_id is not None:
            stmt = stmt.where(HistoryOrm.user_entity_id == user_entity_id)
        if start_time is not None:
            stmt = stmt.where(HistoryOrm.received_time >= int(start_time.timestamp()))
        if end_time is not None:
            stmt = stmt.where(HistoryOrm.received_time <= int(end_time.timestamp()))
        if message_type is not None:
            stmt = stmt.where(HistoryOrm.message_type == message_type)
        if exclude_bot_self_message:
            stmt = stmt.where(HistoryOrm.bot_self_id != HistoryOrm.user_entity_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[History], session_result.scalars().all())

    async def query_all(self) -> list[History]:
        raise NotImplementedError

    async def add(
            self,
            message_id: str,
            bot_self_id: str,
            event_entity_id: str,
            user_entity_id: str,
            received_time: int,
            message_type: str,
            message_raw: str,
            message_text: str,
    ) -> None:
        new_obj = HistoryOrm(bot_self_id=bot_self_id, event_entity_id=event_entity_id, user_entity_id=user_entity_id,
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
