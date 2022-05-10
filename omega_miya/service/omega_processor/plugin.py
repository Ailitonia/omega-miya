"""
@Author         : Ailitonia
@Date           : 2021/09/12 12:36
@FileName       : plugin.py
@Project        : nonebot2_miya 
@Description    : 插件管理器相关组件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, get_loaded_plugins, logger
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.event import Event
from omega_miya.database import Plugin
from omega_miya.utils.process_utils import semaphore_gather


global_config = get_driver().config
SUPERUSERS = global_config.superusers


_log_prefix: str = '<lc>Plugin Manager</lc> | '


async def startup_init_plugins():
    tasks = [Plugin(
        plugin_name=plugin.name,
        module_name=plugin.module_name
    ).add_only(info=getattr(plugin.module, '__plugin_custom_name__', None)) for plugin in get_loaded_plugins()]

    plugins_init_result = await semaphore_gather(tasks=tasks, semaphore_num=1)

    for result in plugins_init_result:
        if isinstance(result, BaseException) or result.error:
            import sys
            logger.opt(colors=True).critical(f'{_log_prefix}<r>初始化插件信息失败</r>, {result}')
            sys.exit(f'初始化插件信息失败, {result}')

    logger.opt(colors=True).success(f'{_log_prefix}<lg>插件信息初始化已完成.</lg>')


async def preprocessor_plugin_manager(matcher: Matcher, event: Event):
    """处理插件管理器"""
    user_id = getattr(event, 'user_id', -1)

    # 忽略超级用户
    if user_id in [int(x) for x in SUPERUSERS]:
        logger.opt(colors=True).debug(f'{_log_prefix}ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name
    try:
        plugin_enable_result = await Plugin(plugin_name=plugin_name, module_name=module_name).query()
        if plugin_enable_result.success and plugin_enable_result.result.enabled == 1:
            logger.opt(colors=True).debug(f'{_log_prefix}User({user_id}) 执行已启用的插件: {plugin_name}')
        elif plugin_enable_result.success and plugin_enable_result.result.enabled != 1:
            logger.opt(colors=True).warning(f'{_log_prefix}User({user_id}) 尝试使用未启用的插件: {plugin_name}')
            raise IgnoredException('插件未启用')
        else:
            logger.opt(colors=True).error(f'{_log_prefix}获取插件: {plugin_name} 启用状态失败, '
                                          f'插件状态异常, {plugin_enable_result.info}')
            raise IgnoredException('插件状态异常')
    except Exception as e:
        if isinstance(e, IgnoredException):
            raise e
        logger.opt(colors=True).error(f'{_log_prefix}获取插件: {plugin_name} 启用状态失败, 数据库操作异常, {e}')
        raise IgnoredException('插件状态异常')


__all__ = [
    'startup_init_plugins',
    'preprocessor_plugin_manager'
]
