"""
@Author         : Ailitonia
@Date           : 2023/10/18 22:51
@FileName       : command
@Project        : nonebot2_miya
@Description    : 选择困难症帮助器插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
from typing import Annotated

from nonebot.params import ArgStr, Depends
from nonebot.plugin import on_command

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaMatcherInterface as OmMI, enable_processor_state


@on_command(
    'choice_helper',
    aliases={'帮我选', '选择困难症'},
    handlers=[get_command_str_single_arg_parser_handler('choices')],
    priority=10,
    block=True,
    state=enable_processor_state(name='choice_helper', level=10),
).got('choices', prompt='有啥选项, 发来我帮你选~')
async def handle_help_choices(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        choices: Annotated[str, ArgStr('choices')],
) -> None:
    choice_list = choices.strip().split()

    if not choice_list:
        await interface.finish_reply('你什么选项都没告诉我, 怎么帮你选OwO')

    result = random.choice(choice_list)
    result_text = f'''帮你从“{'”，“'.join(choice_list)}”中选择了：\n\n“{result}”'''

    await interface.finish_reply(result_text)


__all__ = []
