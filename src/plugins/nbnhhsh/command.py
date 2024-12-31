"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : command.py
@Project        : nonebot2_miya
@Description    : 能不能好好说话
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import ArgStr, Depends
from nonebot.plugin import on_command

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaMatcherInterface as OmMI
from src.service import enable_processor_state
from .data_source import query_guess


@on_command(
    'nbnhhsh',
    aliases={'hhsh', '好好说话', '能不能好好说话'},
    handlers=[get_command_str_single_arg_parser_handler('guess_word')],
    priority=10,
    block=True,
    state=enable_processor_state(name='nbnhhsh', level=20),
).got('guess_word', prompt='有啥缩写搞不懂? 发来给你看看:')
async def handle_guess(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        guess_word: Annotated[str, ArgStr('guess_word')],
) -> None:
    guess_word = guess_word.strip()

    try:
        guess_result = await query_guess(guess=guess_word)
        if guess_result:
            trans = '\n'.join(guess_result)
            trans = f'为你找到了{guess_word!r}的以下解释:\n\n{trans}'
        else:
            trans = f'没有找到{guess_word!r}的解释'
        await interface.send_reply(trans)
    except Exception as e:
        logger.error(f'nbnhhsh | 获取{guess_word!r}查询结果失败, {e!r}')
        await interface.send_reply('发生了意外的错误, 请稍后再试')


__all__ = []
