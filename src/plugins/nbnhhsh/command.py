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

from nonebot.adapters import Message
from nonebot.log import logger
from nonebot.params import ArgStr, CommandArg
from nonebot.plugin import on_command
from nonebot.typing import T_State

from src.service import MatcherInterface, enable_processor_state

from .data_source import query_guess


async def handle_parse_guess_word(state: T_State, cmd_arg: Annotated[Message, CommandArg()]):
    """首次运行时解析命令参数"""
    guess_word = cmd_arg.extract_plain_text().strip()
    if guess_word:
        state.update({'guess_word': guess_word})


@on_command(
    'nbnhhsh',
    aliases={'hhsh', '好好说话', '能不能好好说话'},
    handlers=[handle_parse_guess_word],
    priority=10,
    block=True,
    state=enable_processor_state(name='nbnhhsh', level=20),
).got('guess_word', prompt='有啥缩写搞不懂? 发来给你看看:')
async def handle_guess(guess_word: Annotated[str, ArgStr('guess_word')]):
    guess_word = guess_word.strip()

    matcher_interface = MatcherInterface()
    try:
        guess_result = await query_guess(guess=guess_word)
        if guess_result:
            trans = '\n'.join(guess_result)
            trans = f'为你找到了{guess_word!r}的以下解释:\n\n{trans}'
        else:
            trans = f'没有找到{guess_word!r}的解释'
        await matcher_interface.send_reply(trans)
    except Exception as e:
        logger.error(f'nbnhhsh | 获取{guess_word!r}查询结果失败, {e!r}')
        await matcher_interface.send_reply('发生了意外的错误, 请稍后再试')


__all__ = []
