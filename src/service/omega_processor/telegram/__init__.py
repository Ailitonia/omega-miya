"""
@Author         : Ailitonia
@Date           : 2023/3/20 2:12
@FileName       : telegram
@Project        : nonebot2_miya
@Description    : telegram processor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.adapters.telegram.bot import Bot
from nonebot.adapters.telegram.event import Event, MessageEvent
from nonebot.message import event_preprocessor

from .image_parser import handle_parse_message_image_event_preprocessor


@event_preprocessor
async def handle_telegram_event_preprocessor(bot: Bot, event: Event):
    """事件预处理"""
    # 针对消息事件的处理
    if isinstance(event, MessageEvent):
        # 处理消息段图片解析
        await handle_parse_message_image_event_preprocessor(bot=bot, event=event)


__all__ = []
