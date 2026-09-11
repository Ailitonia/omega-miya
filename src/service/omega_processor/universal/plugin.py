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
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.exception import IgnoredException
from nonebot.matcher import Matcher
from nonebot.permission import SUPERUSER
from sqlalchemy.exc import NoResultFound

from src.database import DATABASE_SESSION, PluginDAL, database_session

_DRIVER = get_driver()
_LOG_PREFIX: str = '<lc>Plugin Manager</lc> | '
"""日志前缀"""


@_DRIVER.on_startup
async def _startup_init_plugins():
    """初始化已加载的插件到数据库

    仅插入缺失的插件行, 已存在的行保持不变, 避免重启时将已禁用的插件重置为启用
    """
    try:
        async with database_session() as session:
            dal = PluginDAL(session=session)
            for plugin in get_loaded_plugins():
                try:
                    await dal.query_unique(plugin_name=plugin.name, module_name=plugin.module_name)
                except NoResultFound:
                    await dal.add_update_exist(
                        plugin_name=plugin.name,
                        module_name=plugin.module_name,
                        enabled=1,
                        info=plugin.metadata.name if plugin.metadata else None,
                    )
    except Exception as e:
        import sys
        logger.opt(colors=True).critical(f'{_LOG_PREFIX}<r>初始化插件信息失败</r>, {e}')
        sys.exit(f'初始化插件信息失败, {e}')

    logger.opt(colors=True).success(f'{_LOG_PREFIX}<lg>插件信息初始化已完成.</lg>')


async def preprocessor_plugin_manager(
        bot: BaseBot,
        event: BaseEvent,
        matcher: Matcher,
        db_session: DATABASE_SESSION,
) -> None:
    """运行预处理, 处理插件管理器"""

    # 跳过非插件创建的 Matcher
    if matcher.plugin is None:
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}Non-plugin matcher, ignore')
        return

    plugin_name = matcher.plugin.name
    module_name = matcher.plugin.module_name

    # 跳过超级用户
    if await SUPERUSER(bot=bot, event=event):
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}{plugin_name} ignored by <ly>SUPERUSER</ly>')
        return

    dal = PluginDAL(session=db_session)
    try:
        plugin = await dal.query_unique(plugin_name=plugin_name, module_name=module_name)
        plugin_enabled = True if plugin.enabled == 1 else False
        logger.opt(colors=True).debug(f'{_LOG_PREFIX}已注册插件 {plugin_name!r}, 启用状态: {plugin.enabled}')
    except NoResultFound:
        plugin_enabled = False
        logger.opt(colors=True).warning(f'{_LOG_PREFIX}未注册的插件 {plugin_name!r}')

    if not plugin_enabled:
        raise IgnoredException('插件未启用')


__all__ = [
    'preprocessor_plugin_manager',
]
