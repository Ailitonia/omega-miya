"""
@Author         : Ailitonia
@Date           : 2023/8/12 21:28
@FileName       : qqguild
@Project        : nonebot2_miya
@Description    : QQGuild 协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pathlib import Path
from typing import Any, Iterable, Tuple, Type, Union, Optional, cast
from urllib.parse import urlparse

from nonebot.adapters.qqguild import (
    Bot as QQGuildBot,
    Message as QQGuildMessage,
    MessageSegment as QQGuildMessageSegment,
    Event as QQGuildEvent,
    MessageEvent as QQGuildMessageEvent
)
from nonebot.adapters.qqguild.api import MessageReference

from ..api_tools import register_api_caller
from ..const import SupportedPlatform, SupportedTarget
from ..event_tools import register_event_handler
from ..entity_tools import register_entity_depend
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


@register_api_caller(adapter_name=SupportedPlatform.qqguild.value)
class QQGuildApiCaller(ApiCaller):
    """QQGuild API 调用适配"""

    async def get_name(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        if id_ is not None:
            raise ValueError('id param not support ')

        if entity.entity_type == SupportedTarget.qqguild_guild.value:
            guild_data = await self.bot.call_api('get_guild', guild_id=entity.entity_id)
            entity_name = guild_data.name
        elif entity.entity_type == SupportedTarget.qqguild_channel.value:
            channel_data = await self.bot.call_api('get_channel', channel_id=entity.entity_id)
            entity_name = channel_data.name
        elif entity.entity_type == SupportedTarget.qqguild_user.value:
            guild_user_data = await self.bot.call_api(
                'get_member', guild_id=entity.parent_id, user_id=entity.entity_id
            )
            entity_name = guild_user_data.nick
        else:
            raise ValueError(f'entity type {entity.entity_type!r} not support')

        return entity_name

    async def get_profile_photo_url(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        if entity.entity_type == SupportedTarget.qqguild_guild.value:
            guild_data = await self.bot.call_api('get_guild', guild_id=entity.entity_id)
            url = guild_data.icon
        elif entity.entity_type == SupportedTarget.qqguild_user.value:
            guild_user_data = await self.bot.call_api(
                'get_member', guild_id=entity.parent_id, user_id=entity.entity_id
            )
            url = guild_user_data.user.avatar
        else:
            raise ValueError(f'entity type {entity.entity_type!r} not support')

        return url


@register_builder(adapter_name=SupportedPlatform.qqguild.value)
class QQGuildMessageBuilder(MessageBuilder):
    """QQGuild 消息构造器"""

    @staticmethod
    def _construct(message: OmegaMessage) -> Iterable[QQGuildMessageSegment]:

        def _iter_message(msg: OmegaMessage) -> Iterable[Tuple[str, dict]]:
            for seg in msg:
                yield seg.type, seg.data

        for type_, data in _iter_message(message):
            match type_:
                case MessageSegmentType.at.value:
                    yield QQGuildMessageSegment.mention_user(user_id=data.get('user_id'))
                case MessageSegmentType.forward_id.value:
                    yield QQGuildMessageSegment.reference(reference=data.get('id'))
                case MessageSegmentType.image.value:
                    url = data.get('url')
                    if urlparse(url).scheme not in ['http', 'https']:
                        yield QQGuildMessageSegment.file_image(data=Path(url))
                    else:
                        yield QQGuildMessageSegment.image(url=url)
                case MessageSegmentType.text.value:
                    yield QQGuildMessageSegment.text(content=data.get('text'))
                case _:
                    pass

    def _build(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment]) -> QQGuildMessage:
        _msg = QQGuildMessage()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return QQGuildMessage(message)
        elif isinstance(message, OmegaMessageSegment):
            return QQGuildMessage(self._construct(OmegaMessage(message)))
        elif isinstance(message, OmegaMessage):
            return QQGuildMessage(self._construct(message))
        else:
            return QQGuildMessage(message)


@register_extractor(adapter_name=SupportedPlatform.qqguild.value)
class QQGuildMessageExtractor(MessageExtractor):
    """QQGuild 消息解析器"""

    @staticmethod
    def _construct(message: QQGuildMessage) -> Iterable[OmegaMessageSegment]:

        def _iter_message(msg: QQGuildMessage) -> Iterable[Tuple[str, dict]]:
            for seg in msg:
                yield seg.type, seg.data

        for type_, data in _iter_message(message):
            match type_:
                case 'mention_user':
                    yield OmegaMessageSegment.at(user_id=data.get('user_id'))
                case 'reference':
                    yield OmegaMessageSegment.forward_id(id_=data.get('reference', {}).get('message_id'))
                case 'attachment':
                    url = 'https://' + str(data.get('url')).removeprefix('http://').removeprefix('https://')
                    yield OmegaMessageSegment.image(url=url)
                case 'text':
                    yield OmegaMessageSegment.text(text=data.get('text'))
                case _:
                    pass

    def _build(self, message: Union[str, None, QQGuildMessage, QQGuildMessageSegment]) -> OmegaMessage:
        _msg = OmegaMessage()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return OmegaMessage(message)
        elif isinstance(message, QQGuildMessageSegment):
            return OmegaMessage(self._construct(QQGuildMessage(message)))
        elif isinstance(message, QQGuildMessage):
            return OmegaMessage(self._construct(message))
        else:
            return OmegaMessage(message)


class QQGuildMessageSender(MessageSender):
    """QQGuild 消息 Sender"""

    @classmethod
    def get_builder(cls) -> Type[MessageBuilder]:
        return QQGuildMessageBuilder

    @classmethod
    def get_extractor(cls) -> Type[MessageExtractor]:
        return QQGuildMessageExtractor

    def construct_multi_msgs(self, messages: Iterable[Union[str, None, QQGuildMessage, QQGuildMessageSegment]]):
        send_message = QQGuildMessage()

        for message in messages:
            if isinstance(message, (str, QQGuildMessageSegment)):
                send_message.append(message)
            elif isinstance(message, QQGuildMessage):
                send_message.extend(message)
            else:
                pass

        return send_message

    def to_send_msg(self) -> SenderParams:
        raise NotImplementedError

    def to_send_multi_msgs(self) -> SenderParams:
        raise NotImplementedError

    def parse_revoke_sent_params(self, content: Any) -> RevokeParams:
        raise NotImplementedError


@register_sender(target_entity=SupportedTarget.qqguild_channel.value)
class QQGuildChannelMessageSender(QQGuildMessageSender):
    """QQGuild 子频道消息 Sender"""

    def to_send_msg(self) -> SenderParams:
        return SenderParams(
            api='send_to',
            message_param_name='message',
            params={
                'channel_id': self.target_entity.entity_id
            }
        )

    def to_send_multi_msgs(self) -> SenderParams:
        return self.to_send_msg()

    def parse_revoke_sent_params(self, content: Any) -> RevokeParams:
        return RevokeParams(
            api='delete_message',  # Patched
            params={'channel_id': content['channel_id'], 'message_id': content['id']}
        )


@register_sender(target_entity=SupportedTarget.qqguild_user.value)
class QQGuildChannelMessageSender(QQGuildMessageSender):
    """QQGuild 子频道消息 Sender"""

    def to_send_msg(self) -> SenderParams:
        return SenderParams(
            api='send_to_dms',  # Patched
            message_param_name='message',
            params={
                'guild_id': self.target_entity.parent_id
            }
        )

    def to_send_multi_msgs(self) -> SenderParams:
        return self.to_send_msg()


@register_event_handler(event=QQGuildMessageEvent)
class QQGuildMessageEventHandler(EventHandler):
    """QQGuild 消息事件处理器"""

    def get_user_nickname(self) -> str:
        self.event = cast(QQGuildMessageEvent, self.event)
        return self.event.author.username

    async def send_at_sender(self, message: Union[str, None, QQGuildMessage, QQGuildMessageSegment], **kwargs):
        self.event = cast(QQGuildMessageEvent, self.event)
        message = QQGuildMessageSegment.mention_user(user_id=self.event.author.id) + message
        return await self.bot.send(event=self.event, message=message, **kwargs)

    async def send_reply(self, message: Union[str, None, QQGuildMessage, QQGuildMessageSegment], **kwargs):
        self.event = cast(QQGuildMessageEvent, self.event)
        message_reference = MessageReference(message_id=self.event.id)
        return await self.bot.send(event=self.event, message=message, message_reference=message_reference, **kwargs)


@register_entity_depend(event=QQGuildEvent)
class TelegramEventEntityDepend(EntityDepend):
    """Telegram 事件 Entity 对象依赖类"""

    @classmethod
    def extract_event_entity_from_event(cls, bot: QQGuildBot, event: QQGuildEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qqguild_user', entity_id=bot.self_id, parent_id=bot.self_id
        )

    @classmethod
    def extract_user_entity_from_event(cls, bot: QQGuildBot, event: QQGuildEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qqguild_user', entity_id=bot.self_id, parent_id=bot.self_id
        )


@register_entity_depend(event=QQGuildMessageEvent)
class QQGuildMessageEventEntityDepend(EntityDepend):
    """QQGuild 频道消息事件 Entity 对象依赖类"""

    @classmethod
    def extract_event_entity_from_event(cls, bot: QQGuildBot, event: QQGuildMessageEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qqguild_channel',
            entity_id=str(event.channel_id), parent_id=str(event.guild_id)
        )

    @classmethod
    def extract_user_entity_from_event(cls, bot: QQGuildBot, event: QQGuildMessageEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qqguild_user',
            entity_id=str(event.author.id), parent_id=str(event.guild_id),
            entity_name=event.author.username, entity_info=event.author.avatar
        )


__all__ = []
