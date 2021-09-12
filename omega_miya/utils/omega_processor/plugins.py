"""
@Author         : Ailitonia
@Date           : 2021/09/12 12:36
@FileName       : plugins.py
@Project        : nonebot2_miya 
@Description    : 插件管理器相关组件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_loaded_plugins, logger
from omega_miya.database import DBPlugin
from omega_miya.utils.omega_plugin_utils import ProcessUtils


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


__all__ = [
    'startup_init_plugins'
]
