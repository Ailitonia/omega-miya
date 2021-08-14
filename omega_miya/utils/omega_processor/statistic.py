"""
@Author         : Ailitonia
@Date           : 2021/08/14 18:26
@FileName       : statistic.py
@Project        : nonebot2_miya 
@Description    : 插件调用统计
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from typing import Optional
from nonebot import logger
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.event import Event
from nonebot.adapters.cqhttp.bot import Bot
from omega_miya.database import DBStatistic


async def postprocessor_statistic(
        matcher: Matcher, exception: Optional[Exception], bot: Bot, event: Event, state: T_State):
    if matcher.temp:
        logger.debug('Postprocessor Statistic | Temp matcher, ignore')
        return
    elif matcher.priority >= 100:
        logger.debug('Postprocessor Statistic | Non-command matcher, ignore')
        return

    module_name = matcher.module_name
    plugin_name = matcher.plugin_name
    self_bot_id = int(bot.self_id)
    group_id = getattr(event, 'group_id', -1)
    user_id = getattr(event, 'user_id', -1)
    if exception:
        info = repr(exception)
    else:
        info = 'Success'
    raw_message = str(getattr(event, 'message', ''))
    if len(raw_message) >= 4096:
        raw_message = raw_message[:4096]

    add_statistic_result = await DBStatistic(self_bot_id=self_bot_id).add(
        module_name=module_name, plugin_name=plugin_name, group_id=group_id, user_id=user_id,
        using_datetime=datetime.now(), raw_message=raw_message, info=info
    )

    if add_statistic_result.error:
        logger.error(f'Postprocessor Statistic | Adding statistic failed, error: {add_statistic_result.info}')
    else:
        logger.debug('Postprocessor Statistic | Adding succeed')


__all__ = [
    'postprocessor_statistic'
]
