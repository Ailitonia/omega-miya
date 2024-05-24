"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : maybe.py
@Project        : nonebot2_miya
@Description    : 求签
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import Annotated

from nonebot.params import ArgStr, Depends
from nonebot.plugin import on_command

from src.params.handler import get_command_str_single_arg_parser_handler
from src.service import OmegaInterface, enable_processor_state

from .helpers import query_divination


@on_command(
    'maybe',
    aliases={'求签'},
    handlers=[get_command_str_single_arg_parser_handler('divination_text')],
    priority=10,
    block=True,
    state=enable_processor_state(name='Maybe', level=10),
).got('divination_text', prompt='你想问什么事呢?')
async def handle_divination(
        interface: Annotated[OmegaInterface, Depends(OmegaInterface('user'))],
        divination_text: Annotated[str, ArgStr('divination_text')]
) -> None:
    divination_text = divination_text.strip()
    interface.refresh_matcher_state()

    user_nickname = interface.get_event_handler().get_user_nickname()

    result_text = query_divination(divination_text=divination_text, user_id=interface.entity.tid)
    today = datetime.now().strftime('%Y年%m月%d日')
    send_message = f'今天是{today}\n{user_nickname}{result_text}'
    await interface.send_reply(send_message)


__all__ = []
