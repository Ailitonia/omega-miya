from nonebot.rule import Rule
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import Event, MessageEvent, PrivateMessageEvent, NoticeEvent, RequestEvent
from omega_miya.database import DBBot, DBFriend, DBBotGroup, DBAuth


class OmegaRules(object):
    # Default basic auth mode name
    basic_auth_node: str = 'basic'

    # Plugin permission rule
    # Only using for group
    @classmethod
    def has_group_notice_permission(cls) -> Rule:
        async def _has_group_notice_permission(bot: Bot, event: Event, state: T_State) -> bool:
            if isinstance(event, PrivateMessageEvent):
                return False
            group_id = getattr(event, 'group_id', None)
            self_bot = DBBot(self_qq=int(bot.self_id))
            # 检查当前消息类型
            if not group_id:
                return False
            else:
                res = await DBBotGroup(group_id=group_id, self_bot=self_bot).permission_notice()
                if res.result == 1:
                    return True
                else:
                    return False
        return Rule(_has_group_notice_permission)

    @classmethod
    def has_group_command_permission(cls) -> Rule:
        async def _has_group_command_permission(bot: Bot, event: Event, state: T_State) -> bool:
            if isinstance(event, PrivateMessageEvent):
                return False
            group_id = getattr(event, 'group_id', None)
            self_bot = DBBot(self_qq=int(bot.self_id))
            # 检查当前消息类型
            if not group_id:
                return False
            else:
                res = await DBBotGroup(group_id=group_id, self_bot=self_bot).permission_command()
                if res.result == 1:
                    return True
                else:
                    return False
        return Rule(_has_group_command_permission)

    @classmethod
    def has_group_permission_level(cls, level: int) -> Rule:
        async def _has_group_permission_level(bot: Bot, event: Event, state: T_State) -> bool:
            if isinstance(event, PrivateMessageEvent):
                return False
            group_id = getattr(event, 'group_id', None)
            self_bot = DBBot(self_qq=int(bot.self_id))
            # 检查当前消息类型
            if not group_id:
                return False
            else:
                res = await DBBotGroup(group_id=group_id, self_bot=self_bot).permission_level()
                if res.result >= level:
                    return True
                else:
                    return False
        return Rule(_has_group_permission_level)

    # 权限节点检查
    @classmethod
    def has_auth_node(cls, *auth_nodes: str) -> Rule:
        async def _has_auth_node(bot: Bot, event: Event, state: T_State) -> bool:
            auth_node = '.'.join(auth_nodes)
            group_id = getattr(event, 'group_id', None)
            user_id = getattr(event, 'user_id', None)
            self_bot = DBBot(self_qq=int(bot.self_id))
            # 检查当前消息类型
            if isinstance(event, PrivateMessageEvent):
                user_auth = DBAuth(self_bot=self_bot, auth_id=user_id, auth_type='user', auth_node=auth_node)
                user_tag_res = await user_auth.tags_info()
                allow_tag = user_tag_res.result[0]
                deny_tag = user_tag_res.result[1]
            elif group_id is not None:
                group_auth = DBAuth(self_bot=self_bot, auth_id=group_id, auth_type='group', auth_node=auth_node)
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
    @classmethod
    def has_level_or_node(cls, level: int, *auth_nodes: str) -> Rule:
        """
        :param level: 需要群组权限等级
        :param auth_nodes: 需要的权限节点
        :return: 群组权限等级大于要求等级或者具备权限节点, 权限节点为deny则拒绝
        """
        async def _has_level_or_node(bot: Bot, event: Event, state: T_State) -> bool:
            auth_node = '.'.join(auth_nodes)
            group_id = getattr(event, 'group_id', None)
            user_id = getattr(event, 'user_id', None)
            self_bot = DBBot(self_qq=int(bot.self_id))

            # level检查部分
            if not group_id:
                level_checker = False
            else:
                level_res = await DBBotGroup(group_id=group_id, self_bot=self_bot).permission_level()
                if level_res.result >= level:
                    level_checker = True
                else:
                    level_checker = False

            # node检查部分
            if isinstance(event, PrivateMessageEvent):
                user_auth = DBAuth(self_bot=self_bot, auth_id=user_id, auth_type='user', auth_node=auth_node)
                user_tag_res = await user_auth.tags_info()
                allow_tag = user_tag_res.result[0]
                deny_tag = user_tag_res.result[1]
            elif group_id is not None:
                group_auth = DBAuth(self_bot=self_bot, auth_id=group_id, auth_type='group', auth_node=auth_node)
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

    @classmethod
    def has_friend_private_permission(cls) -> Rule:
        async def _has_friend_private_permission(bot: Bot, event: Event, state: T_State) -> bool:
            if isinstance(event, MessageEvent):
                detail_type = event.message_type
            elif isinstance(event, NoticeEvent):
                detail_type = event.notice_type
            elif isinstance(event, RequestEvent):
                detail_type = event.request_type
            else:
                detail_type = None
            user_id = getattr(event, 'user_id', None)
            self_bot = DBBot(self_qq=int(bot.self_id))
            # 检查当前消息类型
            if detail_type != 'private':
                return False
            else:
                res = await DBFriend(user_id=user_id, self_bot=self_bot).get_private_permission()
                if res.result == 1:
                    return True
                else:
                    return False
        return Rule(_has_friend_private_permission)


__all__ = [
    'OmegaRules'
]
