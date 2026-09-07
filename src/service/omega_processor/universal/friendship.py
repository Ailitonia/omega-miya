"""
@Author         : Ailitonia
@Date           : 2023/3/20 1:03
@FileName       : friendship
@Project        : nonebot2_miya
@Description    : 用户好感度处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from decimal import Decimal

from nonebot import logger
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent

from src.database import DATABASE_SESSION
from ...omega_base import OmegaMatcherInterface

_ENERGY_INCREMENTAL: float = 0.5
"""每条消息的能量增长值"""
_CURRENCY_INCREMENTAL: float = 0.125
"""每条消息的货币增长值"""
_LOG_PREFIX: str = '<lc>Friendship</lc> | '
"""日志前缀"""


async def postprocessor_friendship(
        bot: BaseBot,
        event: BaseEvent,
        db_session: DATABASE_SESSION,
) -> None:
    """事件后处理, 用户好感度处理"""
    user_entity = OmegaMatcherInterface.get_target_entity(
        bot=bot,
        event=event,
        db_session=db_session,
        acquire_type='user',
    )

    energy_incremental = Decimal.from_float(_ENERGY_INCREMENTAL).quantize(Decimal('0.0001'))
    currency_incremental = Decimal.from_float(_CURRENCY_INCREMENTAL).quantize(Decimal('0.0001'))

    friendship = await user_entity.alter_friendship(energy=energy_incremental, currency=currency_incremental)
    logger.opt(colors=True).debug(f'{_LOG_PREFIX}Increased {user_entity.tid} energy/currency, {friendship}')


__all__ = [
    'postprocessor_friendship',
]
