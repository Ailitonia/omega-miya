"""
@Author         : Ailitonia
@Date           : 2024/10/23 17:11:12
@FileName       : helpers.py
@Project        : omega-miya
@Description    : OneBot V11 反撤回插件工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import TYPE_CHECKING

from nonebot.adapters.onebot.v11 import Message as OneBotV11Message

from src.compat import parse_json_as, parse_obj_as
from src.database import HistoryDAL, begin_db_session

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot

    from src.params.depends import EVENT_ENTITY_PARAMS, USER_ENTITY_PARAMS


type MessageHistory = tuple[datetime, OneBotV11Message]
"""查询到的消息记录: 消息发送时间, 消息内容"""


async def query_message_from_adapter(bot: 'OneBotV11Bot', message_id: int) -> MessageHistory:
    """从协议端查询用户消息"""
    message_result = await bot.get_msg(message_id=message_id)
    message = parse_obj_as(OneBotV11Message, message_result['message']).include('image', 'text')
    sent_time = datetime.fromtimestamp(message_result['time'])
    return sent_time, message


async def query_message_from_database(
        event_entity_params: 'EVENT_ENTITY_PARAMS',
        user_entity_params: 'USER_ENTITY_PARAMS',
        message_id: int,
) -> MessageHistory:
    """从数据库查询用户消息"""
    async with begin_db_session() as session:
        message_recording = await HistoryDAL(session=session).query_unique(
            message_id=message_id,
            bot_self_id=event_entity_params.bot_id,
            event_entity_id=event_entity_params.entity_id,
            user_entity_id=user_entity_params.entity_id,
        )
    message = parse_json_as(OneBotV11Message, message_recording.message_raw).include('image', 'text')
    sent_time = datetime.fromtimestamp(message_recording.received_time)
    return sent_time, message


__all__ = [
    'query_message_from_adapter',
    'query_message_from_database',
]
