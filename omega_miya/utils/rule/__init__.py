"""
@Author         : Ailitonia
@Date           : 2022/04/23 15:04
@FileName       : rule.py
@Project        : nonebot2_miya
@Description    : 自定义匹配规则
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.rule import Rule
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event

from omega_miya.database import EventEntityHelper
from omega_miya.utils.process_utils import run_async_catching_exception


class UserGlobalPermissionRule:
    """检查用户是否有全局权限"""

    __slots__ = ()

    async def __call__(self, bot: Bot, event: Event) -> bool:
        user_id = getattr(event, 'user_id', None)
        if user_id is None:
            return False

        user = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
        check_result = await run_async_catching_exception(user.check_global_permission)()
        if isinstance(check_result, Exception) or not check_result:
            return False
        else:
            return True


class UserPermissionLevelRule:
    """检查用户是否有具有权限等级"""

    __slots__ = ('level',)

    def __init__(self, level: int):
        self.level = level

    async def __call__(self, bot: Bot, event: Event) -> bool:
        user_id = getattr(event, 'user_id', None)
        if user_id is None:
            return False

        user = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
        check_result = await run_async_catching_exception(user.check_permission_level)(level=self.level)
        if isinstance(check_result, Exception) or not check_result:
            return False
        else:
            return True


class UserPermissionNodeRule:
    """检查用户是否有具有权限节点"""

    __slots__ = ('module', 'plugin', 'node')

    def __init__(self, module: str, plugin: str, node: str):
        self.module = module
        self.plugin = plugin
        self.node = node

    async def __call__(self, bot: Bot, event: Event) -> bool:
        user_id = getattr(event, 'user_id', None)
        if user_id is None:
            return False

        user = EventEntityHelper(bot=bot, event=event).get_event_user_entity()
        check_result = await run_async_catching_exception(user.check_auth_setting)(
            module=self.module, plugin=self.plugin, node=self.node, available=1, require_available=False)
        if isinstance(check_result, Exception) or not check_result:
            return False
        else:
            return True


class GroupGlobalPermissionRule:
    """检查群组/频道是否有全局权限"""

    __slots__ = ()

    async def __call__(self, bot: Bot, event: Event) -> bool:
        group = EventEntityHelper(bot=bot, event=event).get_event_entity()
        if group.relation_type == 'bot_user':
            return False

        check_result = await run_async_catching_exception(group.check_global_permission)()
        if isinstance(check_result, Exception) or not check_result:
            return False
        else:
            return True


class GroupPermissionLevelRule:
    """检查群组/频道是否有具有权限等级"""

    __slots__ = ('level',)

    def __init__(self, level: int):
        self.level = level

    async def __call__(self, bot: Bot, event: Event) -> bool:
        group = EventEntityHelper(bot=bot, event=event).get_event_entity()
        if group.relation_type == 'bot_user':
            return False

        check_result = await run_async_catching_exception(group.check_permission_level)(level=self.level)
        if isinstance(check_result, Exception) or not check_result:
            return False
        else:
            return True


class GroupPermissionNodeRule:
    """检查群组/频道是否有具有权限节点"""

    __slots__ = ('module', 'plugin', 'node')

    def __init__(self, module: str, plugin: str, node: str):
        self.module = module
        self.plugin = plugin
        self.node = node

    async def __call__(self, bot: Bot, event: Event) -> bool:
        group = EventEntityHelper(bot=bot, event=event).get_event_entity()
        if group.relation_type == 'bot_user':
            return False

        check_result = await run_async_catching_exception(group.check_auth_setting)(
            module=self.module, plugin=self.plugin, node=self.node, available=1, require_available=False)
        if isinstance(check_result, Exception) or not check_result:
            return False
        else:
            return True


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
    'user_has_global_permission',
    'user_has_permission_level',
    'user_has_permission_node',
    'group_has_global_permission',
    'group_has_permission_level',
    'group_has_permission_node'
]
