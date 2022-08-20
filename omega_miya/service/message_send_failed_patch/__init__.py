"""
@Author         : Ailitonia
@Date           : 2022/06/14 19:27
@FileName       : message_send_failed_patch.py
@Project        : nonebot2_miya 
@Description    : 消息发送失败提示补丁
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TypeVar, ParamSpec, Callable, Coroutine
from functools import wraps

from nonebot.log import logger
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11 import ActionFailed

from .config import message_send_failed_patch_config


P = ParamSpec("P")
R = TypeVar("R")

original_send = Bot.send
send_failed_info: str = message_send_failed_patch_config.message_send_failed_info


def _catch_bot_send_failed(func: Callable[P, Coroutine[None, None, R]]) -> Callable[P, Coroutine[None, None, R]]:
    """包装 Bot.send 的装饰器, 消息发送失败后自动重新发送失败提示"""

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            result = await func(*args, **kwargs)
        except ActionFailed:
            failed_msg = Message(send_failed_info)
            bot_id = args[0].self_id

            if not kwargs:
                original_message = str(args[2])
                args = list(args)
                args[2] = failed_msg
                args = tuple(args)
            else:
                original_message = str(kwargs.get('message'))
                kwargs.update({'message': failed_msg})

            logger.opt(colors=True).exception(f"<lc>MessageSendFailedProcessor</lc> | Bot({bot_id}) send message failed"
                                              f" with message: <ly>{' '.join(original_message.split())!r}</ly>")

            result = await func(*args, **kwargs)
        return result

    return _wrapper


Bot.send = _catch_bot_send_failed(original_send)
"""注意: 由于只装饰了 Bot.send 所以通过 Bot.call_api 发送消息的情况不能被这个补丁所处理"""

logger.opt(colors=True).info(f'<lc>MessageSendFailedProcessor patch</lc> loaded')
