"""
@Author         : Ailitonia
@Date           : 2022/05/23 19:50
@FileName       : gocqhttp_self_sent_patch.py
@Project        : nonebot2_miya 
@Description    : go-cqhttp 自身发送消息适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.log import logger
from nonebot.permission import Permission

from .model import MessageSentEvent


async def _self_sent(event: MessageSentEvent) -> bool:
    return event.self_id == event.user_id


async def _su_self_sent(event: MessageSentEvent) -> bool:
    return (event.self_id == event.user_id
            and event.message.extract_plain_text().startswith('!SU'))


SELF_SENT = Permission(_self_sent)
"""匹配任意自身发送消息类型事件"""
SU_SELF_SENT = Permission(_su_self_sent)
"""匹配以"!SU"开头的自身发送消息类型事件"""

logger.opt(colors=True).info('<lc>MessageSent patch(go-cqhttp)</lc> loaded')


__all__ = [
    'MessageSentEvent',
    'SELF_SENT',
    'SU_SELF_SENT',
]
