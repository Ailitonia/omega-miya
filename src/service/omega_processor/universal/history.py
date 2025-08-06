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
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.adapters import Message as BaseMessage

from src.compat import dump_json_as
from src.database import HistoryDAL, begin_db_session
from src.service import OmegaMatcherInterface

LOG_PREFIX: str = '<lc>Message History</lc> | '


async def postprocessor_history(bot: BaseBot, event: BaseEvent, message: BaseMessage):
    """事件后处理, 消息历史记录"""
    if (message_id := getattr(event, 'message_id', None)) is not None:
        message_id = str(message_id)
    elif (message_id := getattr(event, 'id', None)) is not None:
        message_id = str(message_id)
    else:
        message_id = str(id(message))

    message_raw = dump_json_as(BaseMessage, message, encoding='utf-8')
    message_text = message.extract_plain_text()
    if len(message_raw) > 4096:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}message_raw reduced by exceeding field limiting, {message_raw!r}')
        message_raw = message_raw[:4096]
    if len(message_text) > 4096:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}message_text reduced by exceeding field limiting, {message_text!r}')
        message_text = message_text[:4096]

    try:
        async with begin_db_session() as session:
            event_entity = OmegaMatcherInterface.get_entity(bot, event, session, acquire_type='event')
            user_entity = OmegaMatcherInterface.get_entity(bot, event, session, acquire_type='user')
            await HistoryDAL(session=session).add(
                message_id=message_id,
                bot_self_id=bot.self_id,
                event_entity_id=event_entity.entity_id,
                user_entity_id=user_entity.entity_id,
                received_time=int(datetime.now().timestamp()),
                message_type=f'{event_entity.entity_type}.{event.get_event_name()}',
                message_raw=message_raw,
                message_text=message_text,
            )
        logger.opt(colors=True).trace(f'{LOG_PREFIX}Message(id={message_id!r}, text={message_text!r}) recorded')
    except Exception as e:
        logger.opt(colors=True).error(f'{LOG_PREFIX}Recording message failed, {e!r}, {message_raw!r}')


__all__ = [
    'postprocessor_history',
]
