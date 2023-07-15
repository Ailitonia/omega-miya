"""
@Author         : Ailitonia
@Date           : 2023/6/10 1:32
@FileName       : onebot_v11
@Project        : nonebot2_miya
@Description    : OneBot V11 协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pathlib import Path
from typing import Any, Iterable, Tuple, Type, Union, Optional, cast
from urllib.parse import urlparse

from nonebot.adapters.onebot.v11 import (
    Bot as OnebotV11Bot,
    Message as OnebotV11Message,
    MessageSegment as OnebotV11MessageSegment,
    Event as OnebotV11Event,
    MessageEvent as OnebotV11MessageEvent,
    GroupMessageEvent as OnebotV11GroupMessageEvent,
    PrivateMessageEvent as OnebotV11PrivateMessageEvent,
)

from src.service.gocqhttp_guild_patch import (
    GuildMessageEvent as OnebotV11GuildMessageEvent
)

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


@register_api_caller(adapter_name=SupportedPlatform.onebot_v11.value)
class OnebotV11ApiCaller(ApiCaller):
    """OneBot V11 API 调用适配"""

    async def get_name(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        if id_ is not None:
            raise ValueError('id param not support ')

        if entity.entity_type == SupportedTarget.qq_user.value:
            user_data = await self.bot.call_api('get_stranger_info', user_id=entity.entity_id)
            entity_name = user_data.get('nickname', '')
        elif entity.entity_type == SupportedTarget.qq_group.value:
            group_data = await self.bot.call_api('get_group_info', group_id=entity.entity_id)
            entity_name = group_data.get('group_name', '')
        elif entity.entity_type == SupportedTarget.qq_guild.value:
            guild_data = await self.bot.call_api('get_guild_meta_by_guest', guild_id=entity.entity_id)
            entity_name = guild_data.get('guild_name', '')
        elif entity.entity_type == SupportedTarget.qq_guild_user:
            guild_user_data = await self.bot.call_api('get_guild_member_profile',
                                                      guild_id=entity.parent_id, user_id=entity.entity_id)
            entity_name = guild_user_data.get('nickname', '')
        else:
            raise ValueError(f'entity type {entity.entity_type!r} not support')

        return entity_name

    async def get_profile_photo_url(self, entity: OmegaEntity, id_: Optional[Union[int, str]] = None) -> str:
        if entity.entity_type != SupportedTarget.qq_user.value:
            raise ValueError(f'entity type {entity.entity_type!r} not support')

        # head_img_size: 1: 40×40px, 2: 40×40px, 3: 100×100px, 4: 140×140px, 5: 640×640px, 40: 40×40px, 100: 100×100px
        head_img_size = 5
        url_version = 0

        user_qq = id_ if id_ is not None else entity.entity_id

        match url_version:
            case 2:
                url = f'https://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={user_qq}'
            case 1:
                url = f'https://q2.qlogo.cn/headimg_dl?dst_uin={user_qq}&spec={head_img_size}'
            case 0 | _:
                url = f'https://q1.qlogo.cn/g?b=qq&nk={user_qq}&s={head_img_size}'
        return url


@register_builder(adapter_name=SupportedPlatform.onebot_v11.value)
class OnebotV11MessageBuilder(MessageBuilder):
    """OneBot V11 消息构造器"""

    @staticmethod
    def _construct(message: OmegaMessage) -> Iterable[OnebotV11MessageSegment]:

        def _iter_message(msg: OmegaMessage) -> Iterable[Tuple[str, dict]]:
            for seg in msg:
                yield seg.type, seg.data

        for type_, data in _iter_message(message):
            match type_:
                case MessageSegmentType.at.value:
                    yield OnebotV11MessageSegment.at(user_id=data.get('user_id'))
                case MessageSegmentType.forward_id.value:
                    yield OnebotV11MessageSegment.node(id_=data.get('id'))
                case MessageSegmentType.custom_node.value:
                    yield OnebotV11MessageSegment.node_custom(
                        user_id=data.get('user_id'), nickname=data.get('nickname'), content=data.get('content')
                    )
                case MessageSegmentType.image.value:
                    url = data.get('url')
                    if urlparse(url).scheme not in ['http', 'https']:
                        url = Path(url)
                    yield OnebotV11MessageSegment.image(file=url)
                case MessageSegmentType.text.value:
                    yield OnebotV11MessageSegment.text(text=data.get('text'))
                case _:
                    pass

    def _build(self, message: Union[str, None, OmegaMessage, OmegaMessageSegment]) -> OnebotV11Message:
        _msg = OnebotV11Message()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return OnebotV11Message(message)
        elif isinstance(message, OmegaMessageSegment):
            return OnebotV11Message(self._construct(OmegaMessage(message)))
        elif isinstance(message, OmegaMessage):
            return OnebotV11Message(self._construct(message))
        else:
            return OnebotV11Message(message)


@register_extractor(adapter_name=SupportedPlatform.onebot_v11.value)
class OnebotV11MessageExtractor(MessageExtractor):
    """OneBot V11 消息解析器"""

    @staticmethod
    def _construct(message: OnebotV11Message) -> Iterable[OmegaMessageSegment]:

        def _iter_message(msg: OnebotV11Message) -> Iterable[Tuple[str, dict]]:
            for seg in msg:
                yield seg.type, seg.data

        for type_, data in _iter_message(message):
            match type_:
                case 'at':
                    yield OmegaMessageSegment.at(user_id=data.get('qq'))
                case 'forward':
                    yield OmegaMessageSegment.forward_id(id_=data.get('id'))
                case 'node':
                    yield OmegaMessageSegment.custom_node(
                        user_id=data.get('user_id'), nickname=data.get('nickname'), content=data.get('content')
                    )
                case 'image':
                    url = data.get('url') if data.get('url') else data.get('file')
                    if urlparse(url).scheme not in ['http', 'https']:
                        url = Path(url)
                    yield OmegaMessageSegment.image(url=url)
                case 'text':
                    yield OmegaMessageSegment.text(text=data.get('text'))
                case _:
                    pass

    def _build(self, message: Union[str, None, OnebotV11Message, OnebotV11MessageSegment]) -> OmegaMessage:
        _msg = OmegaMessage()
        if message is None:
            return _msg
        elif isinstance(message, str):
            return OmegaMessage(message)
        elif isinstance(message, OnebotV11MessageSegment):
            return OmegaMessage(self._construct(OnebotV11Message(message)))
        elif isinstance(message, OnebotV11Message):
            return OmegaMessage(self._construct(message))
        else:
            return OmegaMessage(message)


class OnebotV11MessageSender(MessageSender):
    """OneBot V11 消息 Sender"""

    @classmethod
    def get_builder(cls) -> Type[MessageBuilder]:
        return OnebotV11MessageBuilder

    @classmethod
    def get_extractor(cls) -> Type[MessageExtractor]:
        return OnebotV11MessageExtractor

    def construct_multi_msgs(self, messages: Iterable[Union[str, None, OnebotV11Message, OnebotV11MessageSegment]]):
        custom_nickname = 'Ωμεγα_Μιγα'
        custom_user_id = int(self.target_entity.bot_id)
        send_message = OnebotV11Message()

        for message in messages:
            if isinstance(message, (str, OnebotV11Message, OnebotV11MessageSegment)):
                send_message.append(OnebotV11MessageSegment.node_custom(
                    user_id=custom_user_id, nickname=custom_nickname, content=message
                ))
            else:
                pass

        return send_message

    def to_send_msg(self) -> SenderParams:
        raise NotImplementedError

    def to_send_multi_msgs(self) -> SenderParams:
        raise NotImplementedError

    def parse_revoke_sent_params(self, content: Any) -> RevokeParams:
        return RevokeParams(api='delete_msg', params={'message_id': content["message_id"]})


@register_sender(target_entity=SupportedTarget.qq_user.value)
class OnebotV11QQUserMessageSender(OnebotV11MessageSender):
    """OneBot V11 QQ 用户消息 Sender"""

    def to_send_msg(self) -> SenderParams:
        return SenderParams(
            api='send_private_msg',
            message_param_name='message',
            params={
                'user_id': self.target_entity.entity_id
            }
        )

    def to_send_multi_msgs(self) -> SenderParams:
        return SenderParams(
            api='send_private_forward_msg',
            message_param_name='messages',
            params={
                'user_id': self.target_entity.entity_id
            }
        )


@register_sender(target_entity=SupportedTarget.qq_group.value)
class OnebotV11QQGroupMessageSender(OnebotV11MessageSender):
    """OneBot V11 QQ 群组消息 Sender"""

    def to_send_msg(self) -> SenderParams:
        return SenderParams(
            api='send_group_msg',
            message_param_name='message',
            params={
                'group_id': self.target_entity.entity_id
            }
        )

    def to_send_multi_msgs(self) -> SenderParams:
        return SenderParams(
            api='send_group_forward_msg',
            message_param_name='messages',
            params={
                'group_id': self.target_entity.entity_id
            }
        )


@register_sender(target_entity=SupportedTarget.qq_guild_channel.value)
class OnebotV11QQGuildChannelMessageSender(OnebotV11MessageSender):
    """OneBot V11 QQ 子频道消息 Sender"""

    def to_send_msg(self) -> SenderParams:
        return SenderParams(
            api='send_guild_channel_msg',
            message_param_name='message',
            params={
                'guild_id': self.target_entity.parent_id,
                'channel_id': self.target_entity.entity_id
            }
        )

    def to_send_multi_msgs(self) -> SenderParams:
        return self.to_send_msg()


@register_event_handler(event=OnebotV11MessageEvent)
class OnebotV11MessageEventHandler(EventHandler):
    """OneBot V11 消息事件处理器"""

    def get_user_nickname(self) -> str:
        return self.event.sender.card if self.event.sender.card else self.event.sender.nickname

    async def send_at_sender(self, message: Union[str, None, OnebotV11Message, OnebotV11MessageSegment], **kwargs):
        self.event = cast(OnebotV11MessageEvent, self.event)
        return await self.bot.send(event=self.event, message=message, at_sender=True, **kwargs)

    async def send_reply(self, message: Union[str, None, OnebotV11Message, OnebotV11MessageSegment], **kwargs):
        self.event = cast(OnebotV11MessageEvent, self.event)
        return await self.bot.send(event=self.event, message=message, reply_message=True, **kwargs)


@register_entity_depend(event=OnebotV11Event)
class OnebotV11EventEntityDepend(EntityDepend):
    """OneBot V11 事件 Entity 对象依赖类"""

    @classmethod
    def extract_event_entity_from_event(cls, bot: OnebotV11Bot, event: OnebotV11Event) -> EntityParams:
        bot_id = bot.self_id
        parent_id = bot.self_id

        if group_id := getattr(event, 'group_id', None):
            entity_type = 'qq_group'
            entity_id = str(group_id)
        elif (guild_id := getattr(event, 'guild_id', None)) and (channel_id := getattr(event, 'channel_id', None)):
            entity_type = 'qq_guild_channel'
            entity_id = str(channel_id)
            parent_id = str(guild_id)
        elif user_id := getattr(event, 'user_id', None):
            entity_type = 'qq_user'
            entity_id = str(user_id)
        else:
            entity_type = 'qq_user'
            entity_id = bot.self_id

        return EntityParams(bot_id=bot_id, entity_type=entity_type, entity_id=entity_id, parent_id=parent_id)

    @classmethod
    def extract_user_entity_from_event(cls, bot: OnebotV11Bot, event: OnebotV11Event) -> EntityParams:
        bot_id = bot.self_id
        parent_id = bot.self_id

        if user_id := getattr(event, 'user_id', None):
            entity_type = 'qq_user'
            entity_id = str(user_id)
        else:
            entity_type = 'qq_user'
            entity_id = bot.self_id

        return EntityParams(bot_id=bot_id, entity_type=entity_type, entity_id=entity_id, parent_id=parent_id)


@register_entity_depend(event=OnebotV11GroupMessageEvent)
class OnebotV11GroupMessageEventEntityDepend(EntityDepend):
    """OneBot V11 群消息事件 Entity 对象依赖类"""

    @classmethod
    def extract_event_entity_from_event(cls, bot: OnebotV11Bot, event: OnebotV11GroupMessageEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qq_group', entity_id=str(event.group_id), parent_id=bot.self_id
        )

    @classmethod
    def extract_user_entity_from_event(cls, bot: OnebotV11Bot, event: OnebotV11GroupMessageEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qq_user', entity_id=str(event.user_id), parent_id=bot.self_id,
            entity_name=event.sender.nickname, entity_info=event.sender.card
        )


@register_entity_depend(event=OnebotV11PrivateMessageEvent)
class OnebotV11PrivateMessageEventEntityDepend(EntityDepend):
    """OneBot V11 私聊消息事件 Entity 对象依赖类"""

    @classmethod
    def extract_event_entity_from_event(cls, bot: OnebotV11Bot, event: OnebotV11PrivateMessageEvent) -> EntityParams:
        return cls.extract_user_entity_from_event(bot=bot, event=event)

    @classmethod
    def extract_user_entity_from_event(cls, bot: OnebotV11Bot, event: OnebotV11PrivateMessageEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qq_user', entity_id=str(event.user_id), parent_id=bot.self_id,
            entity_name=event.sender.nickname, entity_info=event.sender.card
        )


@register_entity_depend(event=OnebotV11GuildMessageEvent)
class OnebotV11GuildMessageEventEntityDepend(EntityDepend):
    """OneBot V11 频道消息事件 Entity 对象依赖类"""

    @classmethod
    def extract_event_entity_from_event(cls, bot: OnebotV11Bot, event: OnebotV11GuildMessageEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qq_guild_channel',
            entity_id=str(event.channel_id), parent_id=str(event.guild_id)
        )

    @classmethod
    def extract_user_entity_from_event(cls, bot: OnebotV11Bot, event: OnebotV11GuildMessageEvent) -> EntityParams:
        return EntityParams(
            bot_id=bot.self_id, entity_type='qq_guild_user',
            entity_id=str(event.user_id), parent_id=str(event.guild_id),
            entity_name=event.sender.nickname, entity_info=event.sender.card
        )


__all__ = []
