from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event
from omega_miya.utils.Omega_Base import DBFriend, DBGroup, DBAuth


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
            res = await DBGroup(group_id=group_id).permission_notice()
            if res.result == 1:
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
            res = await DBGroup(group_id=group_id).permission_command()
            if res.result == 1:
                return True
            else:
                return False
    return Rule(_has_command_permission)


# 规划权限等级(暂定): 10+一般插件, 20各类订阅插件, 30+限制插件(涉及调用api), 50+涩图插件
def permission_level(level: int) -> Rule:
    async def _has_permission_level(bot: Bot, event: Event, state: T_State) -> bool:
        detail_type = event.dict().get(f'{event.get_type()}_type')
        group_id = event.dict().get('group_id')
        # 检查当前消息类型
        if detail_type != 'group':
            return False
        else:
            res = await DBGroup(group_id=group_id).permission_level()
            if res.result >= level:
                return True
            else:
                return False
    return Rule(_has_permission_level)


# 权限节点检查
def has_auth_node(*auth_nodes: str) -> Rule:
    async def _has_auth_node(bot: Bot, event: Event, state: T_State) -> bool:
        auth_node = '.'.join(auth_nodes)
        detail_type = event.dict().get(f'{event.get_type()}_type')
        group_id = event.dict().get('group_id')
        user_id = event.dict().get('user_id')
        # 检查当前消息类型
        if detail_type == 'private':
            user_auth = DBAuth(auth_id=user_id, auth_type='user', auth_node=auth_node)
            user_tag_res = await user_auth.tags_info()
            allow_tag = user_tag_res.result[0]
            deny_tag = user_tag_res.result[1]
        elif detail_type == 'group' or detail_type == 'group_upload':
            group_auth = DBAuth(auth_id=group_id, auth_type='group', auth_node=auth_node)
            group_tag_res = await group_auth.tags_info()
            allow_tag = group_tag_res.result[0]
            deny_tag = group_tag_res.result[1]
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
    """
    :param level: 需要群组权限等级
    :param auth_nodes: 需要的权限节点
    :return: 群组权限等级大于要求等级或者具备权限节点, 权限节点为deny则拒绝
    """
    async def _has_level_or_node(bot: Bot, event: Event, state: T_State) -> bool:
        auth_node = '.'.join(auth_nodes)
        detail_type = event.dict().get(f'{event.get_type()}_type')
        group_id = event.dict().get('group_id')
        user_id = event.dict().get('user_id')

        # level检查部分
        if detail_type != 'group':
            level_checker = False
        else:
            level_res = await DBGroup(group_id=group_id).permission_level()
            if level_res.result >= level:
                level_checker = True
            else:
                level_checker = False

        # node检查部分
        if detail_type == 'private':
            user_auth = DBAuth(auth_id=user_id, auth_type='user', auth_node=auth_node)
            user_tag_res = await user_auth.tags_info()
            allow_tag = user_tag_res.result[0]
            deny_tag = user_tag_res.result[1]
        elif detail_type == 'group':
            group_auth = DBAuth(auth_id=group_id, auth_type='group', auth_node=auth_node)
            group_tag_res = await group_auth.tags_info()
            allow_tag = group_tag_res.result[0]
            deny_tag = group_tag_res.result[1]
        else:
            allow_tag = 0
            deny_tag = 0

        if allow_tag == 1 and deny_tag == 0:
            return True
        elif allow_tag == -2 and deny_tag == -2:
            return level_checker
        else:
            return False

    return Rule(_has_level_or_node)


def has_friend_private_permission() -> Rule:
    async def _has_friend_private_permission(bot: Bot, event: Event, state: T_State) -> bool:
        detail_type = event.dict().get(f'{event.get_type()}_type')
        user_id = event.dict().get('user_id')
        # 检查当前消息类型
        if detail_type != 'private':
            return False
        else:
            res = await DBFriend(user_id=user_id).get_private_permission()
            if res.result == 1:
                return True
            else:
                return False
    return Rule(_has_friend_private_permission)


__all__ = [
    'has_notice_permission',
    'has_command_permission',
    'has_auth_node',
    'has_level_or_node',
    'permission_level',
    'has_friend_private_permission'
]
