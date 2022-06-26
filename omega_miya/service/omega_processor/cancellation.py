"""
@Author         : Ailitonia
@Date           : 2021/11/18 19:44
@FileName       : args_parser.py
@Project        : nonebot2_miya 
@Description    : 用户取消处理解析器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.helpers import is_cancellation

from omega_miya.utils.process_utils import run_async_catching_exception


_cancel_text: list[str] = ['取消', '中止', '停止', '算了', '算了吧']
_cancel_prompt: str = '操作已取消'


async def preprocessor_cancellation(matcher: Matcher, bot: Bot, event: MessageEvent):
    """用户取消处理"""

    if matcher.temp:
        # 仅处理临时会话（涉及用户交互）
        cancelled = is_cancellation(event.message)
        if cancelled:
            logger.debug(f'Cancellation Parser | User canceled matcher {matcher.plugin_name} processing')
            await run_async_catching_exception(bot.send)(event=event, message=_cancel_prompt, at_sender=True)
            raise IgnoredException('用户取消操作')


__all__ = [
    'preprocessor_cancellation'
]
