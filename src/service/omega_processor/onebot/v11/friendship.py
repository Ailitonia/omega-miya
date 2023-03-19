"""
@Author         : Ailitonia
@Date           : 2023/3/20 1:03
@FileName       : friendship
@Project        : nonebot2_miya
@Description    : 用户好感度处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent, PrivateMessageEvent

from src.params.onebot_v11 import OneBotV11EntityDepend


LOG_PREFIX: str = '<lc>Friendship</lc> | '


async def postprocessor_friendship(bot: Bot, event: MessageEvent):
    """事件后处理， 用户好感度处理"""
    friendship_incremental = 0.01 if isinstance(event, PrivateMessageEvent) else 1
    currency_incremental = 1e-4 if isinstance(event, PrivateMessageEvent) else 5e-2

    entity_name = str(event.sender.nickname if event.sender.nickname else event.user_id)
    try:
        async with OneBotV11EntityDepend(acquire_type='user').get_entity(bot=bot, event=event) as entity:
            await entity.add_upgrade(entity_name=entity_name)
            await entity.change_friendship(energy=friendship_incremental, currency=currency_incremental)
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Increased User({event.user_id}) friendship succeed')
    except Exception as e:
        logger.opt(colors=True).error(f'{LOG_PREFIX}Increased User({event.user_id}) friendship failed, {e}')


__all__ = [
    'postprocessor_friendship'
]
