"""
@Author         : Ailitonia
@Date           : 2022/12/08 21:54
@FileName       : onebot_v11.py
@Project        : nonebot2_miya
@Description    : Onebot v11 dependencies
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal
from nonebot.params import Depends
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import Bot, Event, MessageEvent, GroupMessageEvent, PrivateMessageEvent
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from src.service.gocqhttp_guild_patch import GuildMessageEvent
from src.service.omega_base import OmegaEntity


class OneBotV11EntityDepend(object):
    """Onebot V11 事件对应的 Entity 数据库对象依赖类"""

    def __init__(self, acquire_type: Literal['event', 'user']):
        self.acquire_type = acquire_type

    def __call__(self, bot: Bot, event: Event, session: AsyncSession = Depends(get_db_session)) -> OmegaEntity:
        match self.acquire_type:
            case 'event':
                return OmegaEntity(session=session, **self.generate_event_entity_params_from_event(bot, event))
            case 'user':
                return OmegaEntity(session=session, **self.generate_user_entity_params_from_event(bot, event))
            case _:
                raise ValueError(f'illegal acquire_type: "{self.acquire_type}"')

    @staticmethod
    def generate_event_entity_params_from_event(bot: Bot, event: Event) -> dict:
        """根据 Event 生成对应 Entity 的构造参数"""
        params = {'bot_id': bot.self_id, 'parent_id': bot.self_id}

        if isinstance(event, GroupMessageEvent):
            params.update({'entity_id': str(event.group_id), 'entity_type': 'qq_group'})
        elif isinstance(event, GuildMessageEvent):
            event: GuildMessageEvent
            params.update({'entity_id': str(event.channel_id), 'entity_type': 'qq_guild_channel',
                           'parent_id': str(event.guild_id)})
        elif isinstance(event, PrivateMessageEvent):
            params.update({'entity_id': str(event.user_id), 'entity_type': 'qq_user'})
        elif group_id := getattr(event, 'group_id', None):
            params.update({'entity_id': str(group_id), 'entity_type': 'qq_group'})
        elif (guild_id := getattr(event, 'guild_id', None)) and (channel_id := getattr(event, 'channel_id', None)):
            params.update({'entity_id': str(channel_id), 'entity_type': 'qq_guild_channel', 'parent_id': str(guild_id)})
        elif user_id := getattr(event, 'user_id', None):
            params.update({'entity_id': str(user_id), 'entity_type': 'qq_user'})
        else:
            params.update({'entity_id': bot.self_id, 'entity_type': 'qq_user'})

        return params

    @staticmethod
    def generate_user_entity_params_from_event(bot: Bot, event: Event) -> dict:
        """根据 Event 生成对应 Entity 的构造参数"""
        params = {'bot_id': bot.self_id, 'parent_id': bot.self_id}

        if isinstance(event, GuildMessageEvent):
            event: GuildMessageEvent
            params.update({'entity_id': str(event.user_id), 'entity_type': 'qq_guild_user',
                           'parent_id': str(event.guild_id)})
        elif isinstance(event, MessageEvent):  # event type: GroupMessageEvent | PrivateMessageEvent
            params.update({'entity_id': str(event.user_id), 'entity_type': 'qq_user'})
        elif user_id := getattr(event, 'user_id', None):
            params.update({'entity_id': str(user_id), 'entity_type': 'qq_user'})
        else:
            params.update({'entity_id': bot.self_id, 'entity_type': 'qq_user'})

        return params


class UserGlobalPermissionRule:
    """检查用户是否有全局权限"""

    __slots__ = ()

    async def __call__(self, bot: Bot, event: Event, session: AsyncSession = Depends(get_db_session)) -> bool:
        user_id = getattr(event, 'user_id', None)
        if user_id is None:
            return False

        user_params = OneBotV11EntityDepend.generate_user_entity_params_from_event(bot=bot, event=event)
        entity = OmegaEntity(session=session, **user_params)

        check_result = await entity.check_global_permission()  # caught NoResultFound exception
        return check_result


class UserPermissionLevelRule:
    """检查用户是否有具有权限等级"""

    __slots__ = ('level',)

    def __init__(self, level: int):
        self.level = level

    async def __call__(self, bot: Bot, event: Event, session: AsyncSession = Depends(get_db_session)) -> bool:
        user_id = getattr(event, 'user_id', None)
        if user_id is None:
            return False

        user_params = OneBotV11EntityDepend.generate_user_entity_params_from_event(bot=bot, event=event)
        entity = OmegaEntity(session=session, **user_params)

        check_result = await entity.check_permission_level(level=self.level)  # caught NoResultFound exception
        return check_result


class UserPermissionNodeRule:
    """检查用户是否有具有权限节点"""

    __slots__ = ('module', 'plugin', 'node')

    def __init__(self, module: str, plugin: str, node: str):
        self.module = module
        self.plugin = plugin
        self.node = node

    async def __call__(self, bot: Bot, event: Event, session: AsyncSession = Depends(get_db_session)) -> bool:
        user_id = getattr(event, 'user_id', None)
        if user_id is None:
            return False

        user_params = OneBotV11EntityDepend.generate_user_entity_params_from_event(bot=bot, event=event)
        entity = OmegaEntity(session=session, **user_params)

        check_result = await entity.check_auth_setting(module=self.module, plugin=self.plugin, node=self.node)
        return check_result


class GroupGlobalPermissionRule:
    """检查群组/频道是否有全局权限"""

    __slots__ = ()

    async def __call__(self, bot: Bot, event: Event, session: AsyncSession = Depends(get_db_session)) -> bool:
        group_params = OneBotV11EntityDepend.generate_event_entity_params_from_event(bot=bot, event=event)
        entity = OmegaEntity(session=session, **group_params)
        if entity.entity_type == 'qq_user' or entity.entity_type == 'qq_guild_user':
            return False

        check_result = await entity.check_global_permission()  # caught NoResultFound exception
        return check_result


class GroupPermissionLevelRule:
    """检查群组/频道是否有具有权限等级"""

    __slots__ = ('level',)

    def __init__(self, level: int):
        self.level = level

    async def __call__(self, bot: Bot, event: Event, session: AsyncSession = Depends(get_db_session)) -> bool:
        group_params = OneBotV11EntityDepend.generate_event_entity_params_from_event(bot=bot, event=event)
        entity = OmegaEntity(session=session, **group_params)
        if entity.entity_type == 'qq_user' or entity.entity_type == 'qq_guild_user':
            return False

        check_result = await entity.check_permission_level(level=self.level)  # caught NoResultFound exception
        return check_result


class GroupPermissionNodeRule:
    """检查群组/频道是否有具有权限节点"""

    __slots__ = ('module', 'plugin', 'node')

    def __init__(self, module: str, plugin: str, node: str):
        self.module = module
        self.plugin = plugin
        self.node = node

    async def __call__(self, bot: Bot, event: Event, session: AsyncSession = Depends(get_db_session)) -> bool:
        group_params = OneBotV11EntityDepend.generate_event_entity_params_from_event(bot=bot, event=event)
        entity = OmegaEntity(session=session, **group_params)
        if entity.entity_type == 'qq_user' or entity.entity_type == 'qq_guild_user':
            return False

        check_result = await entity.check_auth_setting(module=self.module, plugin=self.plugin, node=self.node)
        return check_result


def user_has_global_permission() -> Rule:
    """匹配具有全局权限的用户"""

    return Rule(UserGlobalPermissionRule())


def user_has_permission_level(level: int) -> Rule:
    """匹配具有权限等级的用户"""

    return Rule(UserGlobalPermissionRule()) & Rule(UserPermissionLevelRule(level=level))


def user_has_permission_node(module: str, plugin: str, node: str) -> Rule:
    """匹配具有权限节点的用户"""

    return Rule(UserGlobalPermissionRule()) & Rule(UserPermissionNodeRule(module=module, plugin=plugin, node=node))


def group_has_global_permission() -> Rule:
    """匹配具有全局权限的群组/频道"""

    return Rule(GroupGlobalPermissionRule())


def group_has_permission_level(level: int) -> Rule:
    """匹配具有权限等级的群组/频道"""

    return Rule(GroupGlobalPermissionRule()) & Rule(GroupPermissionLevelRule(level=level))


def group_has_permission_node(module: str, plugin: str, node: str) -> Rule:
    """匹配具有权限节点的群组/频道"""

    return Rule(GroupGlobalPermissionRule()) & Rule(GroupPermissionNodeRule(module=module, plugin=plugin, node=node))


__all__ = [
    'OneBotV11EntityDepend',
    'user_has_global_permission',
    'user_has_permission_level',
    'user_has_permission_node',
    'group_has_global_permission',
    'group_has_permission_level',
    'group_has_permission_node'
]
