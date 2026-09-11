"""
@Author         : Ailitonia
@Date           : 2023/3/20 1:32
@FileName       : cost
@Project        : nonebot2_miya
@Description    : 命令消耗
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from decimal import Decimal

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import IgnoredException
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER

from src.database import DATABASE_SESSION
from ...omega_base import OmegaMatcherInterface
from .processor_utils import parse_processor_state

_CURRENCY_ALIAS: str = '硬币'
"""货币的显示别名"""
_LOG_PREFIX: str = '<lc>Command Cost</lc> | '
"""日志前缀"""


async def preprocessor_plugin_cost(
        bot: BaseBot,
        event: BaseEvent,
        matcher: Matcher,
        db_session: DATABASE_SESSION,
) -> None:
    """运行预处理, 命令消耗处理"""

    # 跳过临时会话, 避免冷却在命令交互中被不正常触发
    if matcher.temp:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Temp matcher, ignore')
        return

    # 跳过非插件创建的 Matcher
    if matcher.plugin is None:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Non-plugin matcher, ignore')
        return

    plugin_name = matcher.plugin.name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过超级用户
    if await SUPERUSER(bot=bot, event=event):
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} ignored by <ly>SUPERUSER</ly>')
        return

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} ignored with disabled processor')
        return

    # 跳过声明无消耗的
    if processor_state.cost <= 0:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} ignored with non-cost')
        return

    user_entity = OmegaMatcherInterface(
        bot=bot,
        event=event,
        matcher=matcher,
        acquire_type='user',
    ).get_current_entity(db_session=db_session)
    friendship = await user_entity.query_friendship()

    exist_currency = friendship.currency.quantize(Decimal('0.01'))
    cost = Decimal.from_float(processor_state.cost).quantize(Decimal('0.01'))

    if exist_currency < cost:
        echo_message = f'{_CURRENCY_ALIAS}不足! 命令消耗: {cost}, 持有: {exist_currency}'
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{user_entity.tid} currency not enough for cost')

        try:
            await matcher.send(message=echo_message)
        except Exception as e:
            logger.opt(colors=True).warning(
                f'{_LOG_PREFIX}{plugin_name} send cost not enough message failed, {e}'
            )
        raise IgnoredException(f'{_CURRENCY_ALIAS}不足')

    await user_entity.alter_friendship(currency=-cost)

    echo_message = f'已消耗 {cost} {_CURRENCY_ALIAS}来使用命令{processor_state.name!r}'
    logger.opt(colors=True).info(
        f'{_LOG_PREFIX}{user_entity.tid} cost <ly>{cost}</ly> for {processor_state.name!r}'
    )
    try:
        await matcher.send(message=echo_message)
    except Exception as e:
        logger.opt(colors=True).warning(
            f'{_LOG_PREFIX}{plugin_name} send cost not enough message failed, {e}'
        )


__all__ = [
    'preprocessor_plugin_cost',
]
