"""
@Author         : Ailitonia
@Date           : 2023/7/3 22:31
@FileName       : console
@Project        : nonebot2_miya
@Description    : nonebot-console 协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Iterable, Tuple, Type, Union, Optional

from nonebot.adapters.console import (
    Bot as ConsoleBot,
    Message as ConsoleMessage,
    MessageSegment as ConsoleMessageSegment,
    Event as ConsoleEvent,
    MessageEvent as ConsoleMessageEvent
)

from ..api_tools import register_api_caller
from ..const import SupportedPlatform, SupportedTarget
from ..entity_tools import register_entity_depend
from ..event_tools import register_event_handler
from ..message_tools import register_builder, register_extractor, register_sender
from ..types import (
    ApiCaller,
    EntityDepend,
    EntityParams,
    EventHandler,
    MessageBuilder,
    MessageExtractor,
    MessageSender,
    SenderParams,
    RevokeParams
)
from ...internal import OmegaEntity
from ...message import (
    MessageSegmentType,
    Message as OmegaMessage,
    MessageSegment as OmegaMessageSegment
)


@register_api_caller(adapter_name=SupportedPlatform.console.value)
class ConsoleApiCaller(ApiCaller):
    """nonebot-console API 调用适配"""

    async def get_name(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        return 'ConsoleUser'

    async def get_profile_photo_url(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        return ''


@register_builder(adapter_name=SupportedPlatform.console.value)
class ConsoleMessageBuilder(MessageBuilder):

    @staticmethod
    def _construct(message: OmegaMessage) -> Iterable[ConsoleMessageSegment]:

        def _iter_message(msg: OmegaMessage) -> Iterable[Tuple[str, dict]]:
            for seg in msg:
                yield seg.type, seg.data

        for type_, data in _iter_message(message):
            match type_:
                case MessageSegmentType.text.value:
                    yield ConsoleMessageSegment.text(text=data.get('text'))
                case _:
                    pass

    def _build(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment]) -> ConsoleMessage:
        _msg = ConsoleMessage()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return ConsoleMessage(message)
        elif isinstance(message, OmegaMessageSegment):
            return ConsoleMessage(self._construct(OmegaMessage(message)))
        elif isinstance(message, OmegaMessage):
            return ConsoleMessage(self._construct(message))
        else:
            return ConsoleMessage(message)


@register_extractor(adapter_name=SupportedPlatform.console.value)
class ConsoleMessageExtractor(MessageExtractor):

    @staticmethod
    def _construct(message: ConsoleMessage) -> Iterable[OmegaMessageSegment]:

        def _iter_message(msg: ConsoleMessage) -> Iterable[Tuple[str, dict]]:
            for seg in msg:
                yield seg.type, seg.data

        for type_, data in _iter_message(message):
            match type_:
                case 'emoji':
                    yield OmegaMessageSegment.text(text=data.get('name'))
                case 'text':
                    yield OmegaMessageSegment.text(text=data.get('text'))
                case _:
                    pass

    def _build(self, message: Union[str, None, ConsoleMessage, ConsoleMessageSegment]) -> OmegaMessage:
        _msg = OmegaMessage()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return OmegaMessage(message)
        elif isinstance(message, ConsoleMessageSegment):
            return OmegaMessage(self._construct(ConsoleMessage(message)))
        elif isinstance(message, ConsoleMessage):
            return OmegaMessage(self._construct(message))
        else:
            return OmegaMessage(message)


@register_sender(target_entity=SupportedTarget.console_user.value)
class ConsoleMessageSender(MessageSender):
    """nonebot-console 消息 Sender"""

    @classmethod
    def get_builder(cls) -> Type[MessageBuilder]:
        return ConsoleMessageBuilder

    @classmethod
    def get_extractor(cls) -> Type[MessageExtractor]:
        return ConsoleMessageExtractor

    def construct_multi_msgs(self, messages: Iterable[Union[str, None, ConsoleMessage, ConsoleMessageSegment]]):
        send_message = ConsoleMessage()

        for message in messages:
            if isinstance(message, (str, ConsoleMessageSegment)):
                send_message.append(message)
            elif isinstance(message, ConsoleMessage):
                send_message.extend(message)
            else:
                pass

        return send_message

    def to_send_msg(self) -> SenderParams:
        return SenderParams(
            api='send_msg',
            message_param_name='message',
            params={
                'user_id': self.target_entity.entity_name
            }
        )

    def to_send_multi_msgs(self) -> SenderParams:
        return self.to_send_msg()

    def parse_revoke_sent_params(self, content: Any) -> Union[RevokeParams, Iterable[RevokeParams]]:
        raise NotImplementedError


@register_event_handler(event=ConsoleMessageEvent)
class ConsoleMessageEventHandler(EventHandler):
    """ConsoleMessage 消息事件处理器"""

    def get_user_nickname(self) -> str:
        return self.event.get_user_id()

    async def send_at_sender(self, message: Union[str, None, ConsoleMessage, ConsoleMessageSegment], **kwargs):
        return await self.bot.send(event=self.event, message=message, **kwargs)

    async def send_reply(self, message: Union[str, None, ConsoleMessage, ConsoleMessageSegment], **kwargs):
        return await self.bot.send(event=self.event, message=message, **kwargs)


@register_entity_depend(event=ConsoleEvent)
class ConsoleEventEntityDepend(EntityDepend):
    """nonebot-console 事件 Entity 对象依赖类"""

    @classmethod
    def extract_event_entity_from_event(cls, bot: ConsoleBot, event: ConsoleEvent) -> EntityParams:
        return cls.extract_user_entity_from_event(bot=bot, event=event)

    @classmethod
    def extract_user_entity_from_event(cls, bot: ConsoleBot, event: ConsoleEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='console_user', entity_id=event.user.id, parent_id=bot.self_id,
            entity_name=event.user.nickname, entity_info=event.user.avatar
        )


__all__ = []
