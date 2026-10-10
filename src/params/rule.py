"""
@Author         : Ailitonia
@Date           : 2023/6/24 21:31
@FileName       : rule
@Project        : nonebot2_miya
@Description    : 自定义 Rule 依赖注入
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING

from nonebot.adapters import Bot as BaseBot
from nonebot.adapters import Event as BaseEvent
from nonebot.log import logger
from nonebot.rule import Rule

from src.database.helpers import database_session
from src.service import OmegaMatcherInterface
from src.service.omega_base.internal import EntityAcquireType

if TYPE_CHECKING:
    from src.service.omega_base.internal import OmegaEntity


class _BasePermissionRule:
    """权限 Rule 检查基类

    检查过程抛出异常 (如数据库故障、事件类型未注册) 时视为无权限 (fail-closed),
    记录警告日志而非将异常抛出到事件分发层
    """

    __slots__ = ('acquire_type',)

    def __init__(self, acquire_type: EntityAcquireType) -> None:
        self.acquire_type = acquire_type

    async def _check_entity_permission(self, entity: 'OmegaEntity') -> bool:
        """对目标 Entity 执行具体的权限检查"""
        raise NotImplementedError

    async def __call__(self, bot: BaseBot, event: BaseEvent) -> bool:
        try:
            async with database_session() as session:
                entity = OmegaMatcherInterface.get_target_entity(
                    bot=bot,
                    event=event,
                    db_session=session,
                    acquire_type=self.acquire_type,
                )
                return await self._check_entity_permission(entity)
        except Exception as e:
            logger.warning(f'{self.__class__.__name__} | Permission check failed, denied, {e!r}')
            return False


class EventGlobalPermissionRule(_BasePermissionRule):
    """检查当前事件是否有全局权限"""

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__(acquire_type='event')

    async def _check_entity_permission(self, entity: 'OmegaEntity') -> bool:
        return await entity.check_global_permission()


class EventPermissionLevelRule(_BasePermissionRule):
    """检查当前事件是否具有权限等级"""

    __slots__ = ('level',)

    def __init__(self, level: int):
        super().__init__(acquire_type='event')
        self.level = level

    async def _check_entity_permission(self, entity: 'OmegaEntity') -> bool:
        if not await entity.check_global_permission():
            return False
        return await entity.check_permission_level(level=self.level)


class EventPermissionNodeRule(_BasePermissionRule):
    """检查当前事件是否具有权限节点"""

    __slots__ = ('module', 'plugin', 'node')

    def __init__(self, module: str, plugin: str, node: str):
        super().__init__(acquire_type='event')
        self.module = module
        self.plugin = plugin
        self.node = node

    async def _check_entity_permission(self, entity: 'OmegaEntity') -> bool:
        if not await entity.check_global_permission():
            return False
        verified_auth = await entity.verify_auth_setting(
            module=self.module,
            plugin=self.plugin,
            node=self.node,
        )
        return verified_auth == 1


class UserGlobalPermissionRule(_BasePermissionRule):
    """检查用户是否有全局权限"""

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__(acquire_type='user')

    async def _check_entity_permission(self, entity: 'OmegaEntity') -> bool:
        return await entity.check_global_permission()


class UserPermissionLevelRule(_BasePermissionRule):
    """检查用户是否具有权限等级"""

    __slots__ = ('level',)

    def __init__(self, level: int):
        super().__init__(acquire_type='user')
        self.level = level

    async def _check_entity_permission(self, entity: 'OmegaEntity') -> bool:
        if not await entity.check_global_permission():
            return False
        return await entity.check_permission_level(level=self.level)


class UserPermissionNodeRule(_BasePermissionRule):
    """检查用户是否具有权限节点"""

    __slots__ = ('module', 'plugin', 'node')

    def __init__(self, module: str, plugin: str, node: str):
        super().__init__(acquire_type='user')
        self.module = module
        self.plugin = plugin
        self.node = node

    async def _check_entity_permission(self, entity: 'OmegaEntity') -> bool:
        if not await entity.check_global_permission():
            return False
        verified_auth = await entity.verify_auth_setting(
            module=self.module,
            plugin=self.plugin,
            node=self.node,
        )
        return verified_auth == 1


def event_has_global_permission() -> Rule:
    """匹配具有全局权限的事件"""

    return Rule(EventGlobalPermissionRule())


def event_has_permission_level(level: int) -> Rule:
    """匹配具有权限等级的事件"""

    return Rule(EventPermissionLevelRule(level=level))


def event_has_permission_node(module: str, plugin: str, node: str) -> Rule:
    """匹配具有权限节点的事件"""

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
