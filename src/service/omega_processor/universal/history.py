"""
@Author         : Ailitonia
@Date           : 2023/3/20 0:40
@FileName       : history
@Project        : nonebot2_miya
@Description    : 事件历史记录
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from nonebot import logger
from nonebot.internal.adapter import Bot, Event, Message

from src.database import HistoryDAL, begin_db_session
from src.service import EntityInterface


LOG_PREFIX: str = '<lc>Event History Recorder</lc> | '


async def postprocessor_history(bot: Bot, event: Event, message: Message):
    """事件后处理, 消息历史记录"""
    self_id = bot.self_id
    time = round(datetime.now().timestamp())

    event_type = event.get_type()
    try:
        event_id = f'{event.get_event_name()}_{event.get_session_id()}'
    except (NotImplementedError, ValueError):
        event_id = f'{event_type}_{self_id}_{time}'

    raw_data = event.json()
    raw_data = str(raw_data) if not isinstance(raw_data, str) else raw_data
    msg_data = str(message)

    if len(raw_data) > 4096:
        logger.debug(f'History | Raw data is longer than field limited and it will be reduce, {raw_data!r}')
        raw_data = raw_data[:4096]
    if len(msg_data) > 4096:
        logger.debug(f'History | Raw data is longer than field limited and it will be reduce, {msg_data!r}')
        msg_data = msg_data[:4096]

    try:
        async with EntityInterface(acquire_type='user').get_entity(bot=bot, event=event) as entity:
            parent_entity_id = entity.parent_id
            entity_id = entity.entity_id

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
