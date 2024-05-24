"""
@Author         : Ailitonia
@Date           : 2023/8/12 21:28
@FileName       : qq
@Project        : nonebot2_miya
@Description    : QQ 官方协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pathlib import Path
from typing import Any, Iterable, Tuple, Type, Union, Optional, cast
from urllib.parse import urlparse

from nonebot.matcher import current_event

from nonebot.adapters.qq import (
    Bot as QQBot,
    Message as QQMessage,
    MessageSegment as QQMessageSegment,
    Event as QQEvent,
    GuildMessageEvent as QQGuildMessageEvent
)
from nonebot.adapters.qq.models import MessageReference, Message

from ..const import SupportedPlatform, SupportedTarget
from ..register import PlatformRegister
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


@PlatformRegister.api_caller.register(SupportedPlatform.qq.value)
class QQApiCaller(ApiCaller):
    """QQ 官方适配器 API 调用适配"""

    async def get_name(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        if id_ is not None:
            raise ValueError('id param not support ')

        if entity.entity_type == SupportedTarget.qq_guild.value:
            guild_data = await self.bot.call_api('get_guild', guild_id=entity.entity_id)
            entity_name = guild_data.name
        elif entity.entity_type == SupportedTarget.qq_channel.value:
            channel_data = await self.bot.call_api('get_channel', channel_id=entity.entity_id)
            entity_name = channel_data.name
        elif entity.entity_type == SupportedTarget.qq_guild_user.value:
            guild_user_data = await self.bot.call_api(
                'get_member', guild_id=entity.parent_id, user_id=entity.entity_id
            )
            entity_name = guild_user_data.nick
        else:
            raise ValueError(f'entity type {entity.entity_type!r} not support')

        return entity_name

    async def get_profile_photo_url(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        if entity.entity_type == SupportedTarget.qq_guild.value:
            guild_data = await self.bot.call_api('get_guild', guild_id=entity.entity_id)
            url = guild_data.icon
        elif entity.entity_type == SupportedTarget.qq_guild_user.value:
            guild_user_data = await self.bot.call_api(
                'get_member', guild_id=entity.parent_id, user_id=entity.entity_id
            )
            url = guild_user_data.user.avatar
        else:
            raise ValueError(f'entity type {entity.entity_type!r} not support')

        return url


@PlatformRegister.message_builder.register(SupportedPlatform.qq.value)
class QQMessageBuilder(MessageBuilder):
    """QQ 官方适配器消息构造器"""

    @staticmethod
    def _construct(message: OmegaMessage) -> Iterable[QQMessageSegment]:

        def _iter_message(msg: OmegaMessage) -> Iterable[Tuple[str, dict]]:
            for seg in msg:
                yield seg.type, seg.data

        for type_, data in _iter_message(message):
            match type_:
                case MessageSegmentType.at.value:
                    yield QQMessageSegment.mention_user(user_id=data.get('user_id'))
                case MessageSegmentType.forward_id.value:
                    yield QQMessageSegment.reference(reference=data.get('id'))
                case MessageSegmentType.image.value:
                    url = data.get('url')
                    if urlparse(url).scheme not in ['http', 'https']:
                        yield QQMessageSegment.file_image(data=Path(url))
                    else:
                        yield QQMessageSegment.image(url=url)
                case MessageSegmentType.image_file.value:
                    yield QQMessageSegment.file_image(data=Path(data.get('file')))
                case MessageSegmentType.text.value:
                    yield QQMessageSegment.text(content=data.get('text'))
                case _:
                    pass

    def _build(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment]) -> QQMessage:
        _msg = QQMessage()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return QQMessage(message)
        elif isinstance(message, OmegaMessageSegment):
            return QQMessage(self._construct(OmegaMessage(message)))
        elif isinstance(message, OmegaMessage):
            return QQMessage(self._construct(message))
        else:
            return QQMessage(message)


@PlatformRegister.message_extractor.register(SupportedPlatform.qq.value)
class QQMessageExtractor(MessageExtractor):
    """QQ 官方适配器消息解析器"""

    @staticmethod
    def _construct(message: QQMessage) -> Iterable[OmegaMessageSegment]:

        def _iter_message(msg: QQMessage) -> Iterable[Tuple[str, dict]]:
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

    def _build(self, message: Union[str, None, QQMessage, QQMessageSegment]) -> OmegaMessage:
        _msg = OmegaMessage()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return OmegaMessage(message)
        elif isinstance(message, QQMessageSegment):
            return OmegaMessage(self._construct(QQMessage(message)))
        elif isinstance(message, QQMessage):
            return OmegaMessage(self._construct(message))
        else:
            return OmegaMessage(message)


class QQMessageSender(MessageSender):
    """QQ 官方适配器消息 Sender"""

    @classmethod
    def get_builder(cls) -> Type[MessageBuilder]:
        return QQMessageBuilder

    @classmethod
    def get_extractor(cls) -> Type[MessageExtractor]:
        return QQMessageExtractor

    def construct_multi_msgs(self, messages: Iterable[Union[str, None, QQMessage, QQMessageSegment]]):
        send_message = QQMessage()

        for message in messages:
            if isinstance(message, (str, QQMessageSegment)):
                send_message.append(message)
            elif isinstance(message, QQMessage):
                send_message.extend(message)
            else:
                pass

        return send_message

    def to_send_msg(self, **kwargs) -> SenderParams:
        raise NotImplementedError

    def to_send_multi_msgs(self, **kwargs) -> SenderParams:
        raise NotImplementedError

    def parse_revoke_sent_params(self, content: Any, **kwargs) -> RevokeParams:
        raise NotImplementedError


@PlatformRegister.message_sender.register(SupportedTarget.qq_channel.value)
class QQChannelMessageSender(QQMessageSender):
    """QQ 官方适配器子频道消息 Sender"""

    def to_send_msg(self, **kwargs) -> SenderParams:
        params = {'channel_id': self.target_entity.entity_id}
        if 'msg_id' in kwargs:
            params['msg_id'] = kwargs['msg_id']
        else:
            try:
                # 尝试从 event 上下文中提取 msg_id
                event = current_event.get()
                msg_id = getattr(event, 'id', None)
                if msg_id is not None:
                    params['msg_id'] = msg_id
            except LookupError:
                pass

        return SenderParams(
            api='send_to_channel',
            message_param_name='message',
            params=params
        )

    def to_send_multi_msgs(self, **kwargs) -> SenderParams:
        return self.to_send_msg(**kwargs)

    def parse_revoke_sent_params(self, content: Any, **kwargs) -> RevokeParams:
        if isinstance(content, Message):
            content = content.model_dump()
        return RevokeParams(
            api='delete_message',  # Patched
            params={'channel_id': content['channel_id'], 'message_id': content['id']}
        )


@PlatformRegister.message_sender.register(SupportedTarget.qq_guild_user.value)
class QQGuildUserMessageSender(QQMessageSender):
    """QQ 官方适配器频道用户私聊消息 Sender"""

    def to_send_msg(self, **kwargs) -> SenderParams:
        params = {'guild_id': self.target_entity.parent_id}
        if 'msg_id' in kwargs:
            params['msg_id'] = kwargs['msg_id']
        else:
            try:
                # 尝试从 event 上下文中提取 msg_id
                event = current_event.get()
                msg_id = getattr(event, 'id', None)
                if msg_id is not None:
                    params['msg_id'] = msg_id
            except LookupError:
                pass

        return SenderParams(
            api='send_to_dms',  # Patched
            message_param_name='message',
            params=params
        )

    def to_send_multi_msgs(self, **kwargs) -> SenderParams:
        return self.to_send_msg(**kwargs)


@PlatformRegister.event_handler.register(QQGuildMessageEvent)
class QQGuildMessageEventHandler(EventHandler):
    """QQ 官方适配器 Guild 消息事件处理器"""

    def get_user_nickname(self) -> str:
        self.event = cast(QQGuildMessageEvent, self.event)
        return self.event.author.username

    def get_msg_image_urls(self) -> list[str]:
        return [str(msg_seg.data.get('url')) for msg_seg in self.event.get_message() if msg_seg.type == 'image']

    def get_reply_msg_image_urls(self) -> list[str]:
        if self.event.reply:
            return [
                str(msg_seg.data.get('url'))
                for msg_seg in QQMessage.from_guild_message(self.event.reply)
                if msg_seg.type == 'image'
            ]
        else:
            return []

    def get_reply_msg_plain_text(self) -> Optional[str]:
        if self.event.reply:
            return QQMessage.from_guild_message(self.event.reply).extract_plain_text()
        else:
            return None

    async def send_at_sender(self, message: Union[str, None, QQMessage, QQMessageSegment], **kwargs):
        self.event = cast(QQGuildMessageEvent, self.event)
        message = QQMessageSegment.mention_user(user_id=self.event.author.id) + message
        return await self.bot.send(event=self.event, message=message, **kwargs)

    async def send_reply(self, message: Union[str, None, QQMessage, QQMessageSegment], **kwargs):
        self.event = cast(QQGuildMessageEvent, self.event)
        message = QQMessageSegment.reference(reference=MessageReference(message_id=self.event.id)) + message
        return await self.bot.send(event=self.event, message=message, **kwargs)


@PlatformRegister.entity_depend.register(QQEvent)
class QQEventEntityDepend(EntityDepend):
    """QQ 官方适配器事件 Entity 对象依赖类"""

    @classmethod
    def extract_event_entity_from_event(cls, bot: QQBot, event: QQEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qq_user', entity_id=bot.self_id, parent_id=bot.self_id
        )

    @classmethod
    def extract_user_entity_from_event(cls, bot: QQBot, event: QQEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qq_user', entity_id=bot.self_id, parent_id=bot.self_id
        )


@PlatformRegister.entity_depend.register(QQGuildMessageEvent)
class QQGuildMessageEventEntityDepend(EntityDepend):
    """QQ 官方适配器频道消息事件 Entity 对象依赖类"""

    @classmethod
    def extract_event_entity_from_event(cls, bot: QQBot, event: QQGuildMessageEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qq_channel',
            entity_id=str(event.channel_id), parent_id=str(event.guild_id)
        )

    @classmethod
    def extract_user_entity_from_event(cls, bot: QQBot, event: QQGuildMessageEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qq_guild_user',
            entity_id=str(event.author.id), parent_id=str(event.guild_id),
            entity_name=event.author.username, entity_info=event.author.avatar
        )


__all__ = []
