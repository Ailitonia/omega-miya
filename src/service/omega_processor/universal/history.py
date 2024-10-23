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

from src.compat import dump_json_as
from src.database import HistoryDAL, begin_db_session
from src.service import OmegaMatcherInterface

LOG_PREFIX: str = '<lc>Message History</lc> | '


async def postprocessor_history(bot: Bot, event: Event, message: Message):
    """事件后处理, 消息历史记录"""
    if (message_id := getattr(event, 'message_id', None)) is not None:
        message_id = str(message_id)
    elif (message_id := getattr(event, 'id', None)) is not None:
        message_id = str(message_id)
    else:
        message_id = str(hash(message))

    message_raw = dump_json_as(Message, message, encoding='utf-8')
    message_text = str(message)
    if len(message_raw) > 4096:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}message_raw reduced by exceeding field limiting, {message_raw!r}')
        message_raw = message_raw[:4096]
    if len(message_text) > 4096:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}message_text reduced by exceeding field limiting, {message_text!r}')
        message_text = message_text[:4096]

    try:
        async with begin_db_session() as session:
            entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='user')
            await HistoryDAL(session=session).add(
                message_id=message_id,
                bot_self_id=bot.self_id,
                parent_entity_id=entity.parent_id,
                entity_id=entity.entity_id,
                received_time=int(datetime.now().timestamp()),
                message_type=event.get_event_name(),
                message_raw=message_raw,
                message_text=message_text,
            )
        logger.opt(colors=True).trace(f'{LOG_PREFIX}Message(id={message_id!r}, text={message_text!r}) recorded')
    except Exception as e:
        logger.opt(colors=True).error(f'{LOG_PREFIX}Recording message failed, {e!r}, {message_raw!r}')


__all__ = [
    'postprocessor_history',
]
