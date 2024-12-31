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
from nonebot.params import ArgStr, Depends, ShellCommandArgs
from nonebot.plugin import on_shell_command
from nonebot.rule import ArgumentParser, Namespace
from pydantic import BaseModel, ConfigDict

from src.params.handler import get_command_str_single_arg_parser_handler, get_shell_command_parse_failed_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state
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
    handlers=[get_shell_command_parse_failed_handler(),
              get_command_str_single_arg_parser_handler('word', ensure_key=True)],
    priority=10,
    block=True,
    state=enable_processor_state(
        name='Translate',
        level=30,
        auth_node='translate',
    ),
).got('word')
async def handle_translate(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        args: Annotated[Namespace, ShellCommandArgs()],
        word: Annotated[str | None, ArgStr('word')],
) -> None:
    parsed_args = parse_arguments(args=args)

    if parsed_args.word:
        translate_word = ' '.join(parsed_args.word).strip()
    elif word and word.strip():
        translate_word = word.strip()
    else:
        await interface.reject_reply('请发送需要翻译的内容:')

    try:
        result = await TencentTMT().text_translate(source_text=translate_word, source=args.source, target=args.target)
        if result.error:
            raise RuntimeError(result.Response.Error)
        await interface.send_reply(f'翻译结果:\n\n{result.Response.TargetText}')
    except Exception as e:
        logger.error(f'Translate | 翻译失败, {e}')
        await interface.send_reply('翻译失败, 发生了意外的错误, 请稍后再试')


__all__ = []
