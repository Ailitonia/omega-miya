"""
@Author         : Ailitonia
@Date           : 2023/3/20 0:16
@FileName       : statistic
@Project        : nonebot2_miya
@Description    : 插件调用统计
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from nonebot import logger
from nonebot.matcher import Matcher
from nonebot.internal.adapter import Bot, Event

from src.database import StatisticDAL, begin_db_session
from src.service import OmegaInterface

from ..plugin_utils import parse_processor_state


LOG_PREFIX: str = '<lc>Statistic</lc> | '


async def postprocessor_statistic(matcher: Matcher, bot: Bot, event: Event):
    """运行后处理, 统计插件使用信息"""

    # 跳过临时会话
    if matcher.temp:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Temp matcher, ignore')
        return

    # 跳过没有配置自定义名称的(一般来说这样的插件也不用展示统计信息)
    if matcher.plugin.metadata is None:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Non-metadata plugin, ignore')
        return

    custom_plugin_name = matcher.plugin.metadata.name

    # 从 state 中解析 processor 配置要求
    module_name = matcher.plugin.module_name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({custom_plugin_name}) ignored with disable processor')
        return

    # 跳过不需要 processor 交互的 matcher (一般来说这样的都是后台或响应式的不用展示统计信息)
    if not processor_state.echo_processor_result:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Plugin({custom_plugin_name}) ignored with disable echo')
        return

    try:
        async with OmegaInterface().get_entity(bot=bot, event=event) as entity:
            parent_entity_id = entity.parent_id
            entity_id = entity.entity_id
            call_info = f'{custom_plugin_name!r} called by {entity!r} in event {event}'

        async with begin_db_session() as session:
            dal = StatisticDAL(session=session)
            await dal.add(module_name=module_name, plugin_name=custom_plugin_name,
                          bot_self_id=bot.self_id, parent_entity_id=parent_entity_id, entity_id=entity_id,
                          call_time=datetime.now(), call_info=call_info)
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Add Plugin({custom_plugin_name}) statistic succeed')
    except Exception as e:
        logger.opt(colors=True).error(f'{LOG_PREFIX}Add Plugin({custom_plugin_name}) statistic failed, {e}')


__all__ = [
    'postprocessor_statistic'
]
