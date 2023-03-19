"""
@Author         : Ailitonia
@Date           : 2023/3/20 0:40
@FileName       : history
@Project        : nonebot2_miya
@Description    : 事件历史记录
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from nonebot.adapters.onebot.v11.event import Event, MetaEvent

from src.database import HistoryDAL, begin_db_session


LOG_PREFIX: str = '<lc>Event History Recorder</lc> | '


async def postprocessor_history(event: Event):
    """事件后处理, 事件历史记录"""
    try:
        if isinstance(event, MetaEvent):
            # 不记录元事件
            return

        time = event.time
        self_id = str(event.self_id)
        group_id = getattr(event, 'group_id', None)
        parent_entity_id = self_id if group_id is None else str(group_id)
        channel_id = getattr(event, 'channel_id', None)
        parent_entity_id = parent_entity_id if channel_id is None else str(channel_id)

        user_id = getattr(event, 'user_id', None)
        entity_id = self_id if user_id is None else str(user_id)

        event_type = event.post_type

        try:
            event_id = f'{event.get_event_name()}{event.get_session_id()}'
        except (NotImplementedError, ValueError):
            event_id = f'{getattr(event, "post_type", "Undefined")}_{getattr(event, "sub_type", "Undefined")}'

        raw_data = event.json()
        message_data = getattr(event, 'message', '')

        raw_data = str(raw_data) if not isinstance(raw_data, str) else raw_data
        msg_data = str(message_data) if not isinstance(message_data, str) else message_data
        if len(raw_data) > 4096:
            logger.warning(f'History | Raw data is longer than field limited and it will be reduce, <{raw_data}>')
            raw_data = raw_data[:4096]
        if len(msg_data) > 4096:
            logger.warning(f'History | Raw data is longer than field limited and it will be reduce, <{msg_data}>')
            msg_data = msg_data[:4096]

        async with begin_db_session() as session:
            dal = HistoryDAL(session=session)
            await dal.add(
                time=time, bot_self_id=self_id, parent_entity_id=parent_entity_id, entity_id=entity_id,
                event_type=event_type, event_id=event_id, raw_data=raw_data, msg_data=msg_data
            )
        logger.trace(f'{LOG_PREFIX}Recording event({event_id}) succeed')
    except Exception as e:
        logger.error(f'{LOG_PREFIX}Recording failed, error: {repr(e)}, event: {event.json()}')


__all__ = [
    'postprocessor_history'
]
