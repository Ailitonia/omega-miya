"""
@Author         : Ailitonia
@Date           : 2024/3/24 12:08
@FileName       : register
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from typing import Callable, TypeVar

from nonebot.log import logger
from nonebot.internal.adapter.bot import Bot
from nonebot.internal.adapter.event import Event

from .const import SupportedPlatform, SupportedTarget
from .exception import AdapterNotSupported, TargetNotSupported
from ..internal import OmegaEntity


Depend_T = TypeVar("Depend_T")
Target_T = TypeVar("Target_T")
T = TypeVar("T")


class BaseRegister(object):
    """生成适配器、事件的注册器"""

    def __init__(self):
        self._map: dict[Depend_T, Target_T] = {}

    def _filter_depend(self, depend: Depend_T) -> None:
        """预处理, 条件遍历 depend, 避免注册时出现重复等情况, 默认为空"""
        if depend in self._map.keys():
            logger.error(f'Duplicate {self.__class__.__name__!r} for {depend.__name__!r} has been registered')
            raise ValueError('Duplicate depend')

    def _handle_depend(self, depend: Depend_T) -> Depend_T:
        """预处理, 获取 target 时遍历 depend 保证结果唯一"""
        if depend not in self._map.keys():
            logger.error(f'{self.__class__.__name__!r} not support {depend.__name__!r}')
            raise ValueError('Depend not support')
        return depend

    def register(self, depend: Depend_T) -> Callable[[Target_T], Target_T]:
        """注册不同目标对象依赖类"""

        def _decorator(target: Target_T) -> Target_T:
            self._filter_depend(depend=depend)
            self._map[depend] = target
            logger.opt(colors=True).debug(f'{self.__class__.__name__!r} <e>{target.__name__!r}</e> is registered')
            return target

        return _decorator

    def get_target(self, depend: Depend_T) -> Target_T:
        """从适配器或事件中提取目标依赖"""
        _depend = self._handle_depend(depend=depend)
        return self._map[_depend]


class BaseAdapterRegister(BaseRegister):
    """Depend 为 Adapter 的注册器基类"""

    def _filter_depend(self, depend: Depend_T) -> None:
        if depend not in SupportedPlatform.supported_adapter_names:
            raise AdapterNotSupported(adapter_name=depend)
        super()._filter_depend(depend=depend)

    def _handle_depend(self, depend: Depend_T) -> Depend_T:
        adapter_name = depend.adapter.get_name() if isinstance(depend, Bot) else depend

        if adapter_name not in SupportedPlatform.supported_adapter_names or adapter_name not in self._map.keys():
            raise AdapterNotSupported(adapter_name=adapter_name)
        return adapter_name


class BaseEventRegister(BaseRegister):
    """Depend 为 Event 的注册器基类"""

    def _handle_depend(self, depend: Depend_T) -> Depend_T:
        for event_type in depend.__class__.mro():
            if event_type in self._map:
                if not issubclass(event_type, Event):
                    break
                return event_type
        raise RuntimeError(f'Event {depend.__class__!r} not supported')


class BaseTargetRegister(BaseRegister):
    """Depend 为平台对象实例的注册器基类"""

    def _filter_depend(self, depend: Depend_T) -> None:
        if depend not in SupportedTarget.supported_target_names:
            raise TargetNotSupported(target_name=depend)
        super()._filter_depend(depend=depend)

    def _handle_depend(self, depend: Depend_T) -> Depend_T:
        target_entity = depend.entity_type if isinstance(depend, OmegaEntity) else depend

        if target_entity not in SupportedTarget.supported_target_names or target_entity not in self._map.keys():
            raise TargetNotSupported(target_name=target_entity)
        return target_entity


class ApiCallerRegister(BaseAdapterRegister):
    """注册不同平台 API 适配器

    Depend: adapter_name: str
    Target: Type[ApiCaller]
    """
    ...


class EntityDependRegister(BaseEventRegister):
    """注册不同事件的 Entity 对象依赖类

    Depend: Type[Event]
    Target: Type[EntityDepend]
    """
    ...


class EventHandlerRegister(BaseEventRegister):
    """注册不同事件的 EventHandler

    Depend: Type[Event]
    Target: Type[EventHandler]
    """
    ...


class MessageBuilderRegister(BaseAdapterRegister):
    """注册不同平台消息构造适配器

    Depend: adapter_name: str
    Target: Type[MessageBuilder]
    """
    ...


class MessageExtractorRegister(BaseAdapterRegister):
    """注册不同平台消息解析适配器

    Depend: adapter_name: str
    Target: Type[MessageExtractor]
    """
    ...


class MessageSenderRegister(BaseTargetRegister):
    """注册不同平台消息解析适配器

    Depend: target_entity: str
    Target: Type[MessageSender]
    """
    ...


@dataclass
class PlatformRegister:
    """多平台注册器集合"""
    api_caller = ApiCallerRegister()
    entity_depend = EntityDependRegister()
    event_handler = EventHandlerRegister()
    message_builder = MessageBuilderRegister()
    message_extractor = MessageExtractorRegister()
    message_sender = MessageSenderRegister()


__all__ = [
    'PlatformRegister',
]
