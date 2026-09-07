"""
@Author         : Ailitonia
@Date           : 2023/3/20 0:40
@FileName       : history
@Project        : nonebot2_miya
@Description    : 事件历史记录
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import time

from nonebot import logger
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.adapters import Message as BaseMessage
from nonebot_plugin_alconna.uniseg import get_message_id

from src.database import DATABASE_SESSION, HistoryDAL
from ...omega_base import OmegaMatcherInterface

_LOG_PREFIX: str = '<lc>Message History</lc> | '
"""日志前缀"""


async def postprocessor_history(
        bot: BaseBot,
        event: BaseEvent,
        message: BaseMessage,
        db_session: DATABASE_SESSION,
) -> None:
    """事件后处理, 消息历史记录"""
    event_depend = OmegaMatcherInterface.get_event_depend_cls(target_event=event)(bot=bot, event=event)

    message_id: str = get_message_id(event=event, bot=bot)
    uni_message = event_depend.get_uni_message()
    message_raw = uni_message.dump(media_save_dir=False)
    message_text = message.extract_plain_text()

    event_entity_params = event_depend.extract_entity_params(acquire_type='event')
    user_entity_params = event_depend.extract_entity_params(acquire_type='user')

    try:
        await HistoryDAL(session=db_session).add(
            received_timestamp=int(time.time()),
            message_id=message_id,
            bot_self_id=bot.self_id,
            event_entity_id=event_entity_params.entity_id,
            user_entity_id=user_entity_params.entity_id,
            message_type=f'{event_entity_params.entity_type}.{event.get_event_name()}',
            message_plain_text=message_text,
            message_raw=message_raw,
        )
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Message(id={message_id}) recorded')
    except Exception as e:
        logger.opt(colors=True).error(f'{_LOG_PREFIX}Record message(id={message_id}) failed, {e}')


__all__ = [
    'postprocessor_history',
]
