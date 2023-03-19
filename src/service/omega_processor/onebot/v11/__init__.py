"""
@Author         : Ailitonia
@Date           : 2023/3/19 16:45
@FileName       : v11
@Project        : nonebot2_miya
@Description    : onebot v11 processor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.message import event_postprocessor, run_preprocessor, run_postprocessor
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event, MessageEvent

from .cancellation import preprocessor_cancellation
from .cooldown import preprocessor_global_cooldown, preprocessor_plugin_cooldown
from .cost import preprocessor_plugin_cost
from .friendship import postprocessor_friendship
from .history import postprocessor_history
from .permission import preprocessor_global_permission, preprocessor_plugin_permission
from .statistic import postprocessor_statistic


@run_preprocessor
async def handle_onebot_v11_run_preprocessor(matcher: Matcher, bot: Bot, event: Event):
    """运行预处理"""
    # 针对消息事件的处理
    if isinstance(event, MessageEvent):
        # 处理用户取消
        await preprocessor_cancellation(matcher=matcher, event=event)
        # 处理权限
        await preprocessor_global_permission(matcher=matcher, bot=bot, event=event)
        await preprocessor_plugin_permission(matcher=matcher, bot=bot, event=event)
        # 处理冷却
        await preprocessor_global_cooldown(matcher=matcher, bot=bot, event=event)
        await preprocessor_plugin_cooldown(matcher=matcher, bot=bot, event=event)
        # 处理消耗
        await preprocessor_plugin_cost(matcher=matcher, bot=bot, event=event)


@run_postprocessor
async def handle_onebot_v11_run_postprocessor(matcher: Matcher, bot: Bot, event: Event):
    """运行后处理"""
    # 处理插件统计
    await postprocessor_statistic(matcher=matcher, bot=bot, event=event)


@event_postprocessor
async def handle_onebot_v11_event_postprocessor(bot: Bot, event: Event):
    """事件后处理"""
    # 处理历史记录
    await postprocessor_history(event=event)
    # 针对消息事件的处理
    if isinstance(event, MessageEvent):
        # 处理好感度
        await postprocessor_friendship(bot=bot, event=event)


__all__ = []
