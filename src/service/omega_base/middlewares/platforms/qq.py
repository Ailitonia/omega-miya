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
from typing import Any, Optional
from urllib.parse import urlparse

from nonebot.adapters.qq import (
    Bot as QQBot,
    Message as QQMessage,
    MessageSegment as QQMessageSegment,
    Event as QQEvent,
    GuildMessageEvent as QQGuildMessageEvent,  # DirectMessageCreateEvent 是 GuildMessageEvent 的子类, 直接共用相同逻辑
    GroupAtMessageCreateEvent as QQGroupAtMessageCreateEvent,
    C2CMessageCreateEvent as QQC2CMessageCreateEvent,
)
from nonebot.adapters.qq.models import MessageReference, Message
from nonebot.matcher import current_event

from ..const import SupportedPlatform, SupportedTarget
from ..models import EntityInitParams, EntityTargetSendParams, EntityTargetRevokeParams
from ..platform_interface.entity_target import BaseEntityTarget, entity_target_register
from ..platform_interface.event_depend import BaseEventDepend, event_depend_register
from ..platform_interface.message_builder import BaseMessageBuilder, message_builder_register
from ..typing import BaseSentMessageType
from ...message import (
    MessageSegmentType,
    Message as OmegaMessage,
    MessageSegment as OmegaMessageSegment
)


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
            case MessageSegmentType.at.value:
                return QQMessageSegment.mention_user(user_id=seg_data.get('user_id', ''))
            case MessageSegmentType.forward_id.value:
                return QQMessageSegment.reference(reference=seg_data.get('id', ''))
            case MessageSegmentType.image.value:
                url = str(seg_data.get('url'))
                if urlparse(url).scheme not in ['http', 'https']:
                    return QQMessageSegment.file_image(data=Path(url))
                else:
                    return QQMessageSegment.image(url=url)
            case MessageSegmentType.image_file.value:
                return QQMessageSegment.file_image(data=Path(seg_data.get('file', '')))
            case MessageSegmentType.text.value:
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
            case 'reference':
                return OmegaMessageSegment.forward_id(id_=seg_data.get('reference', {}).get('message_id'))
            case 'attachment':
                url = 'https://' + str(seg_data.get('url')).removeprefix('http://').removeprefix('https://')
                return OmegaMessageSegment.image(url=url)
            case 'text':
                return OmegaMessageSegment.text(text=seg_data.get('text', ''))
            case _:
                return OmegaMessageSegment.text(text='')


@entity_target_register.register_target(SupportedTarget.qq_guild)
class QQGuildEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        raise NotImplementedError

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
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

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
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

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        if not isinstance(sent_return, Message):
            raise ValueError(f'Sent message({sent_return!r}) can not be revoked')
        return EntityTargetRevokeParams(
            api='delete_message',
            params={'channel_id': sent_return.channel_id, 'message_id': sent_return.id}
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

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        raise NotImplementedError  # TODO send_to_group

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        raise NotImplementedError  # TODO

    async def call_api_get_entity_name(self) -> str:
        raise NotImplementedError  # TODO

    async def call_api_get_entity_profile_image_url(self) -> str:
        raise NotImplementedError  # TODO

    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        raise NotImplementedError  # TODO post_group_files

@entity_target_register.register_target(SupportedTarget.qq_user)
class QQUserEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        raise NotImplementedError  # TODO send_to_c2c

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        raise NotImplementedError  # TODO

    async def call_api_get_entity_name(self) -> str:
        raise NotImplementedError  # TODO

    async def call_api_get_entity_profile_image_url(self) -> str:
        raise NotImplementedError  # TODO

    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        raise NotImplementedError  # TODO post_c2c_files

@entity_target_register.register_target(SupportedTarget.qq_guild_user)
class QQGuildUserEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
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

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
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

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_user', entity_id=self.bot.self_id, parent_id=self.bot.self_id
        )

    def get_omega_message_builder(self) -> type["BaseMessageBuilder[OmegaMessage, QQMessage]"]:
        return QQMessageBuilder

    def get_omega_message_extractor(self) -> type["BaseMessageBuilder[QQMessage, OmegaMessage]"]:
        return QQMessageExtractor

    async def send_at_sender(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        raise NotImplementedError

    async def send_reply(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        raise NotImplementedError

    async def revoke(self, sent_return: Any, **kwargs) -> Any:
        raise NotImplementedError

    def get_user_nickname(self) -> str:
        raise NotImplementedError

    def get_msg_image_urls(self) -> list[str]:
        raise NotImplementedError

    def get_reply_msg_image_urls(self) -> list[str]:
        raise NotImplementedError

    def get_reply_msg_plain_text(self) -> Optional[str]:
        raise NotImplementedError


@event_depend_register.register_depend(QQGuildMessageEvent)
class QQGuildMessageEventDepend(QQEventDepend[QQGuildMessageEvent]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_channel',
            entity_id=self.event.channel_id, parent_id=self.event.guild_id
        )

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_guild_user',
            entity_id=self.event.author.id, parent_id=self.event.guild_id,
            entity_name=self.event.author.username, entity_info=self.event.author.avatar
        )

    async def send_at_sender(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.mention_user(user_id=self.event.author.id) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def send_reply(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.reference(reference=MessageReference(message_id=self.event.id)) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def revoke(self, sent_return: Any, **kwargs) -> Any:
        return await self.bot.delete_message(channel_id=sent_return.channel_id, message_id=sent_return.id, **kwargs)

    def get_user_nickname(self) -> str:
        return self.event.author.username if self.event.author.username else ''

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


@event_depend_register.register_depend(QQC2CMessageCreateEvent)
class QQC2CMessageCreateEventDepend(QQEventDepend[QQC2CMessageCreateEvent]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_user',
            entity_id=self.event.author.user_openid, parent_id=self.bot.self_id,
            entity_info=f'id: {self.event.author.id}, openid: {self.event.author.user_openid}'
        )

    async def send_at_sender(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.mention_user(user_id=self.event.author.user_openid) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def send_reply(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.reference(reference=MessageReference(message_id=self.event.id)) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def revoke(self, sent_return: Any, **kwargs) -> Any:
        return await self.bot.delete_c2c_message(openid=self.event.author.user_openid, message_id=sent_return.id)

    def get_user_nickname(self) -> str:
        raise NotImplementedError  # QQ 协议只有 openid, 不支持获取用户信息

    def get_msg_image_urls(self) -> list[str]:
        return [str(msg_seg.data.get('url')) for msg_seg in self.event.get_message() if msg_seg.type == 'image']

    def get_reply_msg_image_urls(self) -> list[str]:
        raise NotImplementedError  # QQ 协议消息只有回复序列 id, 不支持获取回复消息内容

    def get_reply_msg_plain_text(self) -> Optional[str]:
        raise NotImplementedError  # QQ 协议消息只有回复序列 id, 不支持获取回复消息内容


@event_depend_register.register_depend(QQGroupAtMessageCreateEvent)
class QQGroupAtMessageCreateEventDepend(QQEventDepend[QQGroupAtMessageCreateEvent]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_group',
            entity_id=self.event.group_openid, parent_id=self.bot.self_id,
            entity_info=f'group_openid: {self.event.group_openid}'
        )

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='qq_user',
            entity_id=self.event.author.member_openid, parent_id=self.bot.self_id,
            entity_info=f'id: {self.event.author.id}, member_openid: {self.event.author.member_openid}'
        )

    async def send_at_sender(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.mention_user(user_id=self.event.author.member_openid) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def send_reply(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        built_message = self.build_platform_message(message=message)
        send_message = QQMessageSegment.reference(reference=MessageReference(message_id=self.event.id)) + built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    async def revoke(self, sent_return: Any, **kwargs) -> Any:
        return await self.bot.delete_group_message(group_openid=self.event.group_openid, message_id=sent_return.id)

    def get_user_nickname(self) -> str:
        raise NotImplementedError  # QQ 协议只有 openid, 不支持获取用户信息

    def get_msg_image_urls(self) -> list[str]:
        return [str(msg_seg.data.get('url')) for msg_seg in self.event.get_message() if msg_seg.type == 'image']

    def get_reply_msg_image_urls(self) -> list[str]:
        raise NotImplementedError  # QQ 协议消息只有回复序列 id, 不支持获取回复消息内容

    def get_reply_msg_plain_text(self) -> Optional[str]:
        raise NotImplementedError  # QQ 协议消息只有回复序列 id, 不支持获取回复消息内容


__all__ = []
