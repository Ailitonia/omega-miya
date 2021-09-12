"""
@Author         : Ailitonia
@Date           : 2021/07/09 19:49
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 集合全部 processor 统一处理冷却、权限等
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from nonebot import get_driver
from nonebot.message import event_preprocessor, event_postprocessor, run_preprocessor, run_postprocessor
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.event import Event, MessageEvent
from nonebot.adapters.cqhttp.bot import Bot
from .plugins import startup_init_plugins, preprocessor_plugins_manager
from .permission import preprocessor_permission
from .cooldown import preprocessor_cooldown
from .favorability import postprocessor_favorability
from .history import postprocessor_history
from .statistic import postprocessor_statistic
from .rate_limiting import preprocessor_rate_limiting


driver = get_driver()


# 启动时预处理
@driver.on_startup
async def handle_on_startup():
    # 初始化插件信息
    await startup_init_plugins()


# 事件预处理
@event_preprocessor
async def handle_event_preprocessor(bot: Bot, event: Event, state: T_State):
    pass


# 运行预处理
@run_preprocessor
async def handle_run_preprocessor(matcher: Matcher, bot: Bot, event: Event, state: T_State):
    # 处理插件管理
    await preprocessor_plugins_manager(matcher=matcher, bot=bot, event=event, state=state)
    # 针对消息事件的处理
    if isinstance(event, MessageEvent):
        # 处理权限
        await preprocessor_permission(matcher=matcher, bot=bot, event=event, state=state)
        # 处理冷却
        await preprocessor_cooldown(matcher=matcher, bot=bot, event=event, state=state)
        # 处理速率控制
        await preprocessor_rate_limiting(matcher=matcher, bot=bot, event=event, state=state)


# 运行后处理
@run_postprocessor
async def handle_run_postprocessor(
        matcher: Matcher, exception: Optional[Exception], bot: Bot, event: Event, state: T_State):
    # 处理插件统计
    if isinstance(event, MessageEvent):
        await postprocessor_statistic(matcher=matcher, exception=exception, bot=bot, event=event, state=state)


# 事件后处理
@event_postprocessor
async def handle_event_postprocessor(bot: Bot, event: Event, state: T_State):
    # 处理历史记录
    await postprocessor_history(bot=bot, event=event, state=state)
    # 处理好感度
    if isinstance(event, MessageEvent):
        await postprocessor_favorability(bot=bot, event=event, state=state)
