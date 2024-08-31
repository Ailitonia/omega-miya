"""
@Author         : Ailitonia
@Date           : 2023/6/24 21:31
@FileName       : permission
@Project        : nonebot2_miya
@Description    : 自定义 Rule 依赖注入
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.adapters import Bot as BaseBot, Event as BaseEvent
from nonebot.rule import Rule

from src.database import begin_db_session
from src.service import OmegaMatcherInterface


class EventGlobalPermissionRule:
    """检查当前事件是否有全局权限"""

    __slots__ = ()

    async def __call__(self, bot: BaseBot, event: BaseEvent) -> bool:
        async with begin_db_session() as session:
            event_entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='event')
            has_global_permission = await event_entity.check_global_permission()
        return has_global_permission  # caught NoResultFound exception


class EventPermissionLevelRule:
    """检查当前事件是否有具有权限等级"""

    __slots__ = ('level',)

    def __init__(self, level: int):
        self.level = level

    async def __call__(self, bot: BaseBot, event: BaseEvent) -> bool:
        async with begin_db_session() as session:
            event_entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='event')
            has_global_permission = await event_entity.check_global_permission()
            has_permission_level = await event_entity.check_permission_level(level=self.level)
        return has_global_permission and has_permission_level  # caught NoResultFound exception


class EventPermissionNodeRule:
    """检查当前事件是否有具有权限节点"""

    __slots__ = ('module', 'plugin', 'node')

    def __init__(self, module: str, plugin: str, node: str):
        self.module = module
        self.plugin = plugin
        self.node = node

    async def __call__(self, bot: BaseBot, event: BaseEvent) -> bool:
        async with begin_db_session() as session:
            event_entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='event')
            has_global_permission = await event_entity.check_global_permission()
            has_auth = await event_entity.check_auth_setting(module=self.module, plugin=self.plugin, node=self.node)
        return has_global_permission and has_auth  # caught NoResultFound exception


class UserGlobalPermissionRule:
    """检查用户是否有全局权限"""

    __slots__ = ()

    async def __call__(self, bot: BaseBot, event: BaseEvent) -> bool:
        async with begin_db_session() as session:
            user_entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='user')
            has_global_permission = await user_entity.check_global_permission()
        return has_global_permission  # caught NoResultFound exception


class UserPermissionLevelRule:
    """检查用户是否有具有权限等级"""

    __slots__ = ('level',)

    def __init__(self, level: int):
        self.level = level

    async def __call__(self, bot: BaseBot, event: BaseEvent) -> bool:
        async with begin_db_session() as session:
            user_entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='user')
            has_global_permission = await user_entity.check_global_permission()
            has_permission_level = await user_entity.check_permission_level(level=self.level)
        return has_global_permission and has_permission_level  # caught NoResultFound exception


class UserPermissionNodeRule:
    """检查用户是否有具有权限节点"""

    __slots__ = ('module', 'plugin', 'node')

    def __init__(self, module: str, plugin: str, node: str):
        self.module = module
        self.plugin = plugin
        self.node = node

    async def __call__(self, bot: BaseBot, event: BaseEvent) -> bool:
        async with begin_db_session() as session:
            user_entity = OmegaMatcherInterface.get_entity(bot=bot, event=event, session=session, acquire_type='user')
            has_global_permission = await user_entity.check_global_permission()
            has_auth = await user_entity.check_auth_setting(module=self.module, plugin=self.plugin, node=self.node)
        return has_global_permission and has_auth  # caught NoResultFound exception


def event_has_global_permission() -> Rule:
    """匹配具有全局权限的群组/频道"""

    return Rule(EventGlobalPermissionRule())


def event_has_permission_level(level: int) -> Rule:
    """匹配具有权限等级的群组/频道"""

    return Rule(EventPermissionLevelRule(level=level))


def event_has_permission_node(module: str, plugin: str, node: str) -> Rule:
    """匹配具有权限节点的群组/频道"""

    return Rule(EventPermissionNodeRule(module=module, plugin=plugin, node=node))


def user_has_global_permission() -> Rule:
    """匹配具有全局权限的用户"""

    return Rule(UserGlobalPermissionRule())


def user_has_permission_level(level: int) -> Rule:
    """匹配具有权限等级的用户"""

    return Rule(UserPermissionLevelRule(level=level))


def user_has_permission_node(module: str, plugin: str, node: str) -> Rule:
    """匹配具有权限节点的用户"""

    return Rule(UserPermissionNodeRule(module=module, plugin=plugin, node=node))


__all__ = [
    'event_has_global_permission',
    'event_has_permission_level',
    'event_has_permission_node',
    'user_has_global_permission',
    'user_has_permission_level',
    'user_has_permission_node',
]
