"""
@Author         : Ailitonia
@Date           : 2023/3/20 1:32
@FileName       : cost
@Project        : nonebot2_miya
@Description    : 命令消耗
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from nonebot.exception import IgnoredException
from nonebot.internal.adapter import Bot, Event
from nonebot.matcher import Matcher

from src.database import begin_db_session
from src.service import OmegaMatcherInterface
from ..plugin_utils import parse_processor_state

SUPERUSERS = get_driver().config.superusers
CURRENCY_ALIAS: str = '硬币'
LOG_PREFIX: str = '<lc>Command Cost</lc> | '


async def preprocessor_plugin_cost(matcher: Matcher, bot: Bot, event: Event):
    """运行预处理, 命令消耗处理"""

    # 跳过临时 matcher 避免在命令交互中被不正常触发
    if matcher.temp:
        return

    # 跳过非插件创建的 Matcher
    if matcher.plugin is None:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Non-plugin matcher, ignore')
        return

    user_id = event.get_user_id()
    # 忽略超级用户
    if user_id in SUPERUSERS:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    plugin_name = matcher.plugin.name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({plugin_name}) ignored with disable processor')
        return

    # 跳过声明无消耗的
    if processor_state.cost <= 0:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({plugin_name}) ignored with non-cost')
        return

    async with begin_db_session() as session:
        entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='user')
        await entity.add_ignore_exists()
        friendship = await entity.query_friendship()

        if friendship.currency < processor_state.cost:
            echo_message = f'{CURRENCY_ALIAS}不足! 命令消耗: {int(processor_state.cost)}, 持有: {int(friendship.currency)}'
            logger.opt(colors=True).debug(f'{LOG_PREFIX}User({user_id}) currency not enough for cost')
            try:
                await matcher.send(message=echo_message)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'{LOG_PREFIX}Plugin({plugin_name}) send cost not enough tip message failed, {e!r}'
                )
            raise IgnoredException(f'{CURRENCY_ALIAS}不足')

        echo_message = f'已消耗 {processor_state.cost} {CURRENCY_ALIAS}使用命令{processor_state.name!r}'
        logger.opt(colors=True).info(
            f'{LOG_PREFIX}User({user_id}) cost <ly>{processor_state.cost}</ly> for {processor_state.name!r}'
        )
        try:
            await matcher.send(message=echo_message)
        except Exception as e:
            logger.opt(colors=True).warning(
                f'{LOG_PREFIX}Plugin({plugin_name}) send cost succeed tip message failed, {e!r}'
            )
        await entity.change_friendship(currency=-processor_state.cost)


__all__ = [
    'preprocessor_plugin_cost',
]
