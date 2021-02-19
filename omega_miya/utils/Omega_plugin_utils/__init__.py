from nonebot.plugin import Export
from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event
from omega_miya.utils.Omega_Base import DBGroup, DBAuth


def init_export(plugin_export: Export, custom_name: str, usage: str, auth_node: list = None, **kwargs: str) -> Export:
    setattr(plugin_export, 'custom_name', custom_name)
    setattr(plugin_export, 'usage', usage)
    setattr(plugin_export, 'auth_node', auth_node)
    for key, value in kwargs.items():
        setattr(plugin_export, key, value)
    return plugin_export


# Plugin permission rule
# Only using for group
def has_notice_permission() -> Rule:
    async def _has_notice_permission(bot: Bot, event: Event, state: T_State) -> bool:
        detail_type = event.dict().get(f'{event.get_type()}_type')
        group_id = event.dict().get('group_id')
        # 检查当前消息类型
        if detail_type != 'group':
            return False
        else:
            if DBGroup(group_id=group_id).permission_notice().result == 1:
                return True
            else:
                return False
    return Rule(_has_notice_permission)


def has_command_permission() -> Rule:
    async def _has_command_permission(bot: Bot, event: Event, state: T_State) -> bool:
        detail_type = event.dict().get(f'{event.get_type()}_type')
        group_id = event.dict().get('group_id')
        # 检查当前消息类型
        if detail_type != 'group':
            return False
        else:
            if DBGroup(group_id=group_id).permission_command().result == 1:
                return True
            else:
                return False
    return Rule(_has_command_permission)


# 规划权限等级(暂定): 10+一般插件, 20各类订阅插件, 30+限制插件(涉及调用api), 50+涩图插件, 80+后期组用工作插件
def permission_level(level: int) -> Rule:
    async def _has_command_permission(bot: Bot, event: Event, state: T_State) -> bool:
        detail_type = event.dict().get(f'{event.get_type()}_type')
        group_id = event.dict().get('group_id')
        # 检查当前消息类型
        if detail_type != 'group':
            return False
        else:
            if DBGroup(group_id=group_id).permission_level().result >= level:
                return True
            else:
                return False
    return Rule(_has_command_permission)


# 权限节点检查
def has_auth_node(*auth_nodes: str) -> Rule:
    async def _has_auth_node(bot: Bot, event: Event, state: T_State) -> bool:
        auth_node = '.'.join(auth_nodes)
        detail_type = event.dict().get(f'{event.get_type()}_type')
        group_id = event.dict().get('group_id')
        user_id = event.dict().get('user_id')
        # 检查当前消息类型
        if detail_type == 'private':
            allow_tag = DBAuth(auth_id=user_id, auth_type='user', auth_node=auth_node).allow_tag().result
            deny_tag = DBAuth(auth_id=user_id, auth_type='user', auth_node=auth_node).deny_tag().result
        elif detail_type == 'group':
            allow_tag = DBAuth(auth_id=group_id, auth_type='group', auth_node=auth_node).allow_tag().result
            deny_tag = DBAuth(auth_id=group_id, auth_type='group', auth_node=auth_node).deny_tag().result
        else:
            allow_tag = 0
            deny_tag = 0

        if allow_tag == 1 and deny_tag == 0:
            return True
        else:
            return False
    return Rule(_has_auth_node)


# 由于目前nb2暂不支持or连接rule, 因此将or逻辑放在rule内处理
def has_level_or_node(level: int, *auth_nodes: str) -> Rule:
    async def _has_level_or_node(bot: Bot, event: Event, state: T_State) -> bool:
        auth_node = '.'.join(auth_nodes)
        detail_type = event.dict().get(f'{event.get_type()}_type')
        group_id = event.dict().get('group_id')
        user_id = event.dict().get('user_id')

        # level检查部分
        if detail_type != 'group':
            level_checker = False
        else:
            if DBGroup(group_id=group_id).permission_level().result >= level:
                return True
            else:
                level_checker = False

        # node检查部分
        if detail_type == 'private':
            allow_tag = DBAuth(auth_id=user_id, auth_type='user', auth_node=auth_node).allow_tag().result
            deny_tag = DBAuth(auth_id=user_id, auth_type='user', auth_node=auth_node).deny_tag().result
        elif detail_type == 'group':
            allow_tag = DBAuth(auth_id=group_id, auth_type='group', auth_node=auth_node).allow_tag().result
            deny_tag = DBAuth(auth_id=group_id, auth_type='group', auth_node=auth_node).deny_tag().result
        else:
            allow_tag = 0
            deny_tag = 0

        if allow_tag == 1 and deny_tag == 0:
            return True
        else:
            node_checker = False

        return level_checker or node_checker
    return Rule(_has_level_or_node)
