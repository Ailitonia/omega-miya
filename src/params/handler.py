"""
@Author         : Ailitonia
@Date           : 2023/7/17 21:29
@FileName       : handler
@Project        : nonebot2_miya
@Description    : 通用处理流程
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from nonebot_plugin_alconna.uniseg.segment import Media

if TYPE_CHECKING:
    from nonebot_plugin_alconna import AlconnaMatcher, Match
    from nonebot_plugin_alconna.uniseg import UniMessage

    from src.service import OmegaMatcherInterface


async def ensure_arg_message(
        matcher: 'AlconnaMatcher',
        interface: 'OmegaMatcherInterface',
        arg: 'Match[UniMessage]',
        prompt_text: str,
        timeout: float,
) -> 'UniMessage':
    """确保命令参数已提供, 获取原始消息, 缺失时通过 prompt 追问获取

    与 ensure_arg_text 不同, 本函数不 strip, 原样保留整条消息(含 @ 等控制段), 调用方负责剔除 Reply/Reference 段;
    无论参数来自命令还是 prompt 追问, 纯空白文本且无任何媒体段均视为无效参数, 仅媒体(图片等)消息视为有效参数
    """
    message = arg.result if arg.available else None
    if message is None or not message:
        message = await matcher.prompt(prompt_text, timeout=timeout)
        if message is None:
            await interface.finish_reply('等待输入超时, 已取消操作')

    if not message.extract_plain_text().strip() and not message.select(Media):
        await interface.finish_reply('未提供有效参数, 已取消操作')

    return message


async def ensure_arg_text(
        matcher: 'AlconnaMatcher',
        interface: 'OmegaMatcherInterface',
        arg: 'Match[str]',
        prompt_text: str,
        timeout: float,
) -> str:
    """确保命令参数已提供, 缺失时通过 prompt 追问获取"""
    if arg.available and (text := arg.result.strip()):
        return text

    resp = await matcher.prompt(prompt_text, timeout=timeout)
    if resp is None:
        await interface.finish_reply('等待输入超时, 已取消操作')
    text = resp.extract_plain_text().strip()
    if not text:
        await interface.finish_reply('未提供有效参数, 已取消操作')
    return text


async def ensure_multi_args_text(
        matcher: 'AlconnaMatcher',
        interface: 'OmegaMatcherInterface',
        multi_args: 'Match[Sequence[str]]',
        prompt_text: str,
        timeout: float,
) -> list[str]:
    """确保一个或多个命令参数内容已提供, 合并变长参数或 prompt 响应"""
    args_list: list[str] = []
    if multi_args.available:
        args_result = multi_args.result
        if isinstance(args_result, str) and (arg := args_result.strip()):
            args_list.append(arg)
        else:
            args_list.extend(x for x in (arg.strip() for arg in args_result) if x)

    if args_list:
        return args_list

    resp = await matcher.prompt(prompt_text, timeout=timeout)
    if resp is None:
        await interface.finish_reply('等待输入超时, 已取消操作')

    text = resp.extract_plain_text().strip()
    if not text:
        await interface.finish_reply('未提供有效参数, 已取消操作')

    args_list.extend(x for x in (arg.strip() for arg in text.split()) if x)
    return args_list


__all__ = [
    'ensure_arg_message',
    'ensure_arg_text',
    'ensure_multi_args_text',
]
