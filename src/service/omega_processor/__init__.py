"""
@Author         : Ailitonia
@Date           : 2021/07/09 19:49
@FileName       : omega_processor
@Project        : nonebot2_miya 
@Description    : 统一处理冷却、权限等
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver
from nonebot.adapters import Bot, Event
from nonebot.matcher import Matcher
from nonebot.message import event_preprocessor, run_preprocessor

from .plugin_utils import enable_processor_state

from .universal import startup_init_plugins, preprocessor_plugin_manager, preprocessor_rate_limiting
from .onebot import *

driver = get_driver()


@driver.on_startup
async def handle_universal_on_startup():
    """启动时预处理"""
    # 初始化插件信息
    await startup_init_plugins()


@event_preprocessor
async def handle_universal_event_preprocessor(bot: Bot, event: Event):
    """事件预处理"""
    # 处理速率控制
    await preprocessor_rate_limiting(bot=bot, event=event)


@run_preprocessor
async def handle_universal_run_preprocessor(matcher: Matcher, event: Event):
    """运行预处理"""
    # 处理插件管理
    await preprocessor_plugin_manager(matcher=matcher, event=event)


__all__ = [
    'enable_processor_state'
]
