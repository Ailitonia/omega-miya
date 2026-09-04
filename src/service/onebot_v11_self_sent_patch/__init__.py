"""
@Author         : Ailitonia
@Date           : 2022/05/23 19:50
@FileName       : gocqhttp_self_sent_patch.py
@Project        : nonebot2_miya
@Description    : Bot 自身发送消息适配, 适用于 OneBotV11
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.log import logger
from nonebot.permission import Permission

from .model import MessageSentEvent


async def _self_sent(event: MessageSentEvent) -> bool:
    return event.self_id == event.user_id


SELF_SENT = Permission(_self_sent)
"""匹配任意自身发送消息类型事件"""

logger.opt(colors=True).info('<lc>MessageSent patch(go-cqhttp)</lc> loaded')


__all__ = [
    'MessageSentEvent',
    'SELF_SENT',
]
