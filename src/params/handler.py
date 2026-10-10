"""
@Author         : Ailitonia
@Date           : 2023/7/17 21:29
@FileName       : handler
@Project        : nonebot2_miya
@Description    : 通用处理流程
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated, Any

from nonebot.adapters import Message as BaseMessage
from nonebot.exception import ParserExit
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, ShellCommandArgs
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

    async def handle_parse_command_str_single_arg(state: T_State, cmd_arg: Annotated[BaseMessage, CommandArg()]):
        """首次运行时解析命令参数"""
        single_arg = cmd_arg.extract_plain_text().strip()
        if single_arg:
            state.update({key: single_arg})
        elif default is not None:
            state.update({key: default})
        elif ensure_key:
            state.update({key: None})

    return handle_parse_command_str_single_arg


def get_command_str_multi_args_parser_handler(
        key_prefix: str,
        *,
        default: str | None = None,
        ensure_keys_num: int = 0
) -> T_Handler:
    """构造解析多个文本命令参数并更新到 State 的 handler, 一般用于 on_command 的首个 handler

    解析出的参数以 `{key_prefix}_{index}` 的格式更新到 State 中.

    注意:
        - `ensure_keys_num > 0` 时按 `maxsplit=ensure_keys_num - 1` 分割,
          超出数量的参数将以空白连接合并入最后一个 key; `ensure_keys_num=1` 时全部文本作为一个参数不分割
        - 解析出的参数数量不足 `ensure_keys_num` 时以 `default` 填充缺位 (default 缺省时填充 None),
          因此 `default` 仅在 `ensure_keys_num > 0` 时生效, 单独传入 `default` 不产生任何效果
        - `ensure_keys_num <= 0` 时不做数量保证, 参数全部为空白时不更新 State

    :param key_prefix: 参数前缀, 更新 State 的 key 格式: {key_prefix}_{index}
    :param default: 解析出的参数数量不足 ensure_keys_num 时的填充值
    :param ensure_keys_num: 即便未解析出参数, 也要保证有这么多数量的 key 存在于 State 中
    :return: T_Handler
    """

    async def handle_parse_command_str_multi_args(state: T_State, cmd_arg: Annotated[BaseMessage, CommandArg()]):
        multi_args: list[str | None]
        if ensure_keys_num > 0:
            multi_args = cmd_arg.extract_plain_text().strip().split(maxsplit=ensure_keys_num - 1)
        else:
            multi_args = cmd_arg.extract_plain_text().strip().split()

        if len(multi_args) < ensure_keys_num:
            multi_args.extend([default] * (ensure_keys_num - len(multi_args)))

        for index, arg in enumerate(multi_args):
            state.update({f'{key_prefix}_{index}': arg})

    return handle_parse_command_str_multi_args


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

    async def handle_parse_command_message_arg(matcher: Matcher, cmd_arg: Annotated[BaseMessage, CommandArg()]):
        """首次运行时解析命令参数"""
        message_arg = cmd_arg
        message_class = cmd_arg.__class__
        if message_arg:
            matcher.set_arg(key=key, message=message_arg)
        elif default is not None:
            matcher.set_arg(key=key, message=message_class(default))
        elif ensure_key:
            matcher.set_arg(key=key, message=message_class(''))

    return handle_parse_command_message_arg


def get_set_default_state_handler(
        key: str,
        value: Any | None = None,
        *,
        extra_data: dict[str, Any | None] | None = None
) -> T_Handler:
    """构造设置 State 默认值的 handler"""

    async def handle_set_default_state(state: T_State):
        """设置 State 默认值 (不覆盖已有键)"""
        update_data = {key: value}
        if extra_data is not None:
            update_data.update(extra_data)

        # 过滤 State 中已有的键值, 避免赋值异常
        update_data = {k: v for k, v in update_data.items() if k not in state.keys()}
        state.update(update_data)

    return handle_set_default_state


def get_shell_command_parse_failed_handler() -> T_Handler:
    """构造处理解析 Shell 命令失败的 handler"""

    async def handle_parse_failed(matcher: Matcher, shell_args: Annotated[ParserExit, ShellCommandArgs()]):
        """解析命令失败"""
        await matcher.finish(f'命令参数解析错误, 请确认后重试\n{shell_args.message}')

    return handle_parse_failed


__all__ = [
    'get_command_str_single_arg_parser_handler',
    'get_command_str_multi_args_parser_handler',
    'get_command_message_arg_parser_handler',
    'get_set_default_state_handler',
    'get_shell_command_parse_failed_handler',
]
