"""
@Author         : Ailitonia
@Date           : 2024/10/23 17:11:12
@FileName       : helpers.py
@Project        : omega-miya
@Description    : OneBot V11 反撤回插件工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.adapters.onebot.v11 import (
    Bot as OneBotV11Bot,
    Event as OneBotV11Event,
    Message as OneBotV11Message,
)

from src.compat import parse_json_as, parse_obj_as
from src.database import HistoryDAL, begin_db_session
from src.service import OmegaMatcherInterface


async def query_message_from_adapter(bot: OneBotV11Bot, message_id: int) -> OneBotV11Message:
    """从协议端查询用户消息"""
    message_result = await bot.get_msg(message_id=message_id)
    return parse_obj_as(OneBotV11Message, message_result['message']).include('image', 'text')


async def query_message_from_database(bot: OneBotV11Bot, event: OneBotV11Event, message_id: int) -> OneBotV11Message:
    """从数据库查询用户消息"""
    async with begin_db_session() as session:
        entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='user')
        message_recording = await HistoryDAL(session=session).query_unique(
            message_id=message_id,
            bot_self_id=bot.self_id,
            parent_entity_id=entity.parent_id,
            entity_id=entity.entity_id,
        )
    return parse_json_as(OneBotV11Message, message_recording.message_raw).include('image', 'text')


__all__ = [
    'query_message_from_adapter',
    'query_message_from_database',
]
