from nonebot import on_command, get_plugin, get_loaded_plugins, logger
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import MessageEvent, GroupMessageEvent
from nonebot.params import CommandArg, ArgStr

from omega_miya.database import InternalBotUser, InternalBotGroup
from omega_miya.database.internal.consts import SKIP_COOLDOWN_PERMISSION_NODE
from omega_miya.service.omega_processor_tools import init_processor_state, parse_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception


# Custom plugin usage text
__plugin_custom_name__ = '授权管理'
__plugin_usage__ = r'''【OmegaAuth 授权管理插件】
插件特殊权限授权管理
仅限管理员使用

用法:
/OmegaAuth [授权操作] [授权类型] [授权对象] [插件名称] [权限节点]

可用授权操作:
allow: 允许会话所在群组/用户
deny: 禁止会话所在群组/用户
list: 列出会话所在群组/用户已配置的权限节点
custom_allow: 允许指定群组/用户
custom_deny: 禁止指定群组/用户'''


# 注册事件响应器
auth = on_command(
    'OmegaAuth',
    rule=to_me(),
    state=init_processor_state(name='OmegaAuth', enable_processor=False),
    aliases={'oauth'},
    permission=SUPERUSER,
    priority=10,
    block=True
)


@auth.handle()
async def handle_parse_operating(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    operating = cmd_arg.extract_plain_text().strip().lower()
    if operating:
        state.update({'operating': operating})


@auth.got('operating', prompt='请选择要执行的授权操作:\n\nallow\ndeny\nlist\ncustom_allow\ncustom_deny')
async def handle_operating(event: MessageEvent, state: T_State, operating: str = ArgStr('operating')):
    """处理需要执行不同的授权操作"""
    operating = operating.strip().lower()
    match operating:
        case 'allow':
            auth_type, entity_id = get_auth_type_entity_id(event=event)
            state.update({'auth_type': auth_type, 'entity_id': entity_id})
        case 'deny':
            auth_type, entity_id = get_auth_type_entity_id(event=event)
            state.update({'auth_type': auth_type, 'entity_id': entity_id})
        case 'custom_allow':
            pass
        case 'custom_deny':
            pass
        case 'list':
            await auth.finish(await get_entity_auth_info(event=event))
        case _:
            await auth.reject(f'{operating}不可用, 请在以下操作中选择: \n\nallow\ndeny\nlist\ncustom_allow\ncustom_deny')
    state.update({'operating': operating})


@auth.got('auth_type', prompt='请选择要执行的授权对象类型:\n\nuser\ngroup')
async def handle_auth_type(state: T_State, auth_type: str = ArgStr('auth_type')):
    """处理需要执行不同的授权对象类型"""
    auth_type = auth_type.strip().lower()
    match auth_type:
        case 'user' | 'group':
            state.update({'auth_type': auth_type})
        case _:
            await auth.reject(f'{auth_type}不可用, 请在以下类型中选择: \n\nuser\ngroup')


@auth.got('entity_id', prompt='请输入授权用户qq或授权群组群号:')
async def handle_entity_id(bot: Bot, state: T_State, matcher: Matcher, entity_id: str = ArgStr('entity_id')):
    entity_id = entity_id.strip().lower()
    auth_type = state.get('auth_type')
    await verify_entity_exists(matcher=matcher, auth_type=auth_type, bot_self_id=bot.self_id, entity_id=entity_id)
    state.update({'entity_id': entity_id})


@auth.got('plugin_name', prompt='请输入配置权限节点的插件名称:')
async def handle_plugin_name(state: T_State, plugin_name: str = ArgStr('plugin_name')):
    plugin_name = plugin_name.strip()
    plugin_auth_node = get_plugin_auth_node(plugin_name=plugin_name)
    if not plugin_auth_node:
        await auth.finish(f'插件: {plugin_name}不存在或该插件无可配置权限节点')
    else:
        plugin_auth_node_msg = '\n'.join(plugin_auth_node)
        await auth.send(f'插件: {plugin_name}可配置的权限节点有:\n\n{plugin_auth_node_msg}')
    state.update({'plugin_name': plugin_name})


@auth.got('auth_node', prompt='请输入想要配置的权限节点名称:')
async def handle_auth_node(bot: Bot, matcher: Matcher, state: T_State, auth_node: str = ArgStr('auth_node')):
    auth_node = auth_node.strip()
    plugin_name = state.get('plugin_name')
    if auth_node not in get_plugin_auth_node(plugin_name=plugin_name):
        await auth.reject(f'权限节点: {auth_node}不是插件: {plugin_name}的可配置权限节点, 请重新输入:')

    operating = state.get('operating')
    auth_type = state.get('auth_type')
    entity_id = state.get('entity_id')
    plugin_name = state.get('plugin_name')
    plugin = get_plugin(name=plugin_name)
    module_name = plugin.module_name

    match operating:
        case 'allow' | 'custom_allow':
            available = 1
        case _:
            available = 0

    await set_entity_auth_node(
        matcher=matcher,
        auth_type=auth_type,
        bot_self_id=bot.self_id,
        entity_id=entity_id,
        module=module_name,
        plugin=plugin_name,
        node=auth_node,
        available=available
    )


def get_auth_type_entity_id(event: MessageEvent) -> tuple[str, str]:
    """根据 event 中获取授权操作对象类型和 id"""
    if isinstance(event, GroupMessageEvent):
        result = 'group', str(event.group_id)
    else:
        result = 'user', str(event.user_id)
    return result


async def get_entity_auth_info(event: MessageEvent) -> str:
    """根据 event 中获取授权操作对象已有权限清单"""
    bot_self_id = str(event.self_id)
    if isinstance(event, GroupMessageEvent):
        entity = InternalBotGroup(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=str(event.group_id))
    else:
        entity = InternalBotUser(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=str(event.user_id))

    auth_list = await run_async_catching_exception(entity.query_all_auth_setting)()
    if isinstance(auth_list, Exception):
        auth_msg = f'权限节点查询失败, 没有配置权限或未进行初始化'
    else:
        auth_info = '\n'.join(f'[{x.plugin}]{x.node}: {x.available}' for x in auth_list)
        auth_msg = f'已配置权限节点:\n\n{auth_info}'
    return auth_msg


async def verify_entity_exists(matcher: Matcher, auth_type: str, bot_self_id: str, entity_id: str) -> None:
    """验证授权对象可用性并返回提示信息"""
    match auth_type:
        case 'user':
            user = InternalBotUser(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=entity_id)
            entity = await run_async_catching_exception(user.query)()
            entity_prefix = '用户'
        case 'group':
            group = InternalBotGroup(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=entity_id)
            entity = await run_async_catching_exception(group.query)()
            entity_prefix = '群组'
        case _:
            await matcher.finish(f'{auth_type}不可用, 交互异常, 当前操作已取消')
            return

    if isinstance(entity, Exception):
        info_msg = f'{entity_prefix}: {entity_id}不存在, 请初始化该{entity_prefix}信息后再进行配置'
        await matcher.finish(info_msg)
    else:
        all_plugins = [p.name for p in get_loaded_plugins()
                       if getattr(p.module, '__plugin_custom_name__', None) is not None]
        all_plugins.sort()
        all_plugin_name = '\n'.join(all_plugins)
        info_msg = f'即将对{entity_prefix}: {entity_id}执行操作, 现在已安装的插件有:\n\n{all_plugin_name}'
        await matcher.send(info_msg)


def get_plugin_auth_node(plugin_name: str) -> list[str]:
    """根据插件名获取可配置的权限节点名称清单"""
    plugin = get_plugin(name=plugin_name)
    if plugin is None:
        result = []
    else:
        result = [s.auth_node for s in (
            parse_processor_state(m._default_state) for m in plugin.matcher
        ) if s.auth_node is not None]

        # 如果有 extra_auth_node 也加入到可配置的权限节点中
        result.extend((extra_node for s in (
            parse_processor_state(m._default_state) for m in plugin.matcher
        ) if s.extra_auth_node for extra_node in s.extra_auth_node))

        # 如果有冷却配置就把跳过冷却的权限加入到可配置的权限节点中
        if any(s.cool_down for s in (parse_processor_state(m._default_state) for m in plugin.matcher)):
            result.append(SKIP_COOLDOWN_PERMISSION_NODE)
    result = list(set(result))
    result.sort()
    return result


async def set_entity_auth_node(
        matcher: Matcher,
        auth_type: str,
        bot_self_id: str,
        entity_id: str,
        module: str,
        plugin: str,
        node: str,
        available: int
) -> None:
    """配置权限节点"""
    match auth_type:
        case 'user':
            user = InternalBotUser(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=entity_id)
            result = await run_async_catching_exception(user.set_auth_setting)(
                module=module, plugin=plugin, node=node, available=available)
            entity_prefix = '用户'
        case 'group':
            group = InternalBotGroup(bot_id=bot_self_id, parent_id=bot_self_id, entity_id=entity_id)
            result = await run_async_catching_exception(group.set_auth_setting)(
                module=module, plugin=plugin, node=node, available=available)
            entity_prefix = '群组'
        case _:
            await matcher.finish(f'{auth_type}不可用, 交互异常, 当前操作已取消')
            return

    if isinstance(result, Exception):
        logger.error(f'为{entity_prefix}: {entity_id} 配置权限节点 {plugin}-{node} 失败: {result}')
        info_msg = f'为{entity_prefix}: {entity_id} 配置权限节点 {plugin}-{node} 失败, 详情请查看日志'
    else:
        logger.success(f'为{entity_prefix}: {entity_id} 配置权限节点 {plugin}-{node} 成功')
        info_msg = f'为{entity_prefix}: {entity_id} 配置权限节点 {plugin}-{node} 成功'
    await matcher.finish(info_msg)
