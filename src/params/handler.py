"""
@Author         : Ailitonia
@Date           : 2023/7/17 21:29
@FileName       : handler
@Project        : nonebot2_miya
@Description    : 通用处理流程
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated

from nonebot.adapters import Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
from nonebot.typing import T_Handler, T_State


def get_command_str_single_arg_parser_handler(
        key: str,
        *,
        default: str | None = None,
        ensure_key: bool = False
) -> T_Handler:
    """构造解析单个文本命令参数并更新到 State 的 handler, 一般用于 on_command 的首个 handler

    :param key: 存入 State 的 key
    :param default: 未解析出参数时的默认值
    :param ensure_key: 即便未解析出参数, 也要保证 key 存在于 State 中
    :return: T_Handler
    """

    async def handle_parse_command_str_single_arg(state: T_State, cmd_arg: Annotated[Message, CommandArg()]):
        """首次运行时解析命令参数"""
        single_arg = cmd_arg.extract_plain_text().strip()
        if single_arg:
            state.update({key: single_arg})
        elif default:
            state.update({key: default})
        elif ensure_key:
            state.update({key: None})

    return handle_parse_command_str_single_arg


def get_command_message_arg_parser_handler(
        key: str,
        *,
        default: str | None = None,
        ensure_key: bool = False
) -> T_Handler:
    """构造解析单个消息命令参数并更新到 State 的 handler, 一般用于 on_command 的首个 handler

    :param key: 存入 State 的 key
    :param default: 未解析出参数时的默认值
    :param ensure_key: 即便未解析出参数, 也要保证 key 存在于 State 中
    :return: T_Handler
    """

    async def handle_parse_command_message_arg(matcher: Matcher, cmd_arg: Annotated[Message, CommandArg()]):
        """首次运行时解析命令参数"""
        message_arg = cmd_arg
        if message_arg:
            matcher.set_arg(key=key, message=message_arg)
        elif default:
            matcher.set_arg(key=key, message=Message(default))
        elif ensure_key:
            matcher.set_arg(key=key, message=Message(''))

    return handle_parse_command_message_arg


__all__ = [
    'get_command_str_single_arg_parser_handler',
    'get_command_message_arg_parser_handler'
]
