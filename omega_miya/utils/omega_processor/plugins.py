"""
@Author         : Ailitonia
@Date           : 2021/09/12 12:36
@FileName       : plugins.py
@Project        : nonebot2_miya 
@Description    : 插件管理器相关组件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, get_loaded_plugins, logger
from nonebot.exception import IgnoredException
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event
from omega_miya.database import DBPlugin
from omega_miya.utils.omega_plugin_utils import ProcessUtils


global_config = get_driver().config
SUPERUSERS = global_config.superusers


async def startup_init_plugins():
    tasks = [DBPlugin(plugin_name=plugin.name).update(
        matchers=len(plugin.matcher), info=plugin.export.get('custom_name')
    ) for plugin in get_loaded_plugins()]

    plugins_init_result = await ProcessUtils.fragment_process(tasks=tasks, log_flag='Startup Init Plugins')

    for result in plugins_init_result:
        if result.error:
            import sys
            logger.opt(colors=True).critical(f'<r>初始化插件信息失败</r>, {result.info}')
            sys.exit(f'初始化插件信息失败, {result.info}')

    logger.opt(colors=True).success(f'<lg>插件信息初始化已完成.</lg>')


async def preprocessor_plugins_manager(matcher: Matcher, bot: Bot, event: Event, state: T_State):
    """
    插件管理处理 T_RunPreProcessor
    """
    user_id = getattr(event, 'user_id', -1)

    # 忽略超级用户
    if user_id in [int(x) for x in SUPERUSERS]:
        return

    plugin_name = matcher.plugin_name
    plugin_enable_result = await DBPlugin(plugin_name=plugin_name).get_enabled_status()
    if plugin_enable_result.success() and plugin_enable_result.result == 1:
        pass
    elif plugin_enable_result.success() and plugin_enable_result.result != 1:
        logger.warning(f'Plugins Manager | User: {user_id}, 尝试使用未启用的插件: {plugin_name}')
        raise IgnoredException('插件未启用')
    else:
        logger.error(f'Plugins Manager | 获取插件: {plugin_name} 启用状态失败, 插件状态异常, {plugin_enable_result.info}')
        raise IgnoredException('插件状态异常')


__all__ = [
    'startup_init_plugins',
    'preprocessor_plugins_manager'
]
