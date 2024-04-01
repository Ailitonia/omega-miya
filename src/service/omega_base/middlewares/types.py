"""
@Author         : Ailitonia
@Date           : 2023/6/10 16:47
@FileName       : types
@Project        : nonebot2_miya
@Description    : 中间件基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from contextlib import asynccontextmanager
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any, Iterable, Literal, Optional, Type, Union

from nonebot.internal.adapter.bot import Bot as BaseBot
from nonebot.internal.adapter.event import Event as BaseEvent
from nonebot.internal.adapter.message import Message as BaseMessage, MessageSegment as BaseMessageSegment
from nonebot.params import Depends

from src.database import begin_db_session, get_db_session

from .. import OmegaEntity
from ..message import Message as OmegaMessage, MessageSegment as OmegaMessageSegment


class ApiCaller(abc.ABC):
    """平台 API 调用适配"""

    def __init__(self, bot: BaseBot):
        self.bot = bot

    @abc.abstractmethod
    async def get_name(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        """获取名称"""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_profile_photo_url(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        """获取头像"""
        raise NotImplementedError


class EntityParams(BaseModel):
    """构造 InternalEntity 的参数"""
    bot_id: str
    entity_type: str
    entity_id: str
    parent_id: str
    entity_name: str | None = None
    entity_info: str | None = None


class EntityDepend(abc.ABC):
    """提取事件 Entity 对象依赖类"""

    def __init__(self, acquire_type: Literal['event', 'user']):
        """提取事件 Entity 对象依赖类

        :param acquire_type: event: 事件本身对应的 Entity, user: 触发事件用户的 Entity
        """
        self.acquire_type = acquire_type

    def __call__(
            self,
            bot: BaseBot,
            event: BaseEvent,
            session: Annotated[AsyncSession, Depends(get_db_session)]
    ) -> OmegaEntity:
        match self.acquire_type:
            case 'event':
                return OmegaEntity(session=session, **self.extract_event_entity_from_event(bot, event).model_dump())
            case 'user':
                return OmegaEntity(session=session, **self.extract_user_entity_from_event(bot, event).model_dump())
            case _:
                raise ValueError(f'illegal acquire_type: {self.acquire_type!r}')

    @classmethod
    @abc.abstractmethod
    def extract_event_entity_from_event(cls, bot: BaseBot, event: BaseEvent) -> EntityParams:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def extract_user_entity_from_event(cls, bot: BaseBot, event: BaseEvent) -> EntityParams:
        raise NotImplementedError

    @asynccontextmanager
    async def get_entity(self, bot: BaseBot, event: BaseEvent) -> OmegaEntity:
        """获取 OmegaEntity 并开始事务"""
        async with begin_db_session() as session:
            entity = self(bot=bot, event=event, session=session)
            yield entity


class EventHandler(abc.ABC):
    """事件处理器"""

    def __init__(self, bot: BaseBot, event: BaseEvent):
        self.bot = bot
        self.event = event

    @abc.abstractmethod
    def get_user_nickname(self) -> str:
        """获取事件用户昵称"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_msg_image_urls(self) -> list[str]:
        """获取当前事件消息中的全部图片链接"""

    @abc.abstractmethod
    def get_reply_msg_image_urls(self) -> list[str]:
        """获取回复消息中的全部图片链接"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_reply_msg_plain_text(self) -> Optional[str]:
        """获取回复消息的文本"""
        raise NotImplementedError

    @abc.abstractmethod
    async def send_at_sender(self, message: Union[str, None, BaseMessage, BaseMessageSegment], **kwargs):
        """发送消息并 @Sender"""
        raise NotImplementedError

    @abc.abstractmethod
    async def send_reply(self, message: Union[str, None, BaseMessage, BaseMessageSegment], **kwargs):
        """回复一条消息"""
        raise NotImplementedError


class MessageBuilder(abc.ABC):
    """Omega 中间件消息构造器"""

    def __init__(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment]) -> None:
        self.__message = self._build(message=message)

    @property
    def message(self) -> BaseMessage:
        return self.__message.copy()

    @staticmethod
    @abc.abstractmethod
    def _construct(message: OmegaMessage) -> Iterable[BaseMessageSegment]:
        raise NotImplementedError

    @abc.abstractmethod
    def _build(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment]) -> BaseMessage:
        raise NotImplementedError


class MessageExtractor(MessageBuilder, abc.ABC):
    """Omega 中间件消息解析器"""

    @staticmethod
    @abc.abstractmethod
    def _construct(message: BaseMessage) -> Iterable[OmegaMessageSegment]:
        raise NotImplementedError

    @abc.abstractmethod
    def _build(self, message: Union[str, None, BaseMessage, BaseMessageSegment]) -> OmegaMessage:
        raise NotImplementedError


class SenderParams(BaseModel):
    """MessageSender 发送消息参数"""
    api: str
    message_param_name: str
    params: dict[str, Any]


class RevokeParams(BaseModel):
    """MessageSender 撤回消息参数"""
    api: str
    params: dict[str, Any]


class MessageSender(abc.ABC):
    """平台/实体对象 MessageSender 基类"""

    def __init__(self, target_entity: OmegaEntity):
        self.target_entity = target_entity

    @classmethod
    @abc.abstractmethod
    def get_builder(cls) -> Type[MessageBuilder]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_extractor(cls) -> Type[MessageBuilder]:
        raise NotImplementedError

    @abc.abstractmethod
    def construct_multi_msgs(self, messages: Iterable[Union[str, None, BaseMessage, BaseMessageSegment]]):
        raise NotImplementedError

    @abc.abstractmethod
    def to_send_msg(self, **kwargs) -> SenderParams:
        raise NotImplementedError

    @abc.abstractmethod
    def to_send_multi_msgs(self, **kwargs) -> SenderParams:
        raise NotImplementedError

    @abc.abstractmethod
    def parse_revoke_sent_params(self, content: Any, **kwargs) -> Union[RevokeParams, Iterable[RevokeParams]]:
        raise NotImplementedError


__all__ = [
    'ApiCaller',
    'EntityParams',
    'EntityDepend',
    'EventHandler',
    'MessageBuilder',
    'MessageExtractor',
    'MessageSender',
    'SenderParams',
    'RevokeParams'
]
