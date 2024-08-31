"""
@Author         : Ailitonia
@Date           : 2023/7/3 3:02
@FileName       : core
@Project        : nonebot2_miya
@Description    : 核心管理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import timedelta
from typing import Annotated

from nonebot.adapters import Bot, Event, Message
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import ArgStr, CommandArg, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import CommandGroup, get_plugin, get_loaded_plugins
from nonebot.typing import T_State

from src.database import PluginDAL
from src.params.permission import IS_ADMIN
from src.service import OmegaMatcherInterface as OmMI, enable_processor_state
from .helpers import get_all_plugins_desc, get_plugin_desc, get_plugin_auth_node, list_command_by_priority
from .status import get_status

DEFAULT_PERMISSION_LEVEL: int = 30
"""初始化时默认的权限等级"""
MAX_PERMISSION_LEVEL: int = 100
"""通过本命令可以设置的最高权限等级"""


# 注册事件响应器
omega = CommandGroup(
    'omega',
    permission=SUPERUSER,
    priority=20,
    block=True,
    state=enable_processor_state(name='OmegaCoreManager', enable_processor=False)
)


async def handle_parse_args(state: T_State, cmd_arg: Annotated[Message, CommandArg()]):
    """首次运行时解析命令参数"""
    cmd_args = cmd_arg.extract_plain_text().strip().split()

    for index, arg in enumerate(cmd_args):
        state.update({f'omega_arg_{index}': arg})


@omega.command(tuple(), aliases={'Omega'}, permission=None, priority=10).handle()
async def handle_hello(matcher: Matcher):
    await matcher.finish('你好呀~\n我是Omega Miya~\n请问您今天要来点喵娘吗?')


@omega.command('start', aliases={'Start', 'start', 'EnableOmega', 'enable_omega'}, permission=IS_ADMIN).handle()
async def handle_start(interface: Annotated[OmMI, Depends(OmMI.depend())]):
    try:
        await interface.entity.add_ignore_exists()
        await interface.entity.enable_global_permission()
        await interface.entity.set_permission_level(DEFAULT_PERMISSION_LEVEL)
        await interface.entity.commit_session()

        logger.success(f'Omega 启用成功, Entity: {interface.entity}')
        await interface.matcher.send('Omega 启用/初始化成功')
    except Exception as e:
        logger.error(f'Omega 启用/初始化失败, {e!r}')
        await interface.matcher.send('Omega 启用/初始化失败, 请联系管理员处理')


@omega.command('disable', aliases={'DisableOmega', 'disable_omega'}, permission=IS_ADMIN).handle()
async def handle_disable(interface: Annotated[OmMI, Depends(OmMI.depend())]):
    try:
        await interface.entity.add_ignore_exists()
        await interface.entity.disable_global_permission()
        await interface.entity.set_permission_level(0)
        await interface.entity.commit_session()

        logger.success(f'Omega 禁用成功, Entity: {interface.entity}')
        await interface.matcher.send('Omega 禁用成功')
    except Exception as e:
        logger.error(f'Omega 禁用失败, {e!r}')
        await interface.matcher.send('Omega 禁用失败, 请联系管理员处理')


@omega.command('status', aliases={'Status', 'status'}, permission=None, priority=10).handle()
async def handle_status(interface: Annotated[OmMI, Depends(OmMI.depend())]):
    try:
        global_permission = await interface.entity.query_global_permission()
        global_permission_text = '已启用(Enabled)' if global_permission.available == 1 else '已禁用(Disabled)'

        permission_level = await interface.entity.query_permission_level()
        permission_level_text = f'Level-{permission_level.available}'

        permission_status = f'Omega 功能开关: {global_permission_text}\nOmega 权限等级: {permission_level_text}'

        status = await get_status()
        await interface.matcher.send(f'{permission_status}\n\nOmega 运行状态:\n{"-" * 16}\n{status}')
    except Exception as e:
        logger.error(f'获取 Omega 状态失败, {e!r}')
        await interface.matcher.send('获取 Omega 状态失败, 请尝试使用 "/Start" 命令初始化, 或联系管理员处理')


@omega.command('help', aliases={'Help', 'help', '帮助'}, permission=None, priority=10).handle()
async def handle_help(bot: Bot, event: Event, matcher: Matcher, cmd_arg: Annotated[Message, CommandArg()]):
    plugin_name = cmd_arg.extract_plain_text().strip()

    if not plugin_name:
        await matcher.finish(get_all_plugins_desc())
    else:
        is_superuser = await SUPERUSER(bot=bot, event=event)
        await matcher.finish(get_plugin_desc(plugin_name=plugin_name, for_superuser=is_superuser))


@omega.command(
    'set-level', aliases={'SetOmegaLevel', 'set_omega_level'}, handlers=[handle_parse_args], permission=IS_ADMIN
).got('omega_arg_0', prompt='请输入需要设定的权限等级:')
async def handle_set_level(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        level_str: Annotated[str, ArgStr('omega_arg_0')]
) -> None:
    level_str = level_str.strip()
    if not level_str.isdigit():
        await interface.matcher.finish('异常参数, 权限等级应当为整数, 操作已取消')

    level = int(level_str)
    if level < 0 or level > MAX_PERMISSION_LEVEL:
        await interface.matcher.finish(f'异常参数, 可设定的权限等级范围为 0~{MAX_PERMISSION_LEVEL}, 操作已取消')

    try:
        await interface.entity.set_permission_level(level)
        await interface.entity.commit_session()

        logger.success(f'Omega 设置权限等级{level!r}成功, Entity: {interface.entity}')
        await interface.matcher.send(f'Omega 已将当前会话权限等级设置为: Level-{level!r}')
    except Exception as e:
        logger.error(f'Omega 设置权限等级失败, {e!r}')
        await interface.matcher.send('Omega 设置权限等级失败, 请联系管理员处理')


@omega.command('list-commands', aliases={'ListOmegaCommands', 'list_omega_commands'}).handle()
async def handle_list_commands(matcher: Matcher):
    await matcher.finish(f'当前可用的命令列表:\n{"-" * 16}\n{list_command_by_priority()}')


@omega.command('list-plugins', aliases={'ListOmegaPlugins', 'list_omega_plugins'}).handle()
async def handle_list_plugins(matcher: Matcher, plugin_dal: Annotated[PluginDAL, Depends(PluginDAL.dal_dependence)]):
    def _desc(plugin_name: str) -> str:
        """根据 plugin name 获取插件自定义名称"""
        plugin = get_plugin(plugin_id=plugin_name)
        if (plugin is None) or (plugin.metadata is None):
            return plugin_name

        return f'{plugin_name}({plugin.metadata.name})'

    # 只显示有 matcher 以及有 metadata 的插件信息
    plugin_list = [
        plugin.name
        for plugin in get_loaded_plugins()
        if (len(plugin.matcher) > 0) and (plugin.metadata is not None)
    ]

    try:
        enabled_result = await plugin_dal.query_by_enable_status(enabled=1)
        disabled_result = await plugin_dal.query_by_enable_status(enabled=0)
    except Exception as e:
        logger.error(f'Omega 获取启用/禁用插件列表失败, {e!r}')
        await matcher.finish('获取插件列表失败, 请稍后再试或联系管理员处理')

    enabled_plugins = '\n'.join(_desc(x.plugin_name) for x in enabled_result if x.plugin_name in plugin_list)
    enabled_plugins = '无' if not enabled_plugins else enabled_plugins
    disabled_plugins = '\n'.join(_desc(x.plugin_name) for x in disabled_result if x.plugin_name in plugin_list)
    disabled_plugins = '无' if not disabled_plugins else disabled_plugins

    await matcher.send(f'已启用的插件:\n{"-" * 16}\n{enabled_plugins}\n\n\n已禁用的插件:\n{"-" * 16}\n{disabled_plugins}')


@omega.command(
    'enable-plugin', aliases={'EnableOmegaPlugin', 'enable_omega_plugin'}, handlers=[handle_parse_args]
).got('omega_arg_0', prompt='请输入需要启用的插件名称:')
async def handle_enable_plugin(
        matcher: Matcher,
        plugin_dal: Annotated[PluginDAL, Depends(PluginDAL.dal_dependence)],
        plugin_name: Annotated[str, ArgStr('omega_arg_0')]
) -> None:
    plugin_name = plugin_name.strip()
    if plugin_name not in (x.name for x in get_loaded_plugins()):
        await matcher.finish(f'未找到插件{plugin_name!r}, 操作已取消')

    if (imported_plugin := get_plugin(plugin_name)) is None:
        await matcher.finish(f'插件{plugin_name!r}未加载, 操作已取消')

    try:
        plugin = await plugin_dal.query_unique(plugin_name=plugin_name, module_name=imported_plugin.module_name)
        await plugin_dal.update(id_=plugin.id, enabled=1, info='Enabled by OPM')
        await plugin_dal.commit_session()

        logger.success(f'Omega 启用插件{plugin_name!r}成功')
        await matcher.send(f'Omega 启用插件{plugin_name!r}成功')
    except Exception as e:
        logger.error(f'Omega 启用插件{plugin_name!r}失败, {e!r}')
        await matcher.send(f'Omega 启用插件{plugin_name!r}失败, 请稍后再试或联系管理员处理')


@omega.command(
    'disable-plugin', aliases={'DisableOmegaPlugin', 'disable_omega_plugin'}, handlers=[handle_parse_args]
).got('omega_arg_0', prompt='请输入需要禁用的插件名称:')
async def handle_disable_plugin(
        matcher: Matcher,
        plugin_dal: Annotated[PluginDAL, Depends(PluginDAL.dal_dependence)],
        plugin_name: Annotated[str, ArgStr('omega_arg_0')]
) -> None:
    plugin_name = plugin_name.strip()
    if plugin_name not in (x.name for x in get_loaded_plugins()):
        await matcher.finish(f'未找到插件{plugin_name!r}, 操作已取消')

    if (imported_plugin := get_plugin(plugin_name)) is None:
        await matcher.finish(f'插件{plugin_name!r}未加载, 操作已取消')

    try:
        plugin = await plugin_dal.query_unique(plugin_name=plugin_name, module_name=imported_plugin.module_name)
        await plugin_dal.update(id_=plugin.id, enabled=0, info='Disabled by OPM')
        await plugin_dal.commit_session()

        logger.success(f'Omega 禁用插件{plugin_name!r}成功')
        await matcher.send(f'Omega 禁用插件{plugin_name!r}成功')
    except Exception as e:
        logger.error(f'Omega 禁用插件{plugin_name!r}失败, {e!r}')
        await matcher.send(f'Omega 禁用插件{plugin_name!r}失败, 请稍后再试或联系管理员处理')


@omega.command(
    'show-plugin-nodes', aliases={'ShowOmegaPluginNodes', 'show_omega_plugin_nodes'}, handlers=[handle_parse_args]
).got('omega_arg_0', prompt='请输入查询的插件名称:')
async def handle_show_plugin_nodes(matcher: Matcher, plugin_name: Annotated[str, ArgStr('omega_arg_0')]):
    plugin_name = plugin_name.strip()
    plugin_auth_nodes = get_plugin_auth_node(plugin_name=plugin_name)

    if not plugin_auth_nodes:
        await matcher.finish(f'插件{plugin_name!r}不存在, 或该插件无可配置权限节点')

    nodes_text = '\n'.join(plugin_auth_nodes)
    await matcher.finish(f'插件{plugin_name!r}可配置权限节点有:\n\n{nodes_text}')


allow_plugin_node = omega.command(
    'allow-plugin-node', aliases={'AllowOmegaPluginNode', 'allow_omega_plugin_node'}, handlers=[handle_parse_args]
)


@allow_plugin_node.got('omega_arg_0', prompt='请输入需要配置的插件名称:')
@allow_plugin_node.got('omega_arg_1', prompt='请输入需要配置的权限节点:')
async def handle_allow_plugin_node(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        plugin_name: Annotated[str, ArgStr('omega_arg_0')],
        auth_node: Annotated[str, ArgStr('omega_arg_1')]
) -> None:
    await handle_config_plugin_node(interface=interface, plugin_name=plugin_name, auth_node=auth_node, available=1)


deny_plugin_node = omega.command(
    'deny-plugin-node', aliases={'DenyOmegaPluginNode', 'deny_omega_plugin_node'}, handlers=[handle_parse_args]
)


@deny_plugin_node.got('omega_arg_0', prompt='请输入需要配置的插件名称:')
@deny_plugin_node.got('omega_arg_1', prompt='请输入需要配置的权限节点:')
async def handle_deny_plugin_node(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        plugin_name: Annotated[str, ArgStr('omega_arg_0')],
        auth_node: Annotated[str, ArgStr('omega_arg_1')]
) -> None:
    await handle_config_plugin_node(interface=interface, plugin_name=plugin_name, auth_node=auth_node, available=0)


async def handle_config_plugin_node(
        interface: OmMI,
        plugin_name: str,
        auth_node: str,
        available: int
) -> None:
    plugin_name = plugin_name.strip()
    auth_node = auth_node.strip()
    plugin_auth_nodes = get_plugin_auth_node(plugin_name=plugin_name)

    if not plugin_auth_nodes:
        await interface.matcher.finish(f'插件{plugin_name!r}不存在, 或该插件无可配置权限节点')

    if auth_node not in plugin_auth_nodes:
        await interface.matcher.finish(f'权限节点{auth_node!r}不是插件{plugin_name!r}的可配置权限节点, 操作已取消')

    plugin = get_plugin(plugin_id=plugin_name)
    if plugin is None:
        await interface.matcher.finish(f'插件{plugin_name!r}不存在')
    module = plugin.module_name

    try:
        await interface.entity.set_auth_setting(module=module, plugin=plugin_name, node=auth_node, available=available)
        await interface.entity.commit_session()

        logger.success(f'Omega 配置插件{plugin_name!r}权限节点{auth_node!r} -> {available!r}成功')
        await interface.matcher.send(f'Omega 配置插件{plugin_name!r}权限节点{auth_node!r} -> {available!r}成功')
    except Exception as e:
        logger.error(f'Omega 配置插件{plugin_name!r}权限节点{auth_node!r} -> {available!r}失败, {e!r}')
        await interface.matcher.send(
            f'Omega 配置插件{plugin_name!r}权限节点{auth_node!r}失败, 请稍后再试或联系管理员处理')


@omega.command('list-configured-auth', aliases={'ListOmegaConfiguredAuth', 'list_omega_configured_auth'}).handle()
async def handle_list_configured_auth(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    try:
        auth_settings = await interface.entity.query_all_auth_setting()
        auth_text = '\n'.join(f'{x.available} | {x.plugin}:{x.node}' for x in auth_settings)
        await interface.matcher.send(f'Omega 已配置的权限节点有:\n\n{auth_text}')
    except Exception as e:
        logger.error(f'查询 Omega 已配置权限节点失败, {e!r}')
        await interface.matcher.send('查询 Omega 已配置权限节点失败, 请稍后再试或联系管理员处理')


@omega.command(
    'set-limiting', aliases={'SetOmegaLimiting', 'set_omega_limiting'}, handlers=[handle_parse_args]
).got('omega_arg_0', prompt='请输入限制时间(秒):')
async def handle_set_limiting(
        interface: Annotated[OmMI, Depends(OmMI.depend())],
        time_str: Annotated[str, ArgStr('omega_arg_0')]
) -> None:
    time_str = time_str.strip()
    if not time_str.isdigit():
        await interface.matcher.finish('异常参数, 时间应当为整数, 操作已取消')

    time = int(time_str)

    try:
        await interface.entity.set_global_cooldown(expired_time=timedelta(seconds=time))
        await interface.entity.commit_session()

        logger.success(f'Omega 设置流控限制{time!r}秒, Entity: {interface.entity}')
        await interface.matcher.send(f'Omega 已限制当前会话使用{time!r}秒')
    except Exception as e:
        logger.error(f'Omega 设置流控限制失败, {e!r}')
        await interface.matcher.send('Omega 设置流控限制失败, 请联系管理员处理')


__all__ = []
