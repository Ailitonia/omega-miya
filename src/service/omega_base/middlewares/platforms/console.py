"""
@Author         : Ailitonia
@Date           : 2023/7/3 22:31
@FileName       : console
@Project        : nonebot2_miya
@Description    : nonebot-console 协议适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Optional

from nonebot.adapters.console import (
    Bot as ConsoleBot,
    Message as ConsoleMessage,
    MessageSegment as ConsoleMessageSegment,
    Event as ConsoleEvent,
    MessageEvent as ConsoleMessageEvent
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


@message_builder_register.register_builder(SupportedPlatform.console)
class ConsoleMessageBuilder(BaseMessageBuilder[OmegaMessage, ConsoleMessage]):

    @staticmethod
    def _get_source_base_segment_type() -> type[OmegaMessageSegment]:
        return OmegaMessageSegment

    @staticmethod
    def _get_target_base_segment_type() -> type[ConsoleMessageSegment]:
        return ConsoleMessageSegment

    @staticmethod
    def _construct_platform_segment(seg_type: str, seg_data: dict[str, Any]) -> ConsoleMessageSegment:
        match seg_type:
            case MessageSegmentType.text.value:
                return ConsoleMessageSegment.text(text=seg_data.get('text', ''))
            case _:
                return ConsoleMessageSegment.text(text='')


@message_builder_register.register_extractor(SupportedPlatform.console)
class ConsoleMessageExtractor(BaseMessageBuilder[ConsoleMessage, OmegaMessage]):

    @staticmethod
    def _get_source_base_segment_type() -> type[ConsoleMessageSegment]:
        return ConsoleMessageSegment

    @staticmethod
    def _get_target_base_segment_type() -> type[OmegaMessageSegment]:
        return OmegaMessageSegment

    @staticmethod
    def _construct_platform_segment(seg_type: str, seg_data: dict[str, Any]) -> OmegaMessageSegment:
        match seg_type:
            case 'emoji':
                return OmegaMessageSegment.text(text=seg_data.get('name', ''))
            case 'text':
                return OmegaMessageSegment.text(text=seg_data.get('text', ''))
            case _:
                return OmegaMessageSegment.text(text='')


@entity_target_register.register_target(SupportedTarget.console_user)
class ConsoleEntityTarget(BaseEntityTarget):

    def get_api_to_send_msg(self, **kwargs) -> "EntityTargetSendParams":
        return EntityTargetSendParams(
            api='send_msg',
            message_param_name='message',
            params={
                'user_id': self.entity.entity_name
            }
        )

    def get_api_to_revoke_msgs(self, sent_return: Any, **kwargs) -> "EntityTargetRevokeParams":
        raise NotImplementedError

    async def call_api_get_entity_name(self) -> str:
        return 'ConsoleUser'

    async def call_api_get_entity_profile_image_url(self) -> str:
        return ''

    async def call_api_send_file(self, file_path: str, file_name: str) -> None:
        raise NotImplementedError


@event_depend_register.register_depend(ConsoleEvent)
class ConsoleEventDepend[Event_T: ConsoleEvent](BaseEventDepend[ConsoleBot, Event_T, ConsoleMessage]):

    def _extract_event_entity_params(self) -> "EntityInitParams":
        return self._extract_user_entity_params()

    def _extract_user_entity_params(self) -> "EntityInitParams":
        return EntityInitParams(
            bot_id=self.bot.self_id, entity_type='console_user',
            entity_id=self.event.user.id, parent_id=self.bot.self_id,
            entity_name=self.event.user.nickname, entity_info=self.event.user.avatar
        )

    def get_omega_message_builder(self) -> type["BaseMessageBuilder[OmegaMessage, ConsoleMessage]"]:
        return ConsoleMessageBuilder

    def get_omega_message_extractor(self) -> type["BaseMessageBuilder[ConsoleMessage, OmegaMessage]"]:
        return ConsoleMessageExtractor

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


@event_depend_register.register_depend(ConsoleMessageEvent)
class ConsoleMessageEventDepend(ConsoleEventDepend[ConsoleMessageEvent]):

    async def send_at_sender(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        return await self.send(message=message, **kwargs)

    async def send_reply(self, message: "BaseSentMessageType[OmegaMessage]", **kwargs) -> Any:
        return await self.send(message=message, **kwargs)

    def get_user_nickname(self) -> str:
        return self.event.get_user_id()

    def get_msg_image_urls(self) -> list[str]:
        return []

    def get_reply_msg_image_urls(self) -> list[str]:
        return []

    def get_reply_msg_plain_text(self) -> Optional[str]:
        return None


__all__ = []
