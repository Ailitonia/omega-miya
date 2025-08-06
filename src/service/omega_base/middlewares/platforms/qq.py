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
from typing import Any
from urllib.parse import urlparse

from nonebot.adapters.qq import Bot as QQBot
from nonebot.adapters.qq import C2CMessageCreateEvent as QQC2CMessageCreateEvent
from nonebot.adapters.qq import Event as QQEvent
from nonebot.adapters.qq import GroupAtMessageCreateEvent as QQGroupAtMessageCreateEvent
from nonebot.adapters.qq import (
    GuildMessageEvent as QQGuildMessageEvent,  # DirectMessageCreateEvent 是 GuildMessageEvent 的子类, 直接共用相同逻辑
)
from nonebot.adapters.qq import Message as QQMessage
from nonebot.adapters.qq import MessageSegment as QQMessageSegment
from nonebot.adapters.qq.models import Message, MessageReference
from nonebot.matcher import current_event

from ..const import SupportedPlatform, SupportedTarget
from ..models import EntityInitParams, EntityTargetRevokeParams, EntityTargetSendParams, SentMessageResponse
from ..platform_interface.entity_target import BaseEntityTarget, entity_target_register
from ..platform_interface.event_depend import BaseEventDepend, event_depend_register
from ..platform_interface.message_builder import BaseMessageBuilder, message_builder_register
from ..typing import BaseSentMessageType
from ...message import Message as OmegaMessage
from ...message import MessageSegment as OmegaMessageSegment
from ...message import MessageSegmentType


@message_builder_register.register_builder(SupportedPlatform.qq)
class QQMessageBuilder(BaseMessageBuilder[OmegaMessage, QQMessage]):

    @staticmethod
    def _get_source_base_segment_type() -> type[OmegaMessageSegment]:
        return OmegaMessageSegment

    @staticmethod
    def _get_target_base_segment_type() -> type[QQMessageSegment]:
        return QQMessageSegment

    @staticmethod
    def _construct_platform_segment(seg_type: str, seg_data: dict[str, Any]) -> QQMessageSegment:
        match seg_type:
            case MessageSegmentType.at:
                return QQMessageSegment.mention_user(user_id=seg_data.get('user_id', ''))
            case MessageSegmentType.at_all:
                return QQMessageSegment.mention_everyone()
            case MessageSegmentType.emoji:
                return QQMessageSegment.emoji(id=seg_data.get('id', '0'))
            case MessageSegmentType.audio | MessageSegmentType.voice:
                file = _parse_url_to_path(str(seg_data.get('url', '')))
                if isinstance(file, Path):
                    return QQMessageSegment.file_audio(data=file)
                return QQMessageSegment.audio(url=file)
            case MessageSegmentType.video:
                file = _parse_url_to_path(str(seg_data.get('url', '')))
                if isinstance(file, Path):
                    return QQMessageSegment.file_video(data=file)
                return QQMessageSegment.video(url=file)
            case MessageSegmentType.image:
                file = _parse_url_to_path(str(seg_data.get('url', '')))
                if isinstance(file, Path):
                    return QQMessageSegment.file_image(data=file)
                return QQMessageSegment.image(url=file)
            case MessageSegmentType.image_file:
                return QQMessageSegment.file_image(data=Path(seg_data.get('file', '')))
            case MessageSegmentType.file:
                return QQMessageSegment.file_file(data=Path(seg_data.get('file', '')))
            case MessageSegmentType.reply:
                return QQMessageSegment.reference(reference=seg_data.get('id', ''))
            case MessageSegmentType.text:
                return QQMessageSegment.text(content=seg_data.get('text', ''))
            case _:
                return QQMessageSegment.text(content='')


@message_builder_register.register_extractor(SupportedPlatform.qq)
class QQMessageExtractor(BaseMessageBuilder[QQMessage, OmegaMessage]):
    """QQ 官方适配器消息解析器"""

    @staticmethod
    def _get_source_base_segment_type() -> type[QQMessageSegment]:
        return QQMessageSegment

    @staticmethod
    def _get_target_base_segment_type() -> type[OmegaMessageSegment]:
        return OmegaMessageSegment

    @staticmethod
    def _construct_platform_segment(seg_type: str, seg_data: dict[str, Any]) -> OmegaMessageSegment:
        match seg_type:
            case 'mention_user':
                return OmegaMessageSegment.at(user_id=seg_data.get('user_id', ''))
            case 'mention_everyone':
                return OmegaMessageSegment.at_all()
            case 'emoji':
                return OmegaMessageSegment.emoji(id_=seg_data.get('id', ''))
            case 'audio':
                url = 'https://' + str(seg_data.get('url')).removeprefix('http://').removeprefix('https://')
                return OmegaMessageSegment.audio(url=url)
            case 'video':
                url = 'https://' + str(seg_data.get('url')).removeprefix('http://').removeprefix('https://')
                return OmegaMessageSegment.video(url=url)
            case 'image':
                url = 'https://' + str(seg_data.get('url')).removeprefix('http://').removeprefix('https://')
                return OmegaMessageSegment.image(url=url)
            case 'reference':
                return OmegaMessageSegment.reply(id_=seg_data.get('reference', {}).get('message_id'))
            case 'text':
                return OmegaMessageSegment.text(text=seg_data.get('text', ''))
            case _:
                return OmegaMessageSegment.other(type_=seg_type, data=seg_data)


@entity_target_register.register_target(SupportedTarget.qq_guild)
class QQGuildEntityTarget(BaseEntityTarget):

    def extract_sent_message_api_response(self, response: Any) -> 'SentMessageResponse':
        raise NotImplementedError

    def get_api_to_send_msg(self, **kwargs) -> 'EntityTargetSendParams':
        raise NotImplementedError

    def get_api_to_revoke_msgs(self, sent_return: 'SentMessageResponse', **kwargs) -> 'EntityTargetRevokeParams':
        raise NotImplementedError

    async def call_api_get_entity_name(self) -> str:
        bot = await self.get_bot()
        guild_data = await bot.call_api('get_guild', guild_id=self.entity.entity_id)
        entity_name = getattr(guild_data, 'name', '')
        return str(entity_name)

    async def call_api_get_entity_profile_image_url(self) -> str:
        bot = await self.get_bot()
        guild_data = await bot.call_api('get_guild', guild_id=self.entity.entity_id)
        url = getattr(guild_data, 'icon', '')
        return str(url)

    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        raise NotImplementedError


@entity_target_register.register_target(SupportedTarget.qq_channel)
class QQChannelEntityTarget(BaseEntityTarget):

    def extract_sent_message_api_response(self, response: Any) -> 'SentMessageResponse':
        if not isinstance(response, Message):
            raise ValueError(f'Sent message({response!r}) can not be revoked')

        return SentMessageResponse.model_validate({
            'sent_message_id': response.id,
            'bot_self_id': self.entity.bot_id,
            'target_id': response.channel_id,
            'target_type': self.entity.entity_type,
            'raw_response': response,
        })

    def get_api_to_send_msg(self, **kwargs) -> 'EntityTargetSendParams':
        params = {'channel_id': self.entity.entity_id}
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

        return EntityTargetSendParams(
            api='send_to_channel',
            message_param_name='message',
            params=params
        )

    def get_api_to_revoke_msgs(self, sent_return: 'SentMessageResponse', **kwargs) -> 'EntityTargetRevokeParams':
        return EntityTargetRevokeParams(
            api='delete_message',
            params={'channel_id': sent_return.target_id, 'message_id': sent_return.sent_message_id}
        )

    async def call_api_get_entity_name(self) -> str:
        bot = await self.get_bot()
        channel_data = await bot.call_api('get_channel', channel_id=self.entity.entity_id)
        entity_name = getattr(channel_data, 'name', '')
        return str(entity_name)

    async def call_api_get_entity_profile_image_url(self) -> str:
        raise NotImplementedError

    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        raise NotImplementedError  # TODO


@entity_target_register.register_target(SupportedTarget.qq_group)
class QQGroupEntityTarget(BaseEntityTarget):

    def extract_sent_message_api_response(self, response: Any) -> 'SentMessageResponse':
        raise NotImplementedError  # TODO

    def get_api_to_send_msg(self, **kwargs) -> 'EntityTargetSendParams':
        raise NotImplementedError  # TODO send_to_group

    def get_api_to_revoke_msgs(self, sent_return: 'SentMessageResponse', **kwargs) -> 'EntityTargetRevokeParams':
        raise NotImplementedError  # TODO

    async def call_api_get_entity_name(self) -> str:
        raise NotImplementedError  # TODO

    async def call_api_get_entity_profile_image_url(self) -> str:
        raise NotImplementedError  # TODO

    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        raise NotImplementedError  # TODO post_group_files


@entity_target_register.register_target(SupportedTarget.qq_user)
class QQUserEntityTarget(BaseEntityTarget):

    def extract_sent_message_api_response(self, response: Any) -> 'SentMessageResponse':
        raise NotImplementedError  # TODO

    def get_api_to_send_msg(self, **kwargs) -> 'EntityTargetSendParams':
        raise NotImplementedError  # TODO send_to_c2c

    def get_api_to_revoke_msgs(self, sent_return: 'SentMessageResponse', **kwargs) -> 'EntityTargetRevokeParams':
        raise NotImplementedError  # TODO

    async def call_api_get_entity_name(self) -> str:
        raise NotImplementedError  # TODO

    async def call_api_get_entity_profile_image_url(self) -> str:
        raise NotImplementedError  # TODO

    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        raise NotImplementedError  # TODO post_c2c_files


@entity_target_register.register_target(SupportedTarget.qq_guild_user)
class QQGuildUserEntityTarget(BaseEntityTarget):

    def extract_sent_message_api_response(self, response: Any) -> 'SentMessageResponse':
        if not isinstance(response, Message):
            raise ValueError(f'Sent message({response!r}) can not be revoked')

        return SentMessageResponse.model_validate({
            'sent_message_id': response.id,
            'bot_self_id': self.entity.bot_id,
            'target_id': response.guild_id,
            'target_type': self.entity.entity_type,
            'raw_response': response,
        })

    def get_api_to_send_msg(self, **kwargs) -> 'EntityTargetSendParams':
        params = {'guild_id': self.entity.parent_id}
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

        return EntityTargetSendParams(
            api='send_to_dms',
            message_param_name='message',
            params=params
        )

    def get_api_to_revoke_msgs(self, sent_return: 'SentMessageResponse', **kwargs) -> 'EntityTargetRevokeParams':
        raise NotImplementedError  # 暂不支持主动撤回 dms 私聊消息

    async def call_api_get_entity_name(self) -> str:
        bot = await self.get_bot()
        guild_user_data = await bot.call_api(
            'get_member', guild_id=self.entity.parent_id, user_id=self.entity.entity_id
        )
        entity_name = getattr(guild_user_data, 'nick', '')
        return str(entity_name)

    async def call_api_get_entity_profile_image_url(self) -> str:
        bot = await self.get_bot()
        guild_user_data = await bot.call_api(
            'get_member', guild_id=self.entity.parent_id, user_id=self.entity.entity_id
        )
        url = getattr(getattr(guild_user_data, 'user', object()), 'avatar', '')
        return str(url)

    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        raise NotImplementedError  # TODO


@event_depend_register.register_depend(QQEvent)
class QQEventDepend[Event_T: QQEvent](BaseEventDepend[QQBot, Event_T, QQMessage]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_user', entity_id=self.bot.self_id, parent_id=self.bot.self_id
        )

    def get_omega_message_builder(self) -> type['BaseMessageBuilder[OmegaMessage, QQMessage]']:
        return QQMessageBuilder

    def get_omega_message_extractor(self) -> type['BaseMessageBuilder[QQMessage, OmegaMessage]']:
        return QQMessageExtractor

    def extract_platform_sent_message_response(self, response: Any) -> 'SentMessageResponse':
        raise NotImplementedError

    async def send_at_sender(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> 'SentMessageResponse':
        raise NotImplementedError

    async def send_reply(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> 'SentMessageResponse':
        raise NotImplementedError

    async def revoke(self, sent_return: 'SentMessageResponse', **kwargs) -> Any:
        raise NotImplementedError

    def get_user_nickname(self) -> str:
        raise NotImplementedError

    def get_msg_mentioned_user_ids(self) -> list[str]:
        raise NotImplementedError

    def get_msg_image_urls(self) -> list[str]:
        raise NotImplementedError

    def get_reply_msg_id(self) -> str | None:
        raise NotImplementedError

    def get_reply_msg_image_urls(self) -> list[str]:
        raise NotImplementedError

    def get_reply_msg_plain_text(self) -> str | None:
        raise NotImplementedError


@event_depend_register.register_depend(QQGuildMessageEvent)
class QQGuildMessageEventDepend(QQEventDepend[QQGuildMessageEvent]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_channel',
            entity_id=self.event.channel_id, parent_id=self.event.guild_id
        )

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_guild_user',
            entity_id=self.event.author.id, parent_id=self.event.guild_id,
            entity_name=self.event.author.username, entity_info=self.event.author.avatar
        )

    def extract_platform_sent_message_response(self, response: Any) -> 'SentMessageResponse':
        target_entity_params = self._extract_event_entity_params()
        return SentMessageResponse.model_validate({
            'sent_message_id': response.id,
            'bot_self_id': target_entity_params.bot_id,
            'target_id': response.channel_id,
            'target_type': target_entity_params.entity_type,
            'raw_response': response,
        })

    async def send_at_sender(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> 'SentMessageResponse':
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.mention_user(user_id=self.event.author.id) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def send_reply(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> 'SentMessageResponse':
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.reference(reference=MessageReference(message_id=self.event.id)) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def revoke(self, sent_return: 'SentMessageResponse', **kwargs) -> Any:
        return await self.bot.delete_message(
            channel_id=sent_return.target_id,
            message_id=sent_return.sent_message_id,
        )

    def get_user_nickname(self) -> str:
        return self.event.author.username if self.event.author.username else ''

    def get_msg_mentioned_user_ids(self) -> list[str]:
        return [
            str(msg_seg.data.get('user_id'))
            for msg_seg in self.event.get_message()
            if msg_seg.type == 'mention_user'
        ]

    def get_msg_image_urls(self) -> list[str]:
        return [str(msg_seg.data.get('url')) for msg_seg in self.event.get_message() if msg_seg.type == 'image']

    def get_reply_msg_id(self) -> str | None:
        # `GuildMessageEvent.reply` 使用 `get_message_of_id` API 提取回复消息
        # 参考 QQ 适配器 `bot.py` 模块 `_check_reply` 方法
        # `event.reply.id` 与 `event.message_reference.message_id` 等价
        if self.event.message_reference:
            return self.event.message_reference.message_id
        else:
            return None

    def get_reply_msg_image_urls(self) -> list[str]:
        if self.event.reply:
            return [
                str(msg_seg.data.get('url'))
                for msg_seg in QQMessage.from_guild_message(self.event.reply)
                if msg_seg.type == 'image'
            ]
        else:
            return []

    def get_reply_msg_plain_text(self) -> str | None:
        if self.event.reply:
            return QQMessage.from_guild_message(self.event.reply).extract_plain_text()
        else:
            return None


@event_depend_register.register_depend(QQC2CMessageCreateEvent)
class QQC2CMessageCreateEventDepend(QQEventDepend[QQC2CMessageCreateEvent]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_user',
            entity_id=self.event.author.user_openid, parent_id=self.bot.self_id,
            entity_info=f'id: {self.event.author.id}, openid: {self.event.author.user_openid}'
        )

    def extract_platform_sent_message_response(self, response: Any) -> 'SentMessageResponse':
        target_entity_params = self._extract_event_entity_params()
        return SentMessageResponse.model_validate({
            'sent_message_id': response.id,
            'bot_self_id': target_entity_params.bot_id,
            'target_id': target_entity_params.entity_id,
            'target_type': target_entity_params.entity_type,
            'raw_response': response,
        })

    async def send_at_sender(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> 'SentMessageResponse':
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.mention_user(user_id=self.event.author.user_openid) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def send_reply(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> 'SentMessageResponse':
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.reference(reference=MessageReference(message_id=self.event.id)) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def revoke(self, sent_return: 'SentMessageResponse', **kwargs) -> Any:
        return await self.bot.delete_c2c_message(
            openid=sent_return.target_id,
            message_id=sent_return.sent_message_id,
        )

    def get_user_nickname(self) -> str:
        raise NotImplementedError  # QQ 协议只有 openid, 不支持获取用户信息

    def get_msg_mentioned_user_ids(self) -> list[str]:
        return [
            str(msg_seg.data.get('user_id'))
            for msg_seg in self.event.get_message()
            if msg_seg.type == 'mention_user'
        ]

    def get_msg_image_urls(self) -> list[str]:
        return [str(msg_seg.data.get('url')) for msg_seg in self.event.get_message() if msg_seg.type == 'image']

    def get_reply_msg_id(self) -> str | None:
        raise NotImplementedError  # NOTE: QQ API not support currently

    def get_reply_msg_image_urls(self) -> list[str]:
        raise NotImplementedError  # NOTE: QQ API not support currently

    def get_reply_msg_plain_text(self) -> str | None:
        raise NotImplementedError  # NOTE: QQ API not support currently


@event_depend_register.register_depend(QQGroupAtMessageCreateEvent)
class QQGroupAtMessageCreateEventDepend(QQEventDepend[QQGroupAtMessageCreateEvent]):

    def _extract_event_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_group',
            entity_id=self.event.group_openid, parent_id=self.bot.self_id,
            entity_info=f'group_openid: {self.event.group_openid}'
        )

    def _extract_user_entity_params(self) -> 'EntityInitParams':
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_user',
            entity_id=self.event.author.member_openid, parent_id=self.bot.self_id,
            entity_info=f'id: {self.event.author.id}, member_openid: {self.event.author.member_openid}'
        )

    def extract_platform_sent_message_response(self, response: Any) -> 'SentMessageResponse':
        target_entity_params = self._extract_event_entity_params()
        return SentMessageResponse.model_validate({
            'sent_message_id': response.id,
            'bot_self_id': target_entity_params.bot_id,
            'target_id': target_entity_params.entity_id,
            'target_type': target_entity_params.entity_type,
            'raw_response': response,
        })

    async def send_at_sender(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> 'SentMessageResponse':
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.mention_user(user_id=self.event.author.member_openid) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def send_reply(self, message: 'BaseSentMessageType[OmegaMessage]', **kwargs) -> 'SentMessageResponse':
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.reference(reference=MessageReference(message_id=self.event.id)) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def revoke(self, sent_return: 'SentMessageResponse', **kwargs) -> Any:
        return await self.bot.delete_group_message(
            group_openid=sent_return.target_id,
            message_id=sent_return.sent_message_id,
        )

    def get_user_nickname(self) -> str:
        raise NotImplementedError  # QQ 协议只有 openid, 不支持获取用户信息

    def get_msg_mentioned_user_ids(self) -> list[str]:
        return [
            str(msg_seg.data.get('user_id'))
            for msg_seg in self.event.get_message()
            if msg_seg.type == 'mention_user'
        ]

    def get_msg_image_urls(self) -> list[str]:
        return [str(msg_seg.data.get('url')) for msg_seg in self.event.get_message() if msg_seg.type == 'image']

    def get_reply_msg_id(self) -> str | None:
        raise NotImplementedError  # NOTE: QQ API not support currently

    def get_reply_msg_image_urls(self) -> list[str]:
        raise NotImplementedError  # NOTE: QQ API not support currently

    def get_reply_msg_plain_text(self) -> str | None:
        raise NotImplementedError  # NOTE: QQ API not support currently


def _parse_url_to_path(url: str) -> str | Path:
    if urlparse(url).scheme not in ['http', 'https']:
        return Path(url)
    return url


__all__ = []
