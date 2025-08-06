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

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import on_command

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import OmegaMessageSegment, enable_processor_state
from .data_source import get_http_cat


@on_command(
    'http-cat',
    aliases={'HttpCat', 'httpcat', 'http_cat'},
    handlers=[get_command_str_single_arg_parser_handler('code', default='200')],
    priority=10,
    block=True,
    state=enable_processor_state(name='HttpCat', level=20),
).got('code', prompt='猫猫已就绪, 请输入 Http 状态码:')
async def handle_httpcat(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        code: Annotated[str, ArgStr('code')],
) -> None:
    code = code.strip()
    if not code.isdigit():
        code = '404'

    try:
        code_image = await get_http_cat(http_code=code)
        await interface.send_reply(OmegaMessageSegment.image(await code_image.get_hosting_path()))
    except Exception as e:
        logger.error(f'HttpCat | 获取状态码{code!r}对应图片失败, {e!r}')
        await interface.send_reply('获取猫猫失败QAQ')


__all__ = []
