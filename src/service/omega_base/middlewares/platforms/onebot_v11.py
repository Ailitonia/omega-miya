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
from typing import Any, Optional
from urllib.parse import urlparse

from nonebot.adapters.onebot.v11 import (
    Bot as OneBotV11Bot,
    Message as OneBotV11Message,
    MessageSegment as OneBotV11MessageSegment,
    Event as OneBotV11Event,
    MessageEvent as OneBotV11MessageEvent,
    GroupMessageEvent as OneBotV11GroupMessageEvent,
    PrivateMessageEvent as OneBotV11PrivateMessageEvent,
)

from src.service.gocqhttp_guild_patch import (
    GuildMessageEvent as OneBotV11GuildMessageEvent
)
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


@message_builder_register.register_builder(SupportedPlatform.onebot_v11)
class OneBotV11MessageBuilder(BaseMessageBuilder[OmegaMessage, OneBotV11Message]):

    @staticmethod
    def _get_source_base_segment_type() -> type[OmegaMessageSegment]:
        return OmegaMessageSegment

    @staticmethod
    def _get_target_base_segment_type() -> type[OneBotV11MessageSegment]:
        return OneBotV11MessageSegment

    @staticmethod
    def _construct_platform_segment(seg_type: str, seg_data: dict[str, Any]) -> OneBotV11MessageSegment:
        match seg_type:
            case MessageSegmentType.at.value:
                return OneBotV11MessageSegment.at(user_id=seg_data.get('user_id', 0))
            case MessageSegmentType.at_all.value:
                return OneBotV11MessageSegment.at(user_id='all')
            case MessageSegmentType.forward_id.value:
                return OneBotV11MessageSegment.node(id_=seg_data.get('id', 0))
            case MessageSegmentType.custom_node.value:
                return OneBotV11MessageSegment.node_custom(
                    user_id=seg_data.get('user_id', 0),
                    nickname=seg_data.get('nickname', ''),
                    content=seg_data.get('content', '')
                )
            case MessageSegmentType.image.value:
                url = str(seg_data.get('url', ''))
                if urlparse(url).scheme not in ['http', 'https']:
                    url = Path(url)
                return OneBotV11MessageSegment.image(file=url)
            case MessageSegmentType.image_file.value:
                return OneBotV11MessageSegment.image(file=Path(seg_data.get('file', '')))
            case MessageSegmentType.text.value:
                return OneBotV11MessageSegment.text(text=seg_data.get('text', ''))
            case _:
                return OneBotV11MessageSegment.text(text='')


@message_builder_register.register_extractor(SupportedPlatform.onebot_v11)
class OneBotV11MessageExtractor(BaseMessageBuilder[OneBotV11Message, OmegaMessage]):

    @staticmethod
    def _get_source_base_segment_type() -> type[OneBotV11MessageSegment]:
        return OneBotV11MessageSegment

    @staticmethod
    def _get_target_base_segment_type() -> type[OmegaMessageSegment]:
        return OmegaMessageSegment

    @staticmethod
    def _construct_platform_segment(seg_type: str, seg_data: dict[str, Any]) -> OmegaMessageSegment:
        match seg_type:
            case 'at':
                return OmegaMessageSegment.at(user_id=seg_data.get('qq', 0))
            case 'forward':
                return OmegaMessageSegment.forward_id(id_=seg_data.get('id', 0))
            case 'node':
                return OmegaMessageSegment.custom_node(
                    user_id=seg_data.get('user_id', 0),
                    nickname=seg_data.get('nickname', ''),
                    content=seg_data.get('content', '')
                )
            case 'image':
                url = str(seg_data.get('url', '') if seg_data.get('url') else seg_data.get('file', ''))
                if urlparse(url).scheme not in ['http', 'https']:
                    url = Path(url)
                return OmegaMessageSegment.image(url=url)
            case 'text':
                return OmegaMessageSegment.text(text=seg_data.get('text', ''))
            case _:
                return OmegaMessageSegment.text(text='')


@entity_target_register.register_target(SupportedTarget.onebot_v11_user)
class OneBotV11UserEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        return EntityTargetSendParams(
            api='send_private_msg',
            message_param_name='message',
            params={
                'user_id': self.entity.entity_id
            }
        )

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        return EntityTargetRevokeParams(api='delete_msg', params={'message_id': sent_return['message_id']})

    async def call_api_get_entity_name(self) -> str:
        bot = await self.get_bot()
        user_data = await bot.call_api('get_stranger_info', user_id=self.entity.entity_id)
        entity_name = user_data.get('nickname', '')
        return str(entity_name)

    async def call_api_get_entity_profile_image_url(self) -> str:
        # head_img_size: 1: 40×40px, 2: 40×40px, 3: 100×100px, 4: 140×140px, 5: 640×640px, 40: 40×40px, 100: 100×100px
        head_img_size = 5
        url_version = 0

        match url_version:
            case 2:
                url = f'https://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins={self.entity.entity_id}'
            case 1:
                url = f'https://q2.qlogo.cn/headimg_dl?dst_uin={self.entity.entity_id}&spec={head_img_size}'
            case 0 | _:
                url = f'https://q1.qlogo.cn/g?b=qq&nk={self.entity.entity_id}&s={head_img_size}'
        return url


@entity_target_register.register_target(SupportedTarget.onebot_v11_group)
class OneBotV11GroupEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        return EntityTargetSendParams(
            api='send_group_msg',
            message_param_name='message',
            params={
                'group_id': self.entity.entity_id
            }
        )

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        return EntityTargetRevokeParams(api='delete_msg', params={'message_id': sent_return['message_id']})

    async def call_api_get_entity_name(self) -> str:
        bot = await self.get_bot()
        group_data = await bot.call_api('get_group_info', group_id=self.entity.entity_id)
        entity_name = group_data.get('group_name', '')
        return str(entity_name)

    async def call_api_get_entity_profile_image_url(self) -> str:
        # head_img_size: 40: 40×40px, 100: 100×100px, 140: 140×140px, 640: 640×640px
        head_img_size = 640
        return f'https://p.qlogo.cn/gh/{self.entity.entity_id}/{self.entity.entity_id}/{head_img_size}/'


@entity_target_register.register_target(SupportedTarget.onebot_v11_guild)
class OneBotV11GuildEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        raise NotImplementedError  # 非标准 API, 协议端未实现

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        raise NotImplementedError  # 非标准 API, 协议端未实现

    async def call_api_get_entity_name(self) -> str:
        bot = await self.get_bot()
        guild_data = await bot.call_api('get_guild_meta_by_guest', guild_id=self.entity.entity_id)
        entity_name = guild_data.get('guild_name', '')
        return str(entity_name)

    async def call_api_get_entity_profile_image_url(self) -> str:
        raise NotImplementedError  # 非标准 API, 协议端未实现


@entity_target_register.register_target(SupportedTarget.onebot_v11_guild_channel)
class OneBotV11GuildChannelEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        return EntityTargetSendParams(
            api='send_guild_channel_msg',
            message_param_name='message',
            params={
                'guild_id': self.entity.parent_id,
                'channel_id': self.entity.entity_id
            }
        )

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        raise NotImplementedError  # 非标准 API, 协议端未实现

    async def call_api_get_entity_name(self) -> str:
        raise NotImplementedError  # 非标准 API, 协议端未实现

    async def call_api_get_entity_profile_image_url(self) -> str:
        raise NotImplementedError  # 非标准 API, 协议端未实现


@entity_target_register.register_target(SupportedTarget.onebot_v11_guild_user)
class OneBotV11GuildUserEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        raise NotImplementedError  # 非标准 API, 协议端未实现

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        raise NotImplementedError  # 非标准 API, 协议端未实现

    async def call_api_get_entity_name(self) -> str:
        bot = await self.get_bot()
        guild_user_data = await bot.call_api(
            'get_guild_member_profile', guild_id=self.entity.parent_id, user_id=self.entity.entity_id
        )
        entity_name = guild_user_data.get('nickname', '')
        return str(entity_name)

    async def call_api_get_entity_profile_image_url(self) -> str:
        bot = await self.get_bot()
        guild_user_data = await bot.call_api(
            'get_guild_member_profile', guild_id=self.entity.parent_id, user_id=self.entity.entity_id
        )
        avatar_url = guild_user_data.get('avatar_url', '')
        return str(avatar_url)


@event_depend_register.register_depend(OneBotV11Event)
class OneBotV11EventDepend[Event_T: OneBotV11Event](BaseEventDepend[OneBotV11Bot, Event_T, OneBotV11Message]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> "EntityInitParams":
        bot_self_id = self.bot.self_id

        if user_id := getattr(self.event, 'user_id', None):
            entity_type = 'onebot_v11_user'
            entity_id = str(user_id)
        else:
            entity_type = 'onebot_v11_user'
            entity_id = bot_self_id

        return EntityInitParams(bot_id=bot_self_id, entity_type=entity_type, entity_id=entity_id, parent_id=bot_self_id)

    def get_omega_message_builder(self) -> type["BaseMessageBuilder[OmegaMessage, OneBotV11Message]"]:
        return OneBotV11MessageBuilder

    def get_omega_message_extractor(self) -> type["BaseMessageBuilder[OneBotV11Message, OmegaMessage]"]:
        return OneBotV11MessageExtractor

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


@event_depend_register.register_depend(OneBotV11MessageEvent)
class OneBotV11MessageEventDepend[Event_T: OneBotV11MessageEvent](OneBotV11EventDepend[Event_T]):

    async def send_at_sender(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        return await self.send(message=message, at_sender=True, **kwargs)

    async def send_reply(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        return await self.send(message=message, reply_message=True, **kwargs)

    async def revoke(self, sent_return: Any, **kwargs) -> Any:
        return await self.bot.delete_msg(message_id=sent_return['message_id'])

    def get_user_nickname(self) -> str:
        nickname = self.event.sender.card if self.event.sender.card else self.event.sender.nickname
        return nickname if nickname is not None else ''

    def get_msg_image_urls(self) -> list[str]:
        return [str(msg_seg.data.get('url')) for msg_seg in self.event.message if msg_seg.type == 'image']

    def get_reply_msg_image_urls(self) -> list[str]:
        if self.event.reply:
            return [str(msg_seg.data.get('url')) for msg_seg in self.event.reply.message if msg_seg.type == 'image']
        else:
            return []

    def get_reply_msg_plain_text(self) -> Optional[str]:
        if self.event.reply:
            return self.event.reply.message.extract_plain_text()
        else:
            return None


@event_depend_register.register_depend(OneBotV11GroupMessageEvent)
class OneBotV11GroupMessageEventDepend(OneBotV11MessageEventDepend[OneBotV11GroupMessageEvent]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id,
            entity_type='onebot_v11_group',
            entity_id=str(self.event.group_id),
            parent_id=self.bot.self_id
        )

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id,
            entity_type='onebot_v11_user',
            entity_id=str(self.event.user_id),
            parent_id=self.bot.self_id,
            entity_name=self.event.sender.nickname,
            entity_info=self.event.sender.card
        )


@event_depend_register.register_depend(OneBotV11PrivateMessageEvent)
class OneBotV11PrivateMessageEventDepend(OneBotV11MessageEventDepend[OneBotV11PrivateMessageEvent]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id,
            entity_type='onebot_v11_user',
            entity_id=str(self.event.user_id),
            parent_id=self.bot.self_id,
            entity_name=self.event.sender.nickname,
            entity_info=self.event.sender.card
        )


@event_depend_register.register_depend(OneBotV11GuildMessageEvent)
class OneBotV11GuildMessageEventDepend(OneBotV11MessageEventDepend[OneBotV11GuildMessageEvent]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id,
            entity_type='onebot_v11_guild_channel',
            entity_id=str(self.event.channel_id),
            parent_id=str(self.event.guild_id)
        )

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id,
            entity_type='onebot_v11_guild_user',
            entity_id=str(self.event.user_id),
            parent_id=str(self.event.guild_id),
            entity_name=self.event.sender.nickname,
            entity_info=self.event.sender.card
        )


__all__ = []
