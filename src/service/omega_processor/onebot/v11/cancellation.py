"""
@Author         : Ailitonia
@Date           : 2023/3/19 20:28
@FileName       : cancellation
@Project        : nonebot2_miya
@Description    : 用户取消处理解析器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.helpers import is_cancellation


_CANCEL_PROMPT: str = '操作取消，已退出命令交互'


async def preprocessor_cancellation(matcher: Matcher, event: MessageEvent):
    """运行预处理, 用户取消操作"""

    if matcher.temp:
        # 仅处理临时会话（涉及用户交互）
        cancelled = is_cancellation(event.message)
        if cancelled:
            logger.opt(colors=True).debug(
                f'<lc>Cancellation Parser</lc> | User canceled matcher {matcher.plugin_name} processing'
            )
            await matcher.send(message=_CANCEL_PROMPT, at_sender=True)
            raise IgnoredException('用户取消操作')


__all__ = [
    'preprocessor_cancellation'
]
