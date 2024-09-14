"""
@Author         : Ailitonia
@Date           : 2024/8/21 下午6:28
@FileName       : entity_target
@Project        : nonebot2_miya
@Description    : 平台 API 及 Entity 方法适配工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from dataclasses import field, dataclass
from typing import TYPE_CHECKING, Any, Callable

from nonebot.log import logger

from src.service.omega_multibot_support import get_online_bots
from ..const import SupportedTarget
from ..exception import BotNoFound, TargetNotSupported

if TYPE_CHECKING:
    from nonebot.internal.adapter import Bot as BaseBot
    from ..models import EntityTargetSendParams, EntityTargetRevokeParams
    from ...internal import OmegaEntity


class BaseEntityTarget(abc.ABC):
    """中间件平台 API 适配器: 平台 API 及 Entity 方法适配工具基类"""

    def __init__(self, entity: "OmegaEntity") -> None:
        self.entity = entity

    async def get_bot(self) -> "BaseBot":
        """获取 Entity 对应 Bot 实例"""
        bot_self = await self.entity.query_bot_self()
        bot = get_online_bots().get(bot_self.bot_type, {}).get(bot_self.self_id)
        if not bot:
            raise BotNoFound(bot_self.self_id)
        return bot

    """平台发送消息 API 调用适配"""

    @abc.abstractmethod
    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        """获取向 Entity 发送消息调用的 API 名称及参数"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        """获取撤回已发送消息调用的 API 名称及参数"""
        raise NotImplementedError

    """对象通用方法平台 API 调用适配"""

    @abc.abstractmethod
    async def call_api_get_entity_name(self) -> str:
        """调用平台 API: 获取对象名称/昵称"""
        raise NotImplementedError

    @abc.abstractmethod
    async def call_api_get_entity_profile_image_url(self) -> str:
        """调用平台 API: 获取对象头像/图标"""
        raise NotImplementedError

    @abc.abstractmethod
    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        """调用平台 API: 发送本地文件"""
        raise NotImplementedError


@dataclass
class EntityTargetRegister:
    """中间件平台 API 适配器的注册工具, 用于引入平台适配"""

    _map: dict[SupportedTarget, type[BaseEntityTarget]] = field(default_factory=dict)

    def register_target[T: type[BaseEntityTarget]](self, target_name: SupportedTarget) -> Callable[[T], T]:
        """注册中间件平台 API 适配器"""

        def _decorator(target_type: T) -> T:
            if target_name not in SupportedTarget.get_supported_target_names():
                raise TargetNotSupported(target_name=target_name)

            if target_name in self._map.keys():
                logger.error(f'Duplicate entity {target_name!r} for {target_type.__name__!r} has been registered')
                raise ValueError(f'Duplicate entity {target_name!r}')

            self._map[target_name] = target_type
            logger.opt(colors=True).debug(f'<e>{target_type.__name__!r}</e> is registered to {target_name!r}')
            return target_type

        return _decorator

    def get_target(self, target_name: SupportedTarget) -> type[BaseEntityTarget]:
        """提取 Entity 对应的中间件平台 API 适配器"""
        if target_name not in SupportedTarget.get_supported_target_names():
            raise TargetNotSupported(target_name=target_name)

        if target_name not in self._map.keys():
            logger.error(f'Entity {target_name!r} has no registered EntityTarget')
            raise ValueError('EntityTarget not registered')

        return self._map[target_name]


entity_target_register: EntityTargetRegister = EntityTargetRegister()
"""初始化全局中间件平台 API 适配器的注册工具"""

__all__ = [
    'BaseEntityTarget',
    'entity_target_register',
]
