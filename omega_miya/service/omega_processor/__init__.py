"""
@Author         : Ailitonia
@Date           : 2021/07/09 19:49
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : 集合全部 processor 统一处理冷却、权限等
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver
from nonebot.message import event_preprocessor, event_postprocessor, run_preprocessor, run_postprocessor
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event, MessageEvent
from nonebot.exception import IgnoredException

from omega_miya.service.gocqhttp_guild_patch import GuildMessageEvent, ChannelNoticeEvent

from .cancellation import preprocessor_cancellation
from .cooldown import preprocessor_cooldown
from .favorability import postprocessor_friendship
from .history import postprocessor_history
from .plugin import startup_init_plugins, preprocessor_plugin_manager
from .permission import preprocessor_permission
from .rate_limiting import preprocessor_rate_limiting, preprocessor_rate_limiting_cooldown
from .statistic import postprocessor_statistic


driver = get_driver()


@driver.on_startup
async def handle_on_startup():
    """启动时预处理"""
    # 初始化插件信息
    await startup_init_plugins()


@event_preprocessor
async def handle_event_preprocessor(bot: Bot, event: Event):
    """事件预处理"""
    # 暂时不处理频道事件
    if isinstance(event, (GuildMessageEvent, ChannelNoticeEvent)):
        raise IgnoredException('Ignore Guild Event')

    # 针对消息事件的处理
    if isinstance(event, MessageEvent):
        # 处理速率控制
        await preprocessor_rate_limiting(bot=bot, event=event)
        await preprocessor_rate_limiting_cooldown(bot=bot, event=event)


@run_preprocessor
async def handle_run_preprocessor(matcher: Matcher, bot: Bot, event: Event):
    """运行预处理"""
    # 处理插件管理
    await preprocessor_plugin_manager(matcher=matcher, event=event)
    # 针对消息事件的处理
    if isinstance(event, MessageEvent):
        # 处理权限
        await preprocessor_permission(matcher=matcher, bot=bot, event=event)
        # 处理冷却
        await preprocessor_cooldown(matcher=matcher, bot=bot, event=event)
        # 处理取消
        await preprocessor_cancellation(matcher=matcher, bot=bot, event=event)


@run_postprocessor
async def handle_run_postprocessor(matcher: Matcher, bot: Bot, event: Event):
    """运行后处理"""
    # 处理插件统计
    await postprocessor_statistic(matcher=matcher, bot=bot, event=event)


@event_postprocessor
async def handle_event_postprocessor(bot: Bot, event: Event):
    """事件后处理"""
    # 处理历史记录
    await postprocessor_history(event=event)
    # 针对消息事件的处理
    if isinstance(event, MessageEvent):
        # 处理好感度
        await postprocessor_friendship(bot=bot, event=event)
