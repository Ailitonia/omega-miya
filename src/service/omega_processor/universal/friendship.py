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
from nonebot.internal.adapter import Bot, Event

from src.database import begin_db_session
from src.service import OmegaMatcherInterface

LOG_PREFIX: str = '<lc>Friendship</lc> | '
ENERGY_INCREMENTAL = 0.5
CURRENCY_INCREMENTAL = 0.125


async def postprocessor_friendship(bot: Bot, event: Event):
    """事件后处理， 用户好感度处理"""
    user_id = event.get_user_id()

    try:
        async with begin_db_session() as session:
            entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='user')
            await entity.add_ignore_exists()
            await entity.change_friendship(energy=ENERGY_INCREMENTAL, currency=CURRENCY_INCREMENTAL)
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Increased User({user_id}) friendship succeed')
    except Exception as e:
        logger.opt(colors=True).error(f'{LOG_PREFIX}Increased User({user_id}) friendship failed, {e}')


__all__ = [
    'postprocessor_friendship',
]
