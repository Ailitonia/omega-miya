"""
@Author         : Ailitonia
@Date           : 2021/05/30 16:47
@FileName       : http_cat.py
@Project        : nonebot2_miya 
@Description    : Get http cat
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated

from nonebot.adapters import Message
from nonebot.log import logger
from nonebot.params import ArgStr, CommandArg
from nonebot.plugin import on_command
from nonebot.typing import T_State

from src.service import MatcherInterface, OmegaMessageSegment, enable_processor_state

from .data_source import get_http_cat


async def handle_parse_code(state: T_State, cmd_arg: Annotated[Message, CommandArg()]):
    """首次运行时解析命令参数"""
    code = cmd_arg.extract_plain_text().strip()
    if code:
        state.update({'code': code})
    else:
        state.update({'code': '200'})


@on_command(
    'http_cat',
    aliases={'HttpCat', 'httpcat'},
    handlers=[handle_parse_code],
    priority=10,
    block=True,
    state=enable_processor_state(name='HttpCat', level=20),
).got('code', prompt='猫猫已就绪, 请需要输入 Http 状态码:')
async def handle_httpcat(code: Annotated[str, ArgStr('code')]):
    code = code.strip()
    if not code.isdigit():
        code = '404'

    matcher_interface = MatcherInterface()
    try:
        code_image = await get_http_cat(http_code=code)
        await matcher_interface.send_reply(OmegaMessageSegment.image(code_image.path))
    except Exception as e:
        logger.error(f'HttpCat | 获取状态码{code!r}对应图片失败, {e!r}')
        await matcher_interface.send_reply('获取猫猫失败QAQ')


__all__ = []
