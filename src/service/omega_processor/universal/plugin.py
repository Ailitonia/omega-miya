"""
@Author         : Ailitonia
@Date           : 2023/3/19 16:49
@FileName       : plugin
@Project        : nonebot2_miya
@Description    : 插件预处理器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, get_loaded_plugins, logger
from nonebot.adapters import Event
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.plugin import Plugin
from sqlalchemy.exc import NoResultFound

from src.database import PluginDAL, begin_db_session
from src.utils import semaphore_gather

LOG_PREFIX: str = '<lc>Plugin Manager</lc> | '
SUPERUSERS = get_driver().config.superusers


async def _add_update_plugin(plugin: Plugin) -> None:
    """更新数据库中插件信息"""
    async with begin_db_session() as session:
        await PluginDAL(session=session).upsert(
            plugin_name=plugin.name,
            module_name=plugin.module_name,
            enabled=1,
            info=plugin.metadata.name if plugin.metadata else None,
        )


async def startup_init_plugins():
    """初始化已加载的插件到数据库"""
    tasks = [_add_update_plugin(plugin=plugin) for plugin in get_loaded_plugins()]
    plugins_init_result = await semaphore_gather(tasks=tasks, semaphore_num=10)

    for result in plugins_init_result:
        if isinstance(result, Exception):
            import sys
            logger.opt(colors=True).critical(f'{LOG_PREFIX}<r>初始化插件信息失败</r>, {result}')
            sys.exit(f'初始化插件信息失败, {result}')

    logger.opt(colors=True).success(f'{LOG_PREFIX}<lg>插件信息初始化已完成.</lg>')


async def preprocessor_plugin_manager(matcher: Matcher, event: Event):
    """运行预处理, 处理插件管理器"""
    try:
        user_id = event.get_user_id()
    except (NotImplementedError, ValueError):
        logger.opt(colors=True).trace(f'{LOG_PREFIX}Ignored with no-user_id event')
        return
    except Exception as e:
        logger.opt(colors=True).error(f'{LOG_PREFIX}Detecting event type failed, {e}')
        return

    # 跳过非插件创建的 Matcher
    if matcher.plugin is None:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Non-plugin matcher, ignore')
        return

    # 忽略超级用户
    if user_id in SUPERUSERS:
        logger.opt(colors=True).debug(f'{LOG_PREFIX}Ignored with <ly>SUPERUSER({user_id})</ly>')
        return

    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name

    async with begin_db_session() as session:
        dal = PluginDAL(session=session)
        try:
            plugin = await dal.query_unique(plugin_name=plugin_name, module_name=module_name)
            plugin_enabled = True if plugin.enabled == 1 else False
            logger.opt(colors=True).debug(f'{LOG_PREFIX}已注册插件 {plugin_name!r}, 启用状态: {plugin.enabled}')
        except NoResultFound:
            plugin_enabled = False
            logger.opt(colors=True).warning(f'{LOG_PREFIX}未注册的插件 {plugin_name!r}')
        except Exception as e:
            plugin_enabled = False
            logger.opt(colors=True).error(f'{LOG_PREFIX}插件 {plugin_name!r} 状态异常, {e}')

    if not plugin_enabled:
        raise IgnoredException('插件未启用')


__all__ = [
    'startup_init_plugins',
    'preprocessor_plugin_manager',
]
