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

from nonebot.adapters import Message
from nonebot.params import ArgStr, CommandArg, Depends
from nonebot.plugin import on_command
from nonebot.typing import T_State

from src.service import EntityInterface, MatcherInterface, enable_processor_state

from .helpers import query_divination


async def handle_parse_divination_text(state: T_State, cmd_arg: Annotated[Message, CommandArg()]):
    """首次运行时解析命令参数"""
    divination_text = cmd_arg.extract_plain_text().strip()
    if divination_text:
        state.update({'divination_text': divination_text})


@on_command(
    'maybe',
    aliases={'求签'},
    handlers=[handle_parse_divination_text],
    priority=10,
    block=True,
    state=enable_processor_state(name='Maybe', level=10),
).got('divination_text', prompt='你想问什么事呢?')
async def handle_divination(
        entity_interface: Annotated[EntityInterface, Depends(EntityInterface('user'))],
        divination_text: Annotated[str, ArgStr('divination_text')]
) -> None:
    divination_text = divination_text.strip()
    matcher_interface = MatcherInterface()
    user_nickname = matcher_interface.get_event_handler().get_user_nickname()

    result_text = query_divination(divination_text=divination_text, user_id=entity_interface.entity.tid)
    today = datetime.now().strftime('%Y年%m月%d日')
    send_message = f'今天是{today}\n{user_nickname}{result_text}'
    await matcher_interface.send_reply(send_message)


__all__ = []
