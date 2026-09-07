"""
@Author         : Ailitonia
@Date           : 2023/3/20 0:16
@FileName       : statistic
@Project        : nonebot2_miya
@Description    : 插件调用统计
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import time

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.log import logger
from nonebot.matcher import Matcher

from src.database import DATABASE_SESSION, StatisticDAL
from .processor_utils import parse_processor_state
from ...omega_base import OmegaMatcherInterface

_LOG_PREFIX: str = '<lc>Statistic</lc> | '
"""日志前缀"""


async def postprocessor_statistic(
        bot: BaseBot,
        event: BaseEvent,
        matcher: Matcher,
        db_session: DATABASE_SESSION,
) -> None:
    """运行后处理, 统计插件使用信息"""

    # 跳过临时会话, 避免冷却在命令交互中被不正常触发
    if matcher.temp:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Temp matcher, ignore')
        return

    # 跳过非插件创建的 Matcher
    if matcher.plugin is None:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Non-plugin matcher, ignore')
        return

    # 跳过没有配置自定义名称的(一般来说这样的插件也不用展示统计信息)
    if matcher.plugin.metadata is None:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Non-metadata plugin, ignore')
        return

    # 从 state 中解析 processor 配置要求
    custom_plugin_name = matcher.plugin.metadata.name
    module_name = matcher.plugin.module_name
    processor_state = parse_processor_state(state=matcher.state)

    # 跳过不需要 processor 处理的
    if not processor_state.enable_processor:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{custom_plugin_name} ignored with disabled processor')
        return

    event_depend = OmegaMatcherInterface.get_event_depend_cls(target_event=event)(bot=bot, event=event)
    event_entity_params = event_depend.extract_entity_params(acquire_type='event')
    user_entity_params = event_depend.extract_entity_params(acquire_type='user')

    try:
        await StatisticDAL(session=db_session).add(
            plugin_name=custom_plugin_name,
            module_name=module_name,
            call_timestamp=int(time.time()),
            call_entity_meta={
                'event': event_entity_params.model_dump(),
                'user': user_entity_params.model_dump(),
            },
            call_data={str(k): v for k, v in matcher.state.items()},
        )
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Add Plugin({custom_plugin_name}) statistic succeed')
    except Exception as e:
        logger.opt(colors=True).error(f'{_LOG_PREFIX}Add Plugin({custom_plugin_name}) statistic failed, {e}')


__all__ = [
    'postprocessor_statistic',
]
