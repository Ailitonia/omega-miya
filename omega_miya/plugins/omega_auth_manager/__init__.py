"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : omega_auth_manager.py
@Project        : nonebot2_miya
@Description    : Omega 授权管理插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.log import logger
from nonebot.plugin import get_plugin, get_loaded_plugins, on_command, PluginMetadata
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.params import CommandArg, ArgStr

from omega_miya.result import BoolResult
from omega_miya.params import state_plain_text
from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.service.gocqhttp_guild_patch import GUILD_SUPERUSER
from omega_miya.service.omega_processor_tools import init_processor_state, parse_processor_state
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather
from omega_miya.utils.text_utils import AdvanceTextUtils
from omega_miya.database.helper import EventEntityHelper
from omega_miya.database.internal.consts import SKIP_COOLDOWN_PERMISSION_NODE
from omega_miya.database.internal.entity import (
    BaseInternalEntity, InternalBotGroup, InternalBotUser, InternalGuildChannel
)


__plugin_meta__ = PluginMetadata(
    name="授权管理",
    description="【OmegaAuth 授权管理插件】\n"
                "插件特殊权限授权管理\n"
                "仅限管理员使用",
    usage="/OmegaAuth [授权操作] [授权对象ID] [插件名称] [权限节点]\n"
          "/OmegaAuth [allow|deny] [插件名称] [权限节点]\n"
          "/OmegaAuth [list]\n\n"
          "可用授权操作:\n"
          "allow: 允许会话所在群组/频道/用户\n"
          "deny: 禁止会话所在群组/频道/用户\n"
          "list: 列出会话所在群组/频道/用户已配置的权限节点\n"
          "custom_allow: 允许指定群组/频道/用户\n"
          "custom_deny: 禁止指定群组/频道/用户",
    extra={"author": "Ailitonia"},
)


# 注册事件响应器
auth = on_command(
    'OmegaAuth',
    rule=to_me(),
    state=init_processor_state(name='OmegaAuth', enable_processor=False),
    aliases={'oauth'},
    permission=SUPERUSER | GUILD_SUPERUSER,
    priority=10,
    block=True
)


@auth.handle()
async def handle_parse_operating(state: T_State, cmd_arg: Message = CommandArg()):
    """首次运行时解析命令参数"""
    args = cmd_arg.extract_plain_text().strip().split(maxsplit=3)
    match len(args):
        case 1:
            state.update({'operating': args[0].lower()})
        case 2:
            state.update({'operating': args[0].lower(), 'related_entity_id': args[1]})
        case 3:
            state.update({'operating': args[0].lower(), 'plugin_name': args[1], 'auth_node': args[2]})
        case 4:
            state.update({'operating': args[0].lower(), 'related_entity_id': args[1],
                          'plugin_name': args[2], 'auth_node': args[3]})


@auth.got('operating', prompt='请选择要执行的授权操作:\n\nallow\ndeny\nlist\ncustom_allow\ncustom_deny')
async def handle_operating(bot: Bot, event: MessageEvent, state: T_State, operating: str = ArgStr('operating')):
    """处理需要执行不同的授权操作"""
    operating = operating.strip().lower()
    match operating:
        case 'allow' | 'deny':
            related_entity_id = await _get_event_related_entity_id(bot=bot, event=event)
            state.update({'related_entity_id': related_entity_id})
        case 'custom_allow' | 'custom_deny':
            pass
        case 'list':
            await auth.finish(await _get_event_entity_auth_info(bot=bot, event=event))
        case _:
            await auth.reject(f'{operating}不可用, 请在以下操作中选择: \n\nallow\ndeny\nlist\ncustom_allow\ncustom_deny')
    state.update({'operating': operating})


@auth.handle()
async def handle_available_entity(matcher: Matcher, bot: Bot, state: T_State):
    """检查可用的授权对象"""
    if not state.get('related_entity_id', None):
        entity_result = await _get_bot_available_entity(bot=bot)
        text = '群组:\n'
        text += '\n'.join(f'ID: {x.relation_model.id} | {x.entity_model.entity_name}'
                          for x in entity_result if x.relation_model.relation_type == 'bot_group')
        text += '\n\n子频道\n'
        text += '\n'.join(f'ID: {x.relation_model.id} | {x.parent_model.entity_name} | {x.entity_model.entity_name}'
                          for x in entity_result if x.relation_model.relation_type == 'guild_channel')
        text += '\n\n好友\n'
        text += '\n'.join(f'ID: {x.relation_model.id} | {x.entity_model.entity_name}'
                          for x in entity_result if x.relation_model.relation_type == 'bot_user')
        tips_image = await AdvanceTextUtils.parse_from_str(text=text).convert_image(image_size=(1024, 16384),
                                                                                    background=(255, 255, 255, 255))

        await matcher.send(MessageSegment.text('当前可配置权限的对象:\n') + MessageSegment.image(tips_image.file_uri))


@auth.got('related_entity_id', prompt='请输入授权对象ID:')
async def handle_related_entity_id(
        state: T_State,
        matcher: Matcher,
        related_entity_id: str = ArgStr('related_entity_id')
):
    if not related_entity_id.isdigit():
        await matcher.reject('授权对象ID应当为纯数字, 请重新输入:')
    related_entity_id = int(related_entity_id)
    await _verify_relation_entity_exists(matcher=matcher, related_entity_id=related_entity_id)
    state.update({'related_entity_id': related_entity_id})


@auth.handle()
async def handle_plugin_name_tips(matcher: Matcher, state: T_State):
    if not state.get('plugin_name', None):
        all_plugins = [p.name for p in get_loaded_plugins() if p.metadata is not None]
        all_plugins.sort()
        all_plugin_name = '\n'.join(all_plugins)
        info_msg = f'现在已安装的插件有:\n\n{all_plugin_name}'
        await matcher.send(info_msg)


@auth.got('plugin_name', prompt='请输入配置权限节点的插件名称:')
async def handle_plugin_name(state: T_State, plugin_name: str = ArgStr('plugin_name')):
    plugin_name = plugin_name.strip()
    plugin_auth_node = _get_plugin_auth_node(plugin_name=plugin_name)
    if not plugin_auth_node:
        await auth.finish(f'插件: {plugin_name}不存在或该插件无可配置权限节点')
    state.update({'plugin_name': plugin_name})


@auth.handle()
async def handle_auth_node_tips(matcher: Matcher, state: T_State, plugin_name: str = state_plain_text('plugin_name')):
    if not state.get('auth_node', None):
        plugin_auth_node = _get_plugin_auth_node(plugin_name=plugin_name)
        plugin_auth_node_msg = '\n'.join(plugin_auth_node)
        await matcher.send(f'插件: {plugin_name}可配置的权限节点有:\n\n{plugin_auth_node_msg}')


@auth.got('auth_node', prompt='请输入想要配置的权限节点名称:')
async def handle_auth_node(
        matcher: Matcher,
        operating: str = state_plain_text('operating'),
        related_entity_id: str = state_plain_text('related_entity_id'),
        plugin_name: str = state_plain_text('plugin_name'),
        auth_node: str = ArgStr('auth_node')
):
    related_entity_id = int(related_entity_id)

    auth_node = auth_node.strip()
    if auth_node not in _get_plugin_auth_node(plugin_name=plugin_name):
        await auth.reject(f'权限节点: {auth_node}不是插件: {plugin_name}的可配置权限节点, 请重新输入:')

    plugin = get_plugin(name=plugin_name)
    module_name = plugin.module_name

    match operating:
        case 'allow' | 'custom_allow':
            available = 1
        case _:
            available = 0

    result = await _set_entity_auth_node(
        related_entity_id=related_entity_id,
        module=module_name,
        plugin=plugin_name,
        node=auth_node,
        available=available
    )

    if isinstance(result, Exception):
        logger.error(f'为对象(ID: {related_entity_id})配置权限节点 {plugin}-{auth_node} 失败, {result}')
        info_msg = f'配置权限节点失败, 详情请查看日志'
    elif result.error:
        logger.error(result.info)
        info_msg = result.info
    else:
        logger.success(result.info)
        info_msg = result.info
    await matcher.finish(info_msg)


async def _get_event_related_entity_id(bot: Bot, event: MessageEvent) -> int:
    """根据 event 中获取授权操作对象 id"""
    relation = await EventEntityHelper(bot=bot, event=event).get_event_entity().get_relation_model()
    return relation.id


async def _get_event_entity_auth_info(bot: Bot, event: MessageEvent) -> str:
    """根据 event 中获取授权操作对象已有权限清单"""
    entity = EventEntityHelper(bot=bot, event=event).get_event_entity()
    auth_list = await run_async_catching_exception(entity.query_all_auth_setting)()
    if isinstance(auth_list, Exception):
        auth_msg = f'权限节点查询失败, 没有配置权限或未进行初始化'
    else:
        auth_info = '\n'.join(f'[{x.plugin}]{x.node}: {x.available}' for x in auth_list)
        auth_msg = f'已配置权限节点:\n\n{auth_info}'
    return auth_msg


async def _get_bot_available_entity(bot: Bot) -> list[BaseInternalEntity]:
    """获取 Bot 所有可配置权限的 Entity"""
    gocq_bot = GoCqhttpBot(bot=bot)
    entity_list = []

    groups_result = await gocq_bot.get_group_list()
    entity_list.extend(InternalBotGroup(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=x.group_id)
                       for x in groups_result)

    users_result = await gocq_bot.get_friend_list()
    entity_list.extend(InternalBotUser(bot_id=bot.self_id, parent_id=bot.self_id, entity_id=x.user_id)
                       for x in users_result)

    guild_result = await gocq_bot.get_guild_list()
    for guild in guild_result:
        channel_result = await gocq_bot.get_guild_channel_list(guild_id=guild.guild_id)
        entity_list.extend(InternalGuildChannel(bot_id=bot.self_id, parent_id=x.owner_guild_id, entity_id=x.channel_id)
                           for x in channel_result)

    tasks = [x.get_relation_model() for x in entity_list]
    await semaphore_gather(tasks=tasks, semaphore_num=10)
    return entity_list


async def _verify_relation_entity_exists(matcher: Matcher, related_entity_id: int) -> None:
    """验证授权对象可用性并返回提示信息"""
    entity = await run_async_catching_exception(BaseInternalEntity.init_from_index_id)(id_=related_entity_id)

    if isinstance(entity, Exception):
        info_msg = f'对象(ID: {related_entity_id})不存在, 请初始化该对象信息后再进行配置'
        await matcher.finish(info_msg)


def _get_plugin_auth_node(plugin_name: str) -> list[str]:
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


@run_async_catching_exception
async def _set_entity_auth_node(
        related_entity_id: int,
        module: str,
        plugin: str,
        node: str,
        available: int
) -> BoolResult:
    """配置权限节点"""
    entity = await BaseInternalEntity.init_from_index_id(id_=related_entity_id)
    result = await entity.set_auth_setting(module=module, plugin=plugin, node=node, available=available)
    if result.success:
        info = f'为对象(ID: {related_entity_id} | {entity.entity_model.entity_name}) 配置权限节点 {plugin}-{node} 成功'
        return BoolResult(error=False, info=info, result=True)
    else:
        info = f'为对象(ID: {related_entity_id} | {entity.entity_model.entity_name}) 配置权限节点 {plugin}-{node} 失败'
        return BoolResult(error=True, info=info, result=False)
