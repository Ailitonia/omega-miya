"""
@Author         : Ailitonia
@Date           : 2021/08/04 03:26
@FileName       : translate.py
@Project        : nonebot2_miya
@Description    : 翻译插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import Depends, ShellCommandArgs
from nonebot.plugin import on_shell_command
from nonebot.rule import ArgumentParser, Namespace
from pydantic import BaseModel, ConfigDict

from src.params.handler import get_shell_command_parse_failed_handler
from src.service import OmegaInterface, enable_processor_state
from src.utils.tencent_cloud_api import TencentTMT


def get_parser() -> ArgumentParser:
    parser = ArgumentParser(prog='Translate arguments parser', description='Parse translate arguments')
    parser.add_argument('-s', '--source', type=str, default='auto')
    parser.add_argument('-t', '--target', type=str, default='zh')
    parser.add_argument('word', nargs='*')
    return parser


class TranslateArguments(BaseModel):
    source: str
    target: str
    word: list[str]
    model_config = ConfigDict(extra='ignore', from_attributes=True)


def parse_arguments(args: Namespace) -> TranslateArguments:
    """解析搜索命令参数"""
    return TranslateArguments.model_validate(args)


@on_shell_command(
    'translate',
    aliases={'翻译', 'Translate'},
    parser=get_parser(),
    handlers=[get_shell_command_parse_failed_handler()],
    priority=10,
    block=True,
    state=enable_processor_state(
        name='Translate',
        level=30,
        auth_node='translate',
    ),
).handle()
async def handle_translate(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface())],
        args: Annotated[Namespace, ShellCommandArgs()]
) -> None:
    args = parse_arguments(args=args)
    interface.refresh_matcher_state()

    word = ' '.join(args.word).strip()

    if not word:
        await interface.finish(f'未提供待翻译内容, 请确认后再重试吧')

    try:
        translate_result = await TencentTMT().translate(source_text=word, source=args.source, target=args.target)
        if translate_result.error:
            raise RuntimeError(translate_result.Response.Error)
        await interface.send_reply(f'翻译结果:\n\n{translate_result.Response.TargetText}')
    except Exception as e:
        logger.error(f'Translate | 翻译失败, {e}')
        await interface.send_reply('翻译失败, 发生了意外的错误, 请稍后再试')


__all__ = []
