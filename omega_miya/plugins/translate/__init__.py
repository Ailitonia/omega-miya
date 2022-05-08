"""
@Author         : Ailitonia
@Date           : 2021/08/04 03:26
@FileName       : translate.py
@Project        : nonebot2_miya
@Description    : 翻译插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import on_command, logger
from nonebot.typing import T_State
from nonebot.rule import ArgumentParser
from nonebot.exception import ParserExit
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.permission import GROUP, PRIVATE_FRIEND
from nonebot.adapters.onebot.v11.message import Message
from nonebot.params import Depends, CommandArg, ArgStr

from omega_miya.service import init_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.web_resource.tencent_cloud import TencentTMT


# Custom plugin usage text
__plugin_custom_name__ = '翻译'
__plugin_usage__ = r'''【翻译插件】
简单的翻译插件
目前使用了腾讯云的翻译API

/翻译 [翻译内容]'''


translate = on_command(
    'Translate',
    aliases={'translate', '翻译'},
    # 使用run_preprocessor拦截权限管理, 在default_state初始化所需权限
    state=init_processor_state(name='translate', level=30, auth_node='translate'),
    permission=GROUP | PRIVATE_FRIEND,
    priority=20,
    block=True
)


def source_target_parser() -> ArgumentParser:
    """ argument parser"""
    parser = ArgumentParser(prog='Translate arguments parser', description='Parse translate arguments')
    parser.add_argument('-s', '--source', type=str, default='auto')
    parser.add_argument('-t', '--target', type=str, default='zh')
    parser.add_argument('word', nargs='*')
    return parser


@Depends
async def parse_translate_args(matcher: Matcher, state: T_State, cmd_arg: Message = CommandArg()):
    args = cmd_arg.extract_plain_text().strip().split()
    try:
        parse_result = source_target_parser().parse_args(args=args)
        state.update({
            'source': parse_result.source,
            'target': parse_result.target,
            'word': ' '.join(parse_result.word)
        })
    except ParserExit:
        await matcher.finish('无效的翻译参数QAQ')


@translate.handle(parameterless=[parse_translate_args])
async def handle_parse_expression(state: T_State):
    """首次运行时解析命令参数"""
    word = state.get('word', '')
    if not word.strip():
        state.pop('word')


@translate.got('word', prompt='请发送需要翻译的内容:')
async def handle_translate(matcher: Matcher, state: T_State, word: str = ArgStr('word')):
    source: str = state.get('source')
    target: str = state.get('target')
    word = word.strip()
    if not word:
        await matcher.reject(f'你没有发送任何内容呢, 请重新发送你想要翻译的内容:')

    translate_result = await run_async_catching_exception(TencentTMT().translate)(source_text=word,
                                                                                  source=source, target=target)
    if isinstance(translate_result, Exception) or translate_result.error:
        logger.error(f'Translate | 翻译失败, {translate_result}')
        await matcher.finish('翻译失败了QAQ, 发生了意外的错误')
    else:
        await matcher.finish(f'翻译结果:\n\n{translate_result.Response.TargetText}')
