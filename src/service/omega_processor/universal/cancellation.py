"""
@Author         : Ailitonia
@Date           : 2023/3/19 20:28
@FileName       : cancellation
@Project        : nonebot2_miya
@Description    : 用户取消处理解析器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re

from nonebot import logger
from nonebot.exception import IgnoredException
from nonebot.internal.adapter import Message
from nonebot.matcher import Matcher

CANCEL_PROMPT: str = '操作取消，已退出命令交互'
CHINESE_CANCELLATION_WORDS = {'算', '别', '不', '停', '取消'}
CHINESE_CANCELLATION_REGEX_1 = re.compile(r'^那?[算别不停]\w{0,3}了?吧?$')
CHINESE_CANCELLATION_REGEX_2 = re.compile(r'^那?(?:[给帮]我)?取消了?吧?$')


def is_cancellation(message: Message | str) -> bool:
    """判断消息是否表示取消

    :param message: 消息对象或消息文本
    :return: 是否表示取消的布尔值
    """
    text = message.extract_plain_text() if isinstance(message, Message) else message
    return any(kw in text for kw in CHINESE_CANCELLATION_WORDS) and bool(
        CHINESE_CANCELLATION_REGEX_1.match(text)
        or CHINESE_CANCELLATION_REGEX_2.match(text)
    )


async def preprocessor_cancellation(matcher: Matcher, message: Message):
    """运行预处理, 用户取消操作"""

    if matcher.temp:
        # 仅处理临时会话（涉及用户交互）
        cancelled = is_cancellation(message)
        if cancelled:
            logger.opt(colors=True).debug(
                f'<lc>Cancellation Parser</lc> | User canceled matcher {matcher.plugin_name} processing'
            )
            try:
                await matcher.send(message=CANCEL_PROMPT)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'<lc>Cancellation Parser</lc> | Sending cancellation tip message failed, {e!r}'
                )
            raise IgnoredException('用户取消操作')


__all__ = [
    'preprocessor_cancellation',
]
