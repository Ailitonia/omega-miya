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
from typing import Any

from sqlalchemy import delete, desc, func, select

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import HistoryOrm


class History(BaseDataOutModel):
    """历史消息数据"""
    id: int
    received_timestamp: int
    message_id: str
    bot_self_id: str
    event_entity_id: str
    user_entity_id: str
    message_type: str
    message_plain_text: str
    message_raw: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None


class HistoryDAL(BaseDataAccessLayer[HistoryOrm, History]):
    """消息历史"""

    async def _count_all(self) -> int:
        """查询全表行数"""
        stmt = select(func.count()).select_from(HistoryOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表, 敏感操作, 方法内不执行 commit, 可由外层事务 rollback"""
        await self.db_session.execute(delete(HistoryOrm))
        self.db_session.expunge_all()

    async def _select_unique(
            self,
            message_id: str,
            bot_self_id: str,
            event_entity_id: str,
            user_entity_id: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> HistoryOrm:
        stmt = (select(HistoryOrm)
                .where(HistoryOrm.message_id == message_id)
                .where(HistoryOrm.bot_self_id == bot_self_id)
                .where(HistoryOrm.event_entity_id == event_entity_id)
                .where(HistoryOrm.user_entity_id == user_entity_id))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_unique(
            self,
            message_id: str,
            bot_self_id: str,
            event_entity_id: str,
            user_entity_id: str,
            *,
            populate_existing: bool = False,
    ) -> History:
        item = await self._select_unique(
            message_id,
            bot_self_id,
            event_entity_id,
            user_entity_id,
            populate_existing=populate_existing,
        )
        return History.model_validate(item)

    async def query_records_by_condition(
            self,
            bot_self_id: str,
            event_entity_id: str | None = None,
            user_entity_id: str | None = None,
            *,
            message_type: str | None = None,
            start_time: datetime | None = None,
            end_time: datetime | None = None,
            exclude_bot_self_message: bool = False,
            limit: int | None = None,
    ) -> list[History]:
        """按条件查询消息历史记录

        :param bot_self_id: 收到消息的机器人ID
        :param event_entity_id: 消息事件实体ID, 为空则返回全部
        :param user_entity_id: 发送对象实体ID, 为空则返回全部
        :param message_type: 消息事件类型, 为空则返回全部
        :param start_time: 起始时间, 为空则返回全部
        :param end_time: 结束时间, 为空则返回全部
        :param exclude_bot_self_message: 是否排除机器人自身的消息
        :param limit: 返回记录数量上限, 按时间倒序取最近的记录, 为空则不限制
        """
        if event_entity_id is None and user_entity_id is None:
            raise ValueError('need at least one of the event_entity_id and user_entity_id parameters')

        stmt = (select(HistoryOrm)
                .where(HistoryOrm.bot_self_id == bot_self_id)
                .order_by(desc(HistoryOrm.received_timestamp), desc(HistoryOrm.id)))

        if event_entity_id is not None:
            stmt = stmt.where(HistoryOrm.event_entity_id == event_entity_id)
        if user_entity_id is not None:
            stmt = stmt.where(HistoryOrm.user_entity_id == user_entity_id)

        if message_type is not None:
            stmt = stmt.where(HistoryOrm.message_type == message_type)

        if start_time is not None:
            stmt = stmt.where(HistoryOrm.received_timestamp >= int(start_time.timestamp()))
        if end_time is not None:
            stmt = stmt.where(HistoryOrm.received_timestamp <= int(end_time.timestamp()))

        if exclude_bot_self_message:
            stmt = stmt.where(HistoryOrm.bot_self_id != HistoryOrm.user_entity_id)
        if limit is not None:
            stmt = stmt.limit(limit)

        return parse_obj_as(list[History], (await self.db_session.execute(stmt)).scalars().all())

    async def count_records_by_condition(
            self,
            bot_self_id: str,
            event_entity_id: str | None = None,
            user_entity_id: str | None = None,
            *,
            message_type: str | None = None,
            start_time: datetime | None = None,
            end_time: datetime | None = None,
            exclude_bot_self_message: bool = False,
    ) -> int:
        """按条件查询消息历史记录条数

        :param bot_self_id: 收到消息的机器人ID
        :param event_entity_id: 消息事件实体ID, 为空则返回全部
        :param user_entity_id: 发送对象实体ID, 为空则返回全部
        :param message_type: 消息事件类型, 为空则返回全部
        :param start_time: 起始时间, 为空则返回全部
        :param end_time: 结束时间, 为空则返回全部
        :param exclude_bot_self_message: 是否排除机器人自身的消息
        """
        if event_entity_id is None and user_entity_id is None:
            raise ValueError('need at least one of the event_entity_id and user_entity_id parameters')

        stmt = select(func.count()).select_from(HistoryOrm).where(HistoryOrm.bot_self_id == bot_self_id)

        if event_entity_id is not None:
            stmt = stmt.where(HistoryOrm.event_entity_id == event_entity_id)
        if user_entity_id is not None:
            stmt = stmt.where(HistoryOrm.user_entity_id == user_entity_id)

        if message_type is not None:
            stmt = stmt.where(HistoryOrm.message_type == message_type)

        if start_time is not None:
            stmt = stmt.where(HistoryOrm.received_timestamp >= int(start_time.timestamp()))
        if end_time is not None:
            stmt = stmt.where(HistoryOrm.received_timestamp <= int(end_time.timestamp()))

        if exclude_bot_self_message:
            stmt = stmt.where(HistoryOrm.bot_self_id != HistoryOrm.user_entity_id)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def add(
            self,
            received_timestamp: int,
            message_id: str,
            bot_self_id: str,
            event_entity_id: str,
            user_entity_id: str,
            message_type: str,
            message_plain_text: str,
            message_raw: dict[str, Any],
    ) -> History:
        """向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        原则上此表保存历史消息内容原始副本, 不进行更新
        """
        message_raw = parse_obj_as(dict[str, Any], message_raw)

        new_obj = HistoryOrm(
            received_timestamp=received_timestamp,
            message_id=message_id,
            bot_self_id=bot_self_id,
            event_entity_id=event_entity_id,
            user_entity_id=user_entity_id,
            message_type=message_type,
            message_plain_text=message_plain_text,
            message_raw=message_raw,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        return History.model_validate(new_obj)

    async def delete_period_older(
            self,
            before_timestamp: int,
            *,
            bot_self_id: str | None = None,
    ) -> None:
        stmt = (delete(HistoryOrm).where(HistoryOrm.received_timestamp <= before_timestamp))

        if bot_self_id is not None:
            stmt = stmt.where(HistoryOrm.bot_self_id == bot_self_id)

        await self.db_session.execute(stmt)


__all__ = [
    'History',
    'HistoryDAL',
]
