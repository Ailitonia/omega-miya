"""
@Author         : Ailitonia
@Date           : 2024/5/26 上午2:39
@FileName       : v11
@Project        : nonebot2_miya
@Description    : onebot v11 processor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.adapters.onebot.v11 import Bot, Event, MessageEvent
from nonebot.message import event_preprocessor

from .v11_replace_ntqq_image_url import handle_replace_image_url_event_preprocessor


@event_preprocessor
async def handle_onebot_v11_event_preprocessor(bot: Bot, event: Event):
    """事件预处理"""
    # 针对消息事件的处理
    if isinstance(event, MessageEvent):
        # 处理消息段图片域名替换
        await handle_replace_image_url_event_preprocessor(event=event)


__all__ = []
