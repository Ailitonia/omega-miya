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
from src.service import OmegaMatcherInterface

LOG_PREFIX: str = '<lc>Event History</lc> | '


async def postprocessor_history(bot: Bot, event: Event, message: Message):
    """事件后处理, 消息历史记录"""
    self_id = bot.self_id
    time = round(datetime.now().timestamp())

    event_type = event.get_type()
    try:
        event_id = f'{event.get_event_name()}_{event.get_session_id()}'
    except (NotImplementedError, ValueError):
        event_id = f'{event_type}_{self_id}_{time}'

    raw_data = event.model_dump_json()
    raw_data = str(raw_data) if not isinstance(raw_data, str) else raw_data
    msg_data = str(message)

    if len(raw_data) > 4096:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}raw_data is longer than field limiting to be reduce, {raw_data!r}')
        raw_data = raw_data[:4096]
    if len(msg_data) > 4096:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}msg_data is longer than field limiting to be reduce, {msg_data!r}')
        msg_data = msg_data[:4096]

    try:
        async with begin_db_session() as session:
            entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='user')
            parent_entity_id = entity.parent_id
            entity_id = entity.entity_id

            dal = HistoryDAL(session=session)
            await dal.add(
                time=time, bot_self_id=self_id, parent_entity_id=parent_entity_id, entity_id=entity_id,
                event_type=event_type, event_id=event_id, raw_data=raw_data, msg_data=msg_data
            )
        logger.opt(colors=True).trace(f'{LOG_PREFIX}Recording event({event_id}) succeed')
    except Exception as e:
        logger.opt(colors=True).error(f'{LOG_PREFIX}Recording failed, {e!r}, event: {event.model_dump_json()}')


__all__ = [
    'postprocessor_history',
]
