"""
@Author         : Ailitonia
@Date           : 2021/08/28 20:33
@FileName       : favorability.py
@Project        : nonebot2_miya 
@Description    : 好感度处理模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import MessageEvent, PrivateMessageEvent, GroupMessageEvent
from omega_miya.database import DBUser


async def postprocessor_favorability(bot: Bot, event: MessageEvent, state: T_State):
    user = DBUser(user_id=event.user_id)
    if isinstance(event, GroupMessageEvent):
        result = await user.favorability_add(energy=1)
    elif isinstance(event, PrivateMessageEvent):
        result = await user.favorability_add(energy=0.01)
    else:
        return

    if result.error and result.info == 'NoResultFound':
        if isinstance(event, GroupMessageEvent):
            result = await user.favorability_reset(energy=1)
        elif isinstance(event, PrivateMessageEvent):
            result = await user.favorability_reset(energy=0.01)

    if result.error:
        logger.error(f'Add User {event.user_id} favorability-energy Failed, {result.info}')
    else:
        logger.debug(f'Add User {event.user_id} favorability-energy Success, energy increased')


__all__ = [
    'postprocessor_favorability'
]
