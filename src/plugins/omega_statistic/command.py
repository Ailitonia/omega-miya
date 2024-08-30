"""
@Author         : Ailitonia
@Date           : 2023/7/8 14:53
@FileName       : command
@Project        : nonebot2_miya
@Description    : 统计信息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import CommandGroup

from src.database import StatisticDAL
from src.service import OmegaMatcherInterface as OmMI, OmegaMessageSegment, enable_processor_state
from .helpers import draw_statistics

# 注册事件响应器
statistic = CommandGroup(
    'statistic',
    priority=10,
    block=True,
    state=enable_processor_state(name='OmegaStatistic', level=10)
)


@statistic.command('event-entity', aliases={'统计信息', '使用统计', '插件统计'}).handle()
async def handle_event_entity_statistic(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        statistic_dal: Annotated[StatisticDAL, Depends(StatisticDAL.dal_dependence)],
) -> None:
    try:
        statistic_data = await statistic_dal.count_by_condition(
            bot_self_id=interface.bot.self_id,
            parent_entity_id=interface.entity.parent_id,
            entity_id=interface.entity.entity_id
        )
        statistic_image = await draw_statistics(
            statistics_data=statistic_data, title=f'{interface.entity.tid} 插件使用情况统计'
        )
        logger.success(f'OmegaStatistic 获取 {interface.entity} 统计信息成功')
        await interface.send_reply(OmegaMessageSegment.image(statistic_image.path))
    except Exception as e:
        logger.error(f'OmegaStatistic 获取 {interface.entity} 统计信息失败, {e!r}')
        await interface.send_reply(f'获取统计信息失败, 请稍后再试或联系管理员处理')


@statistic.command('bot-all', permission=SUPERUSER).handle()
async def handle_bot_all_statistic(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        statistic_dal: Annotated[StatisticDAL, Depends(StatisticDAL.dal_dependence)],
) -> None:
    try:
        statistic_data = await statistic_dal.count_by_condition(bot_self_id=interface.bot.self_id)
        statistic_image = await draw_statistics(
            statistics_data=statistic_data, title=f'{interface.bot.type} Bot {interface.bot.self_id} 插件使用情况统计'
        )
        logger.success(f'OmegaStatistic 获取 {interface.bot} 统计信息成功')
        await interface.send_reply(OmegaMessageSegment.image(statistic_image.path))
    except Exception as e:
        logger.error(f'OmegaStatistic 获取 {interface.bot} 统计信息失败, {e!r}')
        await interface.send_reply(f'获取统计信息失败, 请稍后再试或联系管理员处理')


__all__ = []
