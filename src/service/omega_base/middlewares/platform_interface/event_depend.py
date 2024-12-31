"""
@Author         : Ailitonia
@Date           : 2024/8/21 15:05:22
@FileName       : event_depend.py
@Project        : omega-miya
@Description    : 平台事件及对象依赖适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated, Any

from nonebot.internal.adapter import Event as BaseEvent
from nonebot.log import logger
from nonebot.params import Depends

from src.database import get_db_session
from ...internal import OmegaEntity

if TYPE_CHECKING:
    from nonebot.internal.adapter import Bot as BaseBot
    from sqlalchemy.ext.asyncio import AsyncSession

    from ...message import Message as OmegaMessage
    from ..models import EntityInitParams
    from ..typing import BaseMessageType, BaseSentMessageType
    from .message_builder import BaseMessageBuilder


class BaseEventDepend[Bot_T: 'BaseBot', Event_T: 'BaseEvent', Message_T: 'BaseMessageType[Any]'](abc.ABC):
    """中间件事件对象解析器: 平台事件及对象依赖适配基类"""

    def __init__(self, bot: Bot_T, event: Event_T) -> None:
        self.bot = bot
        self.event = event

    """事件 Entity 对象依赖提取方法适配"""

    @abc.abstractmethod
    def _extract_event_entity_params(self) -> 'EntityInitParams':
        """根据 Event 提取事件本身对应 Entity 实例化参数"""
        raise NotImplementedError

    @abc.abstractmethod
    def _extract_user_entity_params(self) -> 'EntityInitParams':
        """根据 Event 提取触发事件用户 Entity 实例化参数"""
        raise NotImplementedError

    @property
    def event_entity_depend(self) -> Callable[['AsyncSession'], OmegaEntity]:
        """获取事件本身对应 Entity 依赖"""

        def _depend(session: Annotated['AsyncSession', Depends(get_db_session)]) -> OmegaEntity:
            return OmegaEntity(session=session, **self._extract_event_entity_params().kwargs)

        return _depend

    @property
    def user_entity_depend(self) -> Callable[['AsyncSession'], OmegaEntity]:
        """获取触发事件用户 Entity 依赖"""

        def _depend(session: Annotated['AsyncSession', Depends(get_db_session)]) -> OmegaEntity:
            return OmegaEntity(session=session, **self._extract_user_entity_params().kwargs)

        return _depend

    """平台事件消息交互及流程处理方法适配"""

    @abc.abstractmethod
    def get_omega_message_builder(self) -> type['BaseMessageBuilder[OmegaMessage, Message_T]']:
        raise NotImplementedError

    @abc.abstractmethod
    def get_omega_message_extractor(self) -> type['BaseMessageBuilder[Message_T, OmegaMessage]']:
        raise NotImplementedError

    def build_platform_message(self, message: 'BaseSentMessageType[OmegaMessage]') -> Message_T:
        return self.get_omega_message_builder()(message=message).message

    async def send(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> Any:
        """发送消息"""
        return await self.bot.send(event=self.event, message=self.build_platform_message(message=message), **kwargs)

    @abc.abstractmethod
    async def send_at_sender(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> Any:
        """发送消息并 @Sender"""
        raise NotImplementedError

    @abc.abstractmethod
    async def send_reply(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> Any:
        """发送消息作为另一条消息的回复"""
        raise NotImplementedError

    @abc.abstractmethod
    async def revoke(self, sent_return: Any, **kwargs) -> Any:
        """撤回/删除一条已发送的消息

        :param sent_return: bot.send() 的返回值
        :param kwargs: 其他参数
        :return: 调用平台撤回/删除消息的返回值
        """
        raise NotImplementedError

    """平台事件信息提取及处理方法适配"""

    @abc.abstractmethod
    def get_user_nickname(self) -> str:
        """获取事件用户昵称"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_msg_image_urls(self) -> list[str]:
        """获取当前事件消息中的全部图片链接"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_reply_msg_image_urls(self) -> list[str]:
        """获取回复消息中的全部图片链接"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_reply_msg_plain_text(self) -> str | None:
        """获取回复消息的文本"""
        raise NotImplementedError


type EventDepend[B_T: 'BaseBot', E_T: 'BaseEvent', M_T: 'BaseMessageType[Any]'] = BaseEventDepend[B_T, E_T, M_T]


@dataclass
class EventDependRegister:
    """中间件事件对象解析器的注册工具, 用于引入平台适配"""

    _map: dict[type['BaseEvent'], type[EventDepend]] = field(default_factory=dict)

    def register_depend[Depend_T: type[EventDepend]](
            self, target_event_type: type['BaseEvent']
    ) -> Callable[[Depend_T], Depend_T]:
        """注册对应事件的事件对象解析器"""

        def _decorator(depend: Depend_T) -> Depend_T:
            if target_event_type in self._map.keys():
                logger.error(f'Duplicate event {target_event_type.__name__!r} has been registered')
                raise ValueError(f'Duplicate event {target_event_type.__name__!r}')

            self._map[target_event_type] = depend
            logger.opt(colors=True).debug(f'<e>{depend.__name__!r}</e> is registered to {target_event_type!r}')
            return depend

        return _decorator

    def get_depend(self, target_event: 'BaseEvent') -> type[EventDepend]:
        """从事件中提取对应的事件对象解析器"""
        for event_type in target_event.__class__.mro():
            if event_type in self._map.keys():
                if issubclass(event_type, BaseEvent):
                    target_event_type = event_type
                    break
                else:
                    continue
        else:
            logger.error(f'Event {target_event.__class__.__name__!r} has no registered EventDepend')
            raise ValueError('Event not supported')

        return self._map[target_event_type]


event_depend_register: EventDependRegister = EventDependRegister()
"""初始化全局中间件事件对象解析器的注册工具"""

__all__ = [
    'BaseEventDepend',
    'EventDepend',
    'event_depend_register',
]
