"""
@Author         : Ailitonia
@Date           : 2024/8/21 10:32:46
@FileName       : message_builder.py
@Project        : omega-miya
@Description    : 中间件消息构造器
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from copy import deepcopy
from dataclasses import field, dataclass
from typing import TYPE_CHECKING, Any, Callable, Generator

from nonebot.log import logger

from ..const import SupportedPlatform
from ..exception import AdapterNotSupported
from ..typing import BaseMessageType, BaseMessageSegType, BaseSentMessageType

if TYPE_CHECKING:
    from nonebot.internal.adapter import Message as BaseMessage, MessageSegment as BaseMessageSegment
    from ...message import Message as OmegaMessage


class BaseMessageBuilder[SourceMessage_T: BaseMessageType[Any], TargetMessage_T: BaseMessageType[Any]](abc.ABC):
    """中间件消息构造器: 通过转化消息类构造其他平台消息"""
    type SourceSegment_T = BaseMessageSegType[SourceMessage_T]
    type TargetSegment_T = BaseMessageSegType[TargetMessage_T]
    type SourceSentMessage_T = BaseSentMessageType[SourceMessage_T]

    def __init__(self, message: SourceSentMessage_T) -> None:
        self.__raw_message = message
        self.__built_message = self._build(message=self.__raw_message)

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(message={self.__raw_message})'

    @property
    def message(self) -> TargetMessage_T:
        return deepcopy(self.__built_message)

    @staticmethod
    @abc.abstractmethod
    def _get_source_base_segment_type() -> type[SourceSegment_T]:
        """内部辅助方法, 获取来源平台适配器的 MessageSegment 基类"""
        raise NotImplementedError

    @classmethod
    def _get_source_base_message_type(cls) -> type[SourceMessage_T]:
        """内部辅助方法, 获取目标平台适配器的 Message 基类"""
        return cls._get_source_base_segment_type().get_message_class()

    @staticmethod
    @abc.abstractmethod
    def _get_target_base_segment_type() -> type[TargetSegment_T]:
        """内部辅助方法, 获取目标平台适配器的 MessageSegment 基类"""
        raise NotImplementedError

    @classmethod
    def _get_target_base_message_type(cls) -> type[TargetMessage_T]:
        """内部辅助方法, 获取目标平台适配器的 Message 基类"""
        return cls._get_target_base_segment_type().get_message_class()

    @staticmethod
    def _iter_message(message: SourceMessage_T) -> Generator[tuple[str, dict[str, Any]], Any, None]:
        """内部辅助方法, 遍历来源消息提取消息段内容"""
        for seg in message:
            yield seg.type, seg.data

    @staticmethod
    @abc.abstractmethod
    def _construct_platform_segment(seg_type: str, seg_data: dict[str, Any]) -> TargetSegment_T:
        """内部辅助方法, 将消息段内容解析为平台 MessageSegment, 供消息构造使用"""
        raise NotImplementedError

    @classmethod
    def _construct(cls, message: SourceMessage_T) -> Generator[TargetSegment_T, Any, None]:
        """内部辅助方法, 遍历来源消息并构造为目标平台消息段序列"""
        for seg_type, seg_data in cls._iter_message(message=message):
            yield cls._construct_platform_segment(seg_type=seg_type, seg_data=seg_data)

    @classmethod
    def _build(cls, message: SourceSentMessage_T) -> TargetMessage_T:
        """内部方法, 根据来源消息构造对应目标平台消息"""
        source_segment_type = cls._get_source_base_segment_type()
        source_message_type = cls._get_source_base_message_type()
        target_message_type = cls._get_target_base_message_type()

        if isinstance(message, str):
            return target_message_type(message)
        elif isinstance(message, source_segment_type):
            return target_message_type(cls._construct(source_message_type(message)))
        elif isinstance(message, source_message_type):
            return target_message_type(cls._construct(message))
        else:
            return target_message_type()


type Builder[TargetMessage_T: BaseMessageType[Any]] = BaseMessageBuilder["OmegaMessage", TargetMessage_T]
"""平台消息构造器, 从 Omega 中间件消息构建平台消息"""

type Extractor[SourceMessage_T: BaseMessageType[Any]] = BaseMessageBuilder[SourceMessage_T, "OmegaMessage"]
"""平台消息解析器, 将平台消息转换为 Omega 中间件消息"""


@dataclass
class MessageBuilderRegister:
    """中间件消息构造器的注册工具, 用于引入平台适配"""

    _builder_map: dict[SupportedPlatform, type[Builder]] = field(default_factory=dict)
    _extractor_map: dict[SupportedPlatform, type[Extractor]] = field(default_factory=dict)

    def register_builder[T: type[Builder]](self, platform_name: SupportedPlatform) -> Callable[[T], T]:
        """注册平台消息构造器"""

        def _decorator(builder: T) -> T:
            if platform_name not in SupportedPlatform.get_supported_adapter_names():
                raise AdapterNotSupported(adapter_name=platform_name)

            if platform_name in self._builder_map.keys():
                logger.error(f'Duplicate platform {platform_name!r} for {builder.__name__!r} has been registered')
                raise ValueError(f'Duplicate platform {platform_name!r}')

            self._builder_map[platform_name] = builder
            logger.opt(colors=True).debug(f'<e>{builder.__name__!r}</e> is registered to {platform_name!r}')
            return builder

        return _decorator

    def register_extractor[T: type[Extractor]](self, platform_name: SupportedPlatform) -> Callable[[T], T]:
        """注册平台消息解析器"""

        def _decorator(extractor: T) -> T:
            if platform_name not in SupportedPlatform.get_supported_adapter_names():
                raise AdapterNotSupported(adapter_name=platform_name)

            if platform_name in self._extractor_map.keys():
                logger.error(f'Duplicate platform {platform_name!r} for {extractor.__name__!r} has been registered')
                raise ValueError(f'Duplicate platform {platform_name!r}')

            self._extractor_map[platform_name] = extractor
            logger.opt(colors=True).debug(f'<e>{extractor.__name__!r}</e> is registered to {platform_name!r}')
            return extractor

        return _decorator

    def get_builder(self, platform_name: SupportedPlatform) -> type[Builder["BaseMessage[BaseMessageSegment]"]]:
        """从适配器或事件中提取对应的适配器工具 target"""
        if platform_name not in SupportedPlatform.get_supported_adapter_names():
            raise AdapterNotSupported(adapter_name=platform_name)

        if platform_name not in self._builder_map.keys():
            logger.error(f'Platform {platform_name!r} has no registered MessageBuilder')
            raise ValueError('MessageBuilder not registered')

        return self._builder_map[platform_name]

    def get_extractor(self, platform_name: SupportedPlatform) -> type[Extractor["BaseMessage[BaseMessageSegment]"]]:
        """从适配器或事件中提取对应的适配器工具 target"""
        if platform_name not in SupportedPlatform.get_supported_adapter_names():
            raise AdapterNotSupported(adapter_name=platform_name)

        if platform_name not in self._extractor_map.keys():
            logger.error(f'Platform {platform_name!r} has no registered MessageExtractor')
            raise ValueError('MessageExtractor not registered')

        return self._extractor_map[platform_name]


message_builder_register: MessageBuilderRegister = MessageBuilderRegister()
"""初始化全局中间件消息构造器的注册工具"""

__all__ = [
    'BaseMessageBuilder',
    'Builder',
    'Extractor',
    'message_builder_register',
]
