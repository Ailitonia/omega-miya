"""
@Author         : Ailitonia
@Date           : 2023/6/10 4:19
@FileName       : telegram
@Project        : nonebot2_miya
@Description    : Telegram 协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pathlib import Path
from typing import Any, Optional, Sequence, cast
from urllib.parse import quote

from nonebot.adapters.telegram import (
    Bot as TelegramBot,
    Message as TelegramMessage,
    MessageSegment as TelegramMessageSegment,
    Event as TelegramEvent
)
from nonebot.adapters.telegram.event import (
    MessageEvent as TelegramMessageEvent,
    GroupMessageEvent as TelegramGroupMessageEvent,
    PrivateMessageEvent as TelegramPrivateMessageEvent,
    ChannelPostEvent as TelegramChannelPostEvent
)
from nonebot.adapters.telegram.message import Entity, File

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


@message_builder_register.register_builder(SupportedPlatform.telegram)
class TelegramMessageBuilder(BaseMessageBuilder[OmegaMessage, TelegramMessage]):

    @staticmethod
    def _get_source_base_segment_type() -> type[OmegaMessageSegment]:
        return OmegaMessageSegment

    @staticmethod
    def _get_target_base_segment_type() -> type[TelegramMessageSegment]:
        return TelegramMessageSegment

    @staticmethod
    def _construct_platform_segment(seg_type: str, seg_data: dict[str, Any]) -> TelegramMessageSegment:
        match seg_type:
            case MessageSegmentType.at:
                return Entity.mention(text='@' + seg_data.get('user_id', ''))
            case MessageSegmentType.emoji:
                return Entity.custom_emoji(text=seg_data.get('name', ''), custom_emoji_id=seg_data.get('id', ''))
            case MessageSegmentType.audio:
                return File.audio(file=seg_data.get('url', ''))
            case MessageSegmentType.voice:
                return File.voice(file=seg_data.get('url', ''))
            case MessageSegmentType.video:
                return File.video(file=seg_data.get('url', ''))
            case MessageSegmentType.image:
                return File.photo(file=seg_data.get('url', ''))
            case MessageSegmentType.image_file:
                return File.document(file=seg_data.get('file', ''))
            case MessageSegmentType.file:
                return File.document(file=seg_data.get('file', ''))
            case MessageSegmentType.text:
                return Entity.text(text=seg_data.get('text', ''))
            case _:
                return Entity.text(text='')


@message_builder_register.register_extractor(SupportedPlatform.telegram)
class TelegramMessageExtractor(BaseMessageBuilder[TelegramMessage, OmegaMessage]):

    @staticmethod
    def _get_source_base_segment_type() -> type[TelegramMessageSegment]:
        return TelegramMessageSegment

    @staticmethod
    def _get_target_base_segment_type() -> type[OmegaMessageSegment]:
        return OmegaMessageSegment

    @staticmethod
    def _construct_platform_segment(seg_type: str, seg_data: dict[str, Any]) -> OmegaMessageSegment:
        match seg_type:
            case 'mention':
                return OmegaMessageSegment.at(user_id=str(seg_data.get('text')).removeprefix('@'))
            case 'custom_emoji':
                return OmegaMessageSegment.emoji(id_=seg_data.get('custom_emoji_id', ''), name=seg_data.get('text', ''))
            case 'audio':
                return OmegaMessageSegment.audio(url=seg_data.get('file', ''))
            case 'voice':
                return OmegaMessageSegment.voice(url=seg_data.get('file', ''))
            case 'video':
                return OmegaMessageSegment.video(url=seg_data.get('file', ''))
            case 'photo':
                return OmegaMessageSegment.image(url=seg_data.get('file', ''))
            case 'text':
                return OmegaMessageSegment.text(text=seg_data.get('text', ''))
            case _:
                return OmegaMessageSegment.other(type_=seg_type, data=seg_data)


class BaseTelegramEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        return EntityTargetSendParams(
            api='send_to',
            message_param_name='message',
            params={
                'chat_id': self.entity.entity_id
            }
        )

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        if isinstance(sent_return, Sequence):
            chat_id = sent_return[0].chat.id
            message_ids = [x.message_id for x in sent_return]
            return EntityTargetRevokeParams(
                api='delete_messages',
                params={'chat_id': chat_id, 'message_ids': message_ids}
                )
        else:
            return EntityTargetRevokeParams(
                    api='delete_message',
                    params={'chat_id': sent_return.chat.id, 'message_id': sent_return.message_id}
                )

    async def call_api_get_entity_name(self) -> str:
        bot = await self.get_bot()
        chat_data = await bot.call_api('get_chat', chat_id=self.entity.entity_id)

        title = getattr(chat_data, 'title', None)
        first_name = getattr(chat_data, 'first_name', None)

        return str(title) if title is not None else str(first_name) if first_name is not None else ''

    async def call_api_get_entity_profile_image_url(self) -> str:
        bot = cast(TelegramBot, await self.get_bot())
        chat_data = await bot.call_api('get_chat', chat_id=self.entity.entity_id)

        if (photo := getattr(chat_data, 'photo', None)) is None:
            raise ValueError('chat has no photo')

        file = await bot.call_api('get_file', file_id=getattr(photo, 'big_file_id', ''))
        return f"https://api.telegram.org/file/bot{quote(bot.bot_config.token)}/{quote(file.file_path)}"

    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        bot = cast(TelegramBot, await self.get_bot())
        file_message = File.document(file=Path(file_path).as_posix())

        await bot.send_to(chat_id=self.entity.entity_id, message=file_message)


@entity_target_register.register_target(SupportedTarget.telegram_user)
class TelegramUserEntityTarget(BaseTelegramEntityTarget):
    ...


@entity_target_register.register_target(SupportedTarget.telegram_group)
class TelegramGroupEntityTarget(BaseTelegramEntityTarget):
    ...


@entity_target_register.register_target(SupportedTarget.telegram_channel)
class TelegramChannelEntityTarget(BaseTelegramEntityTarget):
    ...


@event_depend_register.register_depend(TelegramEvent)
class TelegramEventDepend[Event_T: TelegramEvent](BaseEventDepend[TelegramBot, Event_T, TelegramMessage]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='telegram_user', entity_id=self.bot.self_id, parent_id=self.bot.self_id
        )

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='telegram_user', entity_id=self.bot.self_id, parent_id=self.bot.self_id
        )

    def get_omega_message_builder(self) -> type["BaseMessageBuilder[OmegaMessage, TelegramMessage]"]:
        return TelegramMessageBuilder

    def get_omega_message_extractor(self) -> type["BaseMessageBuilder[TelegramMessage, OmegaMessage]"]:
        return TelegramMessageExtractor

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


@event_depend_register.register_depend(TelegramMessageEvent)
class TelegramMessageEventDepend[Event_T: TelegramMessageEvent](TelegramEventDepend[Event_T]):

    async def send_at_sender(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        return await self.send(message=message, **kwargs)

    async def send_reply(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        return await self.send(message=message, reply_to_message_id=self.event.message_id, **kwargs)

    async def revoke(self, sent_return: Any, **kwargs) -> Any:
        if isinstance(sent_return, Sequence):
            message_ids = [x.message_id for x in sent_return]
            await self.bot.delete_messages(chat_id=self.event.chat.id, message_ids=message_ids)
        else:
            await self.bot.delete_message(chat_id=self.event.chat.id, message_id=sent_return.message_id)

    def get_user_nickname(self) -> str:
        return self.event.chat.username if self.event.chat.username else ''

    def get_msg_image_urls(self) -> list[str]:
        return [
            str(msg_seg.data.get('origin_url') or msg_seg.data.get('file'))
            for msg_seg in self.event.get_message()
            if msg_seg.type == 'photo'
        ]

    def get_reply_msg_image_urls(self) -> list[str]:
        if self.event.reply_to_message:
            return [
                str(msg_seg.data.get('origin_url') or msg_seg.data.get('file'))
                for msg_seg in self.event.reply_to_message.get_message()
                if msg_seg.type == 'photo'
            ]
        else:
            return []

    def get_reply_msg_plain_text(self) -> Optional[str]:
        if self.event.reply_to_message:
            return self.event.reply_to_message.get_plaintext()


@event_depend_register.register_depend(TelegramGroupMessageEvent)
class TelegramGroupMessageEventDepend(TelegramMessageEventDepend[TelegramGroupMessageEvent]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='telegram_group',
            entity_id=str(self.event.chat.id), parent_id=self.bot.self_id,
            entity_name=self.event.chat.title, entity_info=self.event.chat.type
        )

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='telegram_user',
            entity_id=str(self.event.from_.id), parent_id=self.bot.self_id,
            entity_name=self.event.from_.first_name,
            entity_info=f'{self.event.from_.first_name}/{self.event.from_.last_name}, @{self.event.from_.username}'
        )

    async def send_at_sender(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        built_message = self.build_platform_message(message=message)
        send_message = TelegramMessage()
        send_message += Entity.mention(f'@{self.event.from_.username}')
        send_message += Entity.text(' ')
        send_message += built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    def get_user_nickname(self) -> str:
        return self.event.from_.first_name


@event_depend_register.register_depend(TelegramPrivateMessageEvent)
class TelegramPrivateMessageEventDepend(TelegramMessageEventDepend[TelegramPrivateMessageEvent]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='telegram_user',
            entity_id=str(self.event.from_.id), parent_id=self.bot.self_id,
            entity_name=self.event.from_.first_name,
            entity_info=f'{self.event.from_.first_name}/{self.event.from_.last_name}, @{self.event.from_.username}'
        )

    async def send_at_sender(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        built_message = self.build_platform_message(message=message)
        send_message = TelegramMessage()
        send_message += Entity.mention(f'@{self.event.from_.username}')
        send_message += Entity.text(' ')
        send_message += built_message
        return await self.bot.send(event=self.event, message=send_message, **kwargs)

    def get_user_nickname(self) -> str:
        return self.event.from_.first_name


@event_depend_register.register_depend(TelegramChannelPostEvent)
class TelegramChannelPostEventDepend(TelegramMessageEventDepend[TelegramChannelPostEvent]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='telegram_channel',
            entity_id=str(self.event.chat.id), parent_id=self.bot.self_id,
            entity_name=self.event.chat.title, entity_info=self.event.chat.type
        )

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return self._extract_event_entity_params()


__all__ = []
