"""
@Author         : Ailitonia
@Date           : 2023/7/3 3:02
@FileName       : command
@Project        : nonebot2_miya
@Description    : Omega 核心管理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from arclet.alconna import Alconna, Args, CommandMeta, Subcommand
from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.plugin import get_loaded_plugins, get_plugin
from nonebot_plugin_alconna import AlconnaMatcher, Match, on_alconna
from sqlalchemy.exc import NoResultFound

from src.params.depends import EVENT_M_IFACE, PLUGIN_DAL
from src.params.handler import ensure_arg_text
from src.params.permission import check_event_is_admin, check_event_is_superuser
from src.service import OmegaMatcherInterface, enable_processor_state
from .helpers import get_all_plugins_desc, get_plugin_auth_node, get_plugin_desc, list_command_by_priority
from .status import get_status

_DEFAULT_PERMISSION_LEVEL: int = 30
"""初始化时默认的权限等级"""
_MAX_PERMISSION_LEVEL: int = 100
"""通过命令可以设置的最高权限等级"""
_HANDLER_PROMPT_TIMEOUT: float = 60
"""交互流程等待用户响应超时时间"""

omega_cmd = on_alconna(
    Alconna(
        'omega',
        Subcommand(
            'start',
            alias=['Start', 'Enable', 'enable'],
            help_text='启用/初始化 Omega',
        ),
        Subcommand(
            'disable',
            alias=['Disable'],
            help_text='禁用 Omega',
        ),
        Subcommand(
            'status',
            alias=['Status'],
            help_text='查看 Omega 运行状态',
        ),
        Subcommand(
            'help',
            Args['plugin_name?#插件名称', str],
            alias=['Help', '帮助'],
            help_text='查看插件帮助信息',
        ),
        Subcommand(
            'set-level',
            Args['level?#权限等级', str],
            alias=['SetLevel', 'set_level'],
            help_text='设置当前会话权限等级',
        ),
        Subcommand(
            'list-commands',
            alias=['ListCommands', 'list_commands'],
            help_text='列出当前可用的命令',
        ),
        Subcommand(
            'list-plugins',
            alias=['ListPlugins', 'list_plugins'],
            help_text='列出插件启用状态',
        ),
        Subcommand(
            'enable-plugin',
            Args['plugin_name?#插件名称', str],
            alias=['EnablePlugin', 'enable_plugin'],
            help_text='启用插件',
        ),
        Subcommand(
            'disable-plugin',
            Args['plugin_name?#插件名称', str],
            alias=['DisablePlugin', 'disable_plugin'],
            help_text='禁用插件',
        ),
        Subcommand(
            'show-plugin-nodes',
            Args['plugin_name?#插件名称', str],
            alias=['ShowPluginNodes', 'show_plugin_nodes'],
            help_text='列出插件可配置权限节点',
        ),
        Subcommand(
            'allow-plugin-node',
            Args['plugin_name?#插件名称', str]['auth_node?#权限节点', str],
            alias=['AllowPluginNode', 'allow_plugin_node'],
            help_text='为当前会话启用插件权限节点',
        ),
        Subcommand(
            'deny-plugin-node',
            Args['plugin_name?#插件名称', str]['auth_node?#权限节点', str],
            alias=['DenyPluginNode', 'deny_plugin_node'],
            help_text='为当前会话禁用插件权限节点',
        ),
        Subcommand(
            'list-configured-auth',
            alias=['ListConfiguredAuth', 'list_configured_auth'],
            help_text='列出当前会话已配置的权限节点',
        ),
        meta=CommandMeta(
            description='Omega 机器人核心管理',
            usage='/omega <子命令> [参数]',
            example='/omega start',
            compact=True,
        ),
    ),
    use_cmd_start=True,
    aliases={'Omega'},
    priority=20,
    block=True,
    # 本插件即为权限管理插件, 不启用 processor 处理流程
    default_state=enable_processor_state(name='OmegaCoreManager', enable_processor=False),
)


@omega_cmd.assign('$main')
async def handle_hello(interface: EVENT_M_IFACE) -> None:
    """Omega 问候"""
    await interface.finish_reply('你好呀~\n我是Omega Miya~\n请问您今天要来点喵娘吗?')


@omega_cmd.assign('start', additional=check_event_is_admin)
async def handle_start(interface: EVENT_M_IFACE) -> None:
    """启用/初始化 Omega"""
    try:
        async with interface.create_current_entity_session() as entity:
            await entity.init_self()
            await entity.enable_global_permission()
            await entity.set_permission_level(_DEFAULT_PERMISSION_LEVEL)
    except Exception as e:
        logger.error(f'Omega 启用/初始化失败, {interface}, {e!r}')
        await interface.finish_reply('Omega 启用/初始化失败, 请联系管理员处理')

    logger.success(f'Omega 启用成功, {interface}')
    await interface.finish_reply('Omega 启用/初始化成功')


@omega_cmd.assign('disable', additional=check_event_is_admin)
async def handle_disable(interface: EVENT_M_IFACE) -> None:
    """禁用 Omega"""
    try:
        async with interface.create_current_entity_session() as entity:
            await entity.init_self()
            await entity.disable_global_permission()
            await entity.set_permission_level(0)
    except Exception as e:
        logger.error(f'Omega 禁用失败, {interface}, {e!r}')
        await interface.finish_reply('Omega 禁用失败, 请联系管理员处理')

    logger.success(f'Omega 禁用成功, {interface}')
    await interface.finish_reply('Omega 禁用成功')


@omega_cmd.assign('status', additional=check_event_is_admin)
async def handle_status(interface: EVENT_M_IFACE) -> None:
    """查看 Omega 运行状态"""
    try:
        async with interface.create_current_entity_session() as entity:
            await entity.query_bot_self()
            if await entity.check_global_permission():
                global_permission_text = '已启用(Enabled)'
            else:
                global_permission_text = '已禁用(Disabled)'
            try:
                permission_level = await entity.query_permission_level()
                permission_level_text = f'Level-{permission_level.available}'
            except NoResultFound:
                permission_level_text = '未设置'
    except NoResultFound:
        await interface.finish_reply('Omega 未初始化, 请尝试使用 "/omega start" 命令初始化, 或联系管理员处理')
    except Exception as e:
        logger.error(f'获取 Omega 状态失败, {e!r}')
        await interface.finish_reply('获取 Omega 状态失败, 请尝试使用 "/omega start" 命令初始化, 或联系管理员处理')

    try:
        status = await get_status()
    except Exception as e:
        logger.error(f'获取 Omega 运行状态失败, {e!r}')
        await interface.finish_reply('获取 Omega 运行状态失败, 请稍后再试或联系管理员处理')

    await interface.send_reply(
        f'Omega 功能开关: {global_permission_text}\nOmega 权限等级: {permission_level_text}'
        f'\n\nOmega 运行状态:\n{"-" * 16}\n{status}'
    )


@omega_cmd.assign('help')
async def handle_help(
        bot: BaseBot,
        event: BaseEvent,
        interface: EVENT_M_IFACE,
        plugin_name: Match[str],
) -> None:
    """查看插件帮助信息"""
    if plugin_name.available and (target_plugin_name := plugin_name.result.strip()):
        is_superuser = await SUPERUSER(bot=bot, event=event)
        await interface.finish_reply(get_plugin_desc(plugin_name=target_plugin_name, for_superuser=is_superuser))
    else:
        await interface.finish_reply(get_all_plugins_desc())


@omega_cmd.assign('set-level', additional=check_event_is_admin)
async def handle_set_level(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        level: Match[str],
) -> None:
    """设置当前会话权限等级"""
    level_str = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=level,
        prompt_text='请输入需要设定的权限等级:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    if not level_str.isdecimal():
        await interface.finish_reply('异常参数, 权限等级应当为整数, 操作已取消')

    try:
        target_level = int(level_str)
    except ValueError:
        # isdecimal 通过的字符串仍可能因超过 int 转换位数上限而抛出 ValueError
        await interface.finish_reply('异常参数, 权限等级应当为整数, 操作已取消')

    if target_level < 0 or target_level > _MAX_PERMISSION_LEVEL:
        await interface.finish_reply(f'异常参数, 可设定的权限等级范围为 0~{_MAX_PERMISSION_LEVEL}, 操作已取消')

    try:
        async with interface.create_current_entity_session() as entity:
            await entity.set_permission_level(target_level)
    except Exception as e:
        logger.error(f'Omega 设置权限等级失败, {interface}, {e!r}')
        await interface.finish_reply('Omega 设置权限等级失败, 请联系管理员处理')

    logger.success(f'Omega 设置权限等级{target_level!r}成功, {interface}')
    await interface.finish_reply(f'Omega 已将当前会话权限等级设置为: Level-{target_level!r}')


@omega_cmd.assign('list-commands', additional=check_event_is_superuser)
async def handle_list_commands(interface: EVENT_M_IFACE) -> None:
    """列出当前可用的命令"""
    await interface.finish_reply(f'当前可用的命令列表:\n{"-" * 16}\n{list_command_by_priority()}')


@omega_cmd.assign('list-plugins', additional=check_event_is_superuser)
async def handle_list_plugins(interface: EVENT_M_IFACE, plugin_dal: PLUGIN_DAL) -> None:
    """列出插件启用状态"""

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
        await interface.finish_reply('获取插件列表失败, 请稍后再试或联系管理员处理')

    enabled_plugins = '\n'.join(_desc(x.plugin_name) for x in enabled_result if x.plugin_name in plugin_list)
    enabled_plugins = '无' if not enabled_plugins else enabled_plugins
    disabled_plugins = '\n'.join(_desc(x.plugin_name) for x in disabled_result if x.plugin_name in plugin_list)
    disabled_plugins = '无' if not disabled_plugins else disabled_plugins

    await interface.finish_reply(
        f'已启用的插件:\n{"-" * 16}\n{enabled_plugins}\n\n\n已禁用的插件:\n{"-" * 16}\n{disabled_plugins}'
    )


async def _handle_switch_plugin_enabled(
        interface: OmegaMatcherInterface,
        plugin_dal: PLUGIN_DAL,
        *,
        plugin_name: str,
        enabled: int,
) -> None:
    """启用/禁用插件公共流程"""
    action_text = '启用' if enabled else '禁用'

    if plugin_name not in (x.name for x in get_loaded_plugins()):
        await interface.finish_reply(f'未找到插件{plugin_name!r}, 操作已取消')
    if (imported_plugin := get_plugin(plugin_id=plugin_name)) is None:
        await interface.finish_reply(f'插件{plugin_name!r}未加载, 操作已取消')

    try:
        await plugin_dal.add_update_exist(
            plugin_name=plugin_name,
            module_name=imported_plugin.module_name,
            enabled=enabled,
            info=f'{"Enabled" if enabled else "Disabled"} by OPM',
        )
        # 显式提交以保证写操作及时落库, 不依赖事件结束时依赖清理路径的自动提交
        await plugin_dal.commit_session()
    except Exception as e:
        logger.error(f'Omega {action_text}插件{plugin_name!r}失败, {e!r}')
        await interface.finish_reply(f'Omega {action_text}插件{plugin_name!r}失败, 请稍后再试或联系管理员处理')

    logger.success(f'Omega {action_text}插件{plugin_name!r}成功')
    await interface.finish_reply(f'Omega {action_text}插件{plugin_name!r}成功')


@omega_cmd.assign('enable-plugin', additional=check_event_is_superuser)
async def handle_enable_plugin(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        plugin_dal: PLUGIN_DAL,
        plugin_name: Match[str],
) -> None:
    """启用插件"""
    target_plugin_name = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=plugin_name,
        prompt_text='请输入需要启用的插件名称:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    await _handle_switch_plugin_enabled(interface, plugin_dal, plugin_name=target_plugin_name, enabled=1)


@omega_cmd.assign('disable-plugin', additional=check_event_is_superuser)
async def handle_disable_plugin(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        plugin_dal: PLUGIN_DAL,
        plugin_name: Match[str],
) -> None:
    """禁用插件"""
    target_plugin_name = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=plugin_name,
        prompt_text='请输入需要禁用的插件名称:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    await _handle_switch_plugin_enabled(interface, plugin_dal, plugin_name=target_plugin_name, enabled=0)


@omega_cmd.assign('show-plugin-nodes', additional=check_event_is_superuser)
async def handle_show_plugin_nodes(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        plugin_name: Match[str],
) -> None:
    """列出插件可配置权限节点"""
    target_plugin_name = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=plugin_name,
        prompt_text='请输入查询的插件名称:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    plugin_auth_nodes = get_plugin_auth_node(plugin_name=target_plugin_name)

    if not plugin_auth_nodes:
        await interface.finish_reply(f'插件{target_plugin_name!r}不存在, 或该插件无可配置权限节点')

    nodes_text = '\n'.join(plugin_auth_nodes)
    await interface.finish_reply(f'插件{target_plugin_name!r}可配置权限节点有:\n\n{nodes_text}')


async def _handle_config_plugin_node(
        interface: OmegaMatcherInterface,
        plugin_name: str,
        auth_node: str,
        available: int,
) -> None:
    """配置插件权限节点公共流程"""
    plugin_auth_nodes = get_plugin_auth_node(plugin_name=plugin_name)

    if not plugin_auth_nodes:
        await interface.finish_reply(f'插件{plugin_name!r}不存在, 或该插件无可配置权限节点')

    if auth_node not in plugin_auth_nodes:
        await interface.finish_reply(f'权限节点{auth_node!r}不是插件{plugin_name!r}的可配置权限节点, 操作已取消')

    plugin = get_plugin(plugin_id=plugin_name)
    if plugin is None:
        await interface.finish_reply(f'插件{plugin_name!r}存在但无法获取插件对象')
    module = plugin.module_name

    try:
        async with interface.create_current_entity_session() as entity:
            await entity.set_auth_setting(
                module=module,
                plugin=plugin_name,
                node=auth_node,
                available=available,
                value={},
            )
    except Exception as e:
        logger.error(f'Omega 配置插件{plugin_name!r}权限节点{auth_node!r} -> {available!r}失败, {e!r}')
        await interface.finish_reply(
            f'Omega 配置插件{plugin_name!r}权限节点{auth_node!r}失败, 请稍后再试或联系管理员处理'
        )

    logger.success(f'Omega 配置插件{plugin_name!r}权限节点{auth_node!r} -> {available!r}成功')
    await interface.finish_reply(f'Omega 配置插件{plugin_name!r}权限节点{auth_node!r} -> {available!r}成功')


@omega_cmd.assign('allow-plugin-node', additional=check_event_is_superuser)
async def handle_allow_plugin_node(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        plugin_name: Match[str],
        auth_node: Match[str],
) -> None:
    """为当前会话启用插件权限节点"""
    target_plugin_name = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=plugin_name,
        prompt_text='请输入需要配置的插件名称:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    target_auth_node = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=auth_node,
        prompt_text='请输入需要配置的权限节点:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    await _handle_config_plugin_node(
        interface=interface,
        plugin_name=target_plugin_name,
        auth_node=target_auth_node,
        available=1,
    )


@omega_cmd.assign('deny-plugin-node', additional=check_event_is_superuser)
async def handle_deny_plugin_node(
        matcher: AlconnaMatcher,
        interface: EVENT_M_IFACE,
        plugin_name: Match[str],
        auth_node: Match[str],
) -> None:
    """为当前会话禁用插件权限节点"""
    target_plugin_name = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=plugin_name,
        prompt_text='请输入需要配置的插件名称:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    target_auth_node = await ensure_arg_text(
        matcher=matcher,
        interface=interface,
        arg=auth_node,
        prompt_text='请输入需要配置的权限节点:',
        timeout=_HANDLER_PROMPT_TIMEOUT,
    )
    await _handle_config_plugin_node(
        interface=interface,
        plugin_name=target_plugin_name,
        auth_node=target_auth_node,
        available=0,
    )


@omega_cmd.assign('list-configured-auth', additional=check_event_is_superuser)
async def handle_list_configured_auth(interface: EVENT_M_IFACE) -> None:
    """列出当前会话已配置的权限节点"""
    try:
        async with interface.create_current_entity_session() as entity:
            auth_settings = await entity.query_all_auth_setting()
    except Exception as e:
        logger.error(f'查询 Omega 已配置权限节点失败, {e!r}')
        await interface.finish_reply('查询 Omega 已配置权限节点失败, 请稍后再试或联系管理员处理')

    auth_text = '\n'.join(f'{x.available} | {x.plugin}:{x.node}' for x in auth_settings)
    await interface.finish_reply(f'Omega 已配置的权限节点有:\n\n{auth_text if auth_text else "无"}')


# 注册声明式自检, 启动时解析失败将输出 ERROR 日志
omega_cmd.test('omega')
omega_cmd.test('omega start')
omega_cmd.test('omega disable')
omega_cmd.test('omega status')
omega_cmd.test('omega help')
omega_cmd.test('omega help OmegaCoreManager')
omega_cmd.test('omega set-level 30')
omega_cmd.test('omega list-commands')
omega_cmd.test('omega list-plugins')
omega_cmd.test('omega enable-plugin omega_core_manager')
omega_cmd.test('omega disable-plugin omega_core_manager')
omega_cmd.test('omega show-plugin-nodes omega_core_manager')
omega_cmd.test('omega allow-plugin-node omega_core_manager OmegaCoreManager')
omega_cmd.test('omega deny-plugin-node omega_core_manager OmegaCoreManager')
omega_cmd.test('omega list-configured-auth')


__all__ = []
