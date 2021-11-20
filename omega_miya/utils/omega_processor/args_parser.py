"""
@Author         : Ailitonia
@Date           : 2021/11/18 19:44
@FileName       : args_parser.py
@Project        : nonebot2_miya 
@Description    : 消息事件参数解析器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List
from nonebot import logger
from nonebot.exception import IgnoredException
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent
from omega_miya.utils.omega_plugin_utils import MessageDecoder


cancel_text = ['取消', '中止', '停止', '算了', '算了吧']


async def preprocessor_args_parser(bot: Bot, event: MessageEvent, state: T_State):
    """
    消息事件参数解析器 T_EventPreProcessor
    """
    args_list: List[str] = event.get_plaintext().strip().split()
    args_count = len(args_list)

    msg_decoder = MessageDecoder(message=event.get_message())

    state.update({
        '_parsed_args': {
            '_args_count': args_count,
            '_args': args_list,
            '_url_count': len(msg_decoder.get_all_img_url()),
            '_url_args': msg_decoder.get_all_img_url(),
            '_at_count': len(msg_decoder.get_all_at_qq()),
            '_at_args': msg_decoder.get_all_at_qq(),
        }
    })


async def preprocessor_cancel_parser(matcher: Matcher, bot: Bot, event: MessageEvent, state: T_State):
    """
    用户取消处理 T_RunPreProcessor
    """
    # 仅处理临时会话（涉及用户交互）
    if matcher.temp:
        parsed_arg: List[str] = event.get_plaintext().strip().split()
        arg_len = len(parsed_arg)

        if arg_len == 1 and parsed_arg[0] in cancel_text:
            logger.debug(f'Args Parser | User canceled matcher {matcher.plugin_name} processing')
            await bot.send(event=event, message='操作已取消', at_sender=True)
            raise IgnoredException('用户取消操作')


__all__ = [
    'preprocessor_args_parser',
    'preprocessor_cancel_parser'
]
