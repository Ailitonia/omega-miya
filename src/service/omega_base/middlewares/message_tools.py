"""
@Author         : Ailitonia
@Date           : 2023/6/11 17:40
@FileName       : message_tools
@Project        : nonebot2_miya
@Description    : 平台消息适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Callable, Type, TypeVar, Union

from nonebot.log import logger
from nonebot.internal.adapter.bot import Bot

from .const import SupportedPlatform, SupportedTarget
from .exception import AdapterNotSupported, TargetNotSupported
from .types import MessageBuilder, MessageSender

from ..internal import OmegaEntity


__MESSAGE_BUILDERS: dict[str, Type[MessageBuilder]] = {}
__MESSAGE_EXTRACTORS: dict[str, Type[MessageBuilder]] = {}
__MESSAGE_SENDERS: dict[str, Type[MessageSender]] = {}

Builder_T = TypeVar("Builder_T", bound=Type[MessageBuilder])
Sender_T = TypeVar("Sender_T", bound=Type[MessageSender])
T = TypeVar("T")


def register_builder(adapter_name: str) -> Callable[[T], T]:
    """注册不同平台消息构造适配器"""

    def decorator(message_builder: Builder_T) -> Builder_T:
        """注册不同平台消息构造适配器"""
        global __MESSAGE_BUILDERS

        if adapter_name not in SupportedPlatform.supported_adapter_names:
            raise AdapterNotSupported(adapter_name=adapter_name)

        if adapter_name in __MESSAGE_BUILDERS.keys():
            logger.warning(f'Duplicate {message_builder.__name__!r} for {adapter_name!r} has been registered')
            return message_builder

        __MESSAGE_BUILDERS[adapter_name] = message_builder
        logger.opt(colors=True).debug(f'MessageBuilder <e>{message_builder.__name__!r}</e> is registered')
        return message_builder

    return decorator


def register_extractor(adapter_name: str) -> Callable[[T], T]:
    """注册不同平台消息解析适配器"""

    def decorator(message_extractor: Builder_T) -> Builder_T:
        """注册不同平台消息构造适配器"""
        global __MESSAGE_EXTRACTORS

        if adapter_name not in SupportedPlatform.supported_adapter_names:
            raise AdapterNotSupported(adapter_name=adapter_name)

        if adapter_name in __MESSAGE_EXTRACTORS.keys():
            logger.warning(f'Duplicate {message_extractor.__name__!r} for {adapter_name!r} has been registered')
            return message_extractor

        __MESSAGE_EXTRACTORS[adapter_name] = message_extractor
        logger.opt(colors=True).debug(f'MessageExtractor <e>{message_extractor.__name__!r}</e> is registered')
        return message_extractor

    return decorator


def register_sender(target_entity: str) -> Callable[[T], T]:
    """注册不同平台消息发送适配器"""

    def decorator(message_sender: Sender_T) -> Sender_T:
        """注册不同平台消息发送适配器"""
        global __MESSAGE_SENDERS

        if target_entity not in SupportedTarget.supported_target_names:
            raise TargetNotSupported(target_name=target_entity)

        if target_entity in __MESSAGE_SENDERS.keys():
            logger.warning(f'Duplicate {message_sender.__name__!r} for {target_entity!r} has been registered')
            return message_sender

        __MESSAGE_SENDERS[target_entity] = message_sender
        logger.opt(colors=True).debug(f'MessageSender <e>{message_sender.__name__!r}</e> is registered')
        return message_sender

    return decorator


def get_msg_builder(platform: Union[str, Bot]) -> Type[MessageBuilder]:
    """根据适配平台获取 MessageBuilder"""

    adapter_name = platform.adapter.get_name() if isinstance(platform, Bot) else platform

    if adapter_name not in SupportedPlatform.supported_adapter_names or adapter_name not in __MESSAGE_BUILDERS.keys():
        raise AdapterNotSupported(adapter_name=adapter_name)
    return __MESSAGE_BUILDERS[adapter_name]


def get_msg_extractor(platform: Union[str, Bot]) -> Type[MessageBuilder]:
    """根据适配平台获取 MessageExtractor"""

    adapter_name = platform.adapter.get_name() if isinstance(platform, Bot) else platform

    if adapter_name not in SupportedPlatform.supported_adapter_names or adapter_name not in __MESSAGE_EXTRACTORS.keys():
        raise AdapterNotSupported(adapter_name=adapter_name)
    return __MESSAGE_EXTRACTORS[adapter_name]


def get_msg_sender(target: Union[str, OmegaEntity]) -> Type[MessageSender]:
    """根据适配平台获取 MessageSender"""

    target_entity = target.entity_type if isinstance(target, OmegaEntity) else target

    if target_entity not in SupportedTarget.supported_target_names or target_entity not in __MESSAGE_SENDERS.keys():
        raise TargetNotSupported(target_name=target_entity)
    return __MESSAGE_SENDERS[target_entity]


__all__ = [
    'register_builder',
    'register_extractor',
    'register_sender',
    'get_msg_builder',
    'get_msg_extractor',
    'get_msg_sender'
]
