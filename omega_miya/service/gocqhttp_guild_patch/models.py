import inspect
from typing import List, Optional, Type, TypeVar

from nonebot.adapters.onebot.v11 import (
    Adapter,
    Event,
    Message,
    MessageEvent,
    NoticeEvent,
    MessageSegment
)
from nonebot.log import logger
from nonebot.typing import overrides
from nonebot.utils import escape_tag
from nonebot.exception import NoLogException
from pydantic import BaseModel, Field, parse_obj_as, validator, root_validator
from typing_extensions import Literal

from .config import guild_patch_config

Event_T = TypeVar("Event_T", bound=Type[Event])


def register_event(event: Event_T) -> Event_T:
    Adapter.add_custom_model(event)
    logger.opt(colors=True).debug(
        f"Custom event <e>{event.__qualname__!r}</e> registered "
        f"from module <g>{inspect.getmodule(event).__name__!r}</g>"
    )
    return event


@register_event
class GuildMessageEvent(MessageEvent):
    """收到频道消息"""
    message_type: Literal["guild"]
    self_tiny_id: int
    message_id: str
    guild_id: int
    channel_id: int

    raw_message: str = Field(alias="message")
    font: None = None

    @validator('raw_message', pre=True)
    def _validate_raw_message(cls, raw_message):
        if isinstance(raw_message, str):
            return raw_message
        elif isinstance(raw_message, list):
            return str(parse_obj_as(Message, raw_message))
        raise ValueError('unknown raw message type')

    @root_validator(pre=False)
    def _validate_is_tome(cls, values):
        message = values.get('message')
        self_tiny_id = values.get('self_tiny_id')
        message, is_tome = cls._check_at_me(message=message, self_tiny_id=self_tiny_id)
        values.update({'message': message, 'to_me': is_tome, 'raw_message': str(message)})
        return values

    @overrides(Event)
    def is_tome(self) -> bool:
        return self.to_me or any(
            str(msg_seg.data.get('qq', '')) == str(self.self_tiny_id)
            for msg_seg in self.message
            if msg_seg.type == 'at'
        )

    @overrides(Event)
    def get_event_description(self) -> str:
        return (
            f'Message {self.message_id} from {self.user_id}@[频道:{self.guild_id}/子频道:{self.channel_id}] "'
            + "".join(
                map(
                    lambda x: escape_tag(str(x))
                    if x.is_text()
                    else f"<le>{escape_tag(str(x))}</le>",
                    self.message,
                )
            )
            + '"'
        )

    def get_log_string(self) -> str:
        if not guild_patch_config.enable_guild_event_log:
            raise NoLogException(adapter_name='nonebot-adapter-onebot')
        else:
            return super().get_log_string()

    @overrides(MessageEvent)
    def get_session_id(self) -> str:
        return f"guild_{self.guild_id}_channel_{self.channel_id}_{self.user_id}"

    @staticmethod
    def _check_at_me(message: Message, self_tiny_id: int | str) -> tuple[Message, bool]:
        """检查消息开头或结尾是否存在 @机器人，去除并赋值 ``event.to_me``"""
        is_tome = False
        # ensure message not empty
        if not message:
            message.append(MessageSegment.text(""))

        def _is_at_me_seg(segment: MessageSegment):
            return segment.type == 'at' and str(segment.data.get('qq', '')) == str(self_tiny_id)

        # check the first segment
        if _is_at_me_seg(message[0]):
            is_tome = True
            message.pop(0)
            if message and message[0].type == "text":
                message[0].data["text"] = message[0].data["text"].lstrip()
                if not message[0].data["text"]:
                    del message[0]
            if message and _is_at_me_seg(message[0]):
                message.pop(0)
                if message and message[0].type == "text":
                    message[0].data["text"] = (
                        message[0].data["text"].lstrip()
                    )
                    if not message[0].data["text"]:
                        del message[0]

        if not is_tome:
            # check the last segment
            i = -1
            last_msg_seg = message[i]
            if (
                    last_msg_seg.type == "text"
                    and not last_msg_seg.data["text"].strip()
                    and len(message) >= 2
            ):
                i -= 1
                last_msg_seg = message[i]

            if _is_at_me_seg(last_msg_seg):
                is_tome = True
                del message[i:]

        if not message:
            message.append(MessageSegment.text(""))

        return message, is_tome


class ReactionInfo(BaseModel):
    emoji_id: str
    emoji_index: int
    emoji_type: int
    emoji_name: str
    count: int
    clicked: bool

    class Config:
        extra = "allow"


@register_event
class ChannelNoticeEvent(NoticeEvent):
    """频道通知事件"""
    notice_type: Literal["channel"]
    self_tiny_id: int
    guild_id: int
    channel_id: int
    user_id: int

    sub_type: None = None

    def get_log_string(self) -> str:
        if not guild_patch_config.enable_guild_event_log:
            raise NoLogException(adapter_name='nonebot-adapter-onebot')
        else:
            return super().get_log_string()


@register_event
class MessageReactionUpdatedNoticeEvent(ChannelNoticeEvent):
    """频道消息表情贴更新"""
    notice_type: Literal["message_reactions_updated"]
    message_id: str
    current_reactions: Optional[List[ReactionInfo]] = None

    def get_log_string(self) -> str:
        if not guild_patch_config.enable_guild_event_log:
            raise NoLogException(adapter_name='nonebot-adapter-onebot')
        else:
            return super().get_log_string()


class SlowModeInfo(BaseModel):
    slow_mode_key: int
    slow_mode_text: str
    speak_frequency: int
    slow_mode_circle: int

    class Config:
        extra = "allow"


class ChannelInfo(BaseModel):
    owner_guild_id: int
    channel_id: int
    channel_type: int
    channel_name: str
    create_time: int
    creator_id: Optional[int]
    creator_tiny_id: int
    talk_permission: int
    visible_type: int
    current_slow_mode: int
    slow_modes: List[SlowModeInfo] = []

    class Config:
        extra = "allow"


@register_event
class ChannelUpdatedNoticeEvent(ChannelNoticeEvent):
    """子频道信息更新"""
    notice_type: Literal["channel_updated"]
    operator_id: int
    old_info: ChannelInfo
    new_info: ChannelInfo

    def get_log_string(self) -> str:
        if not guild_patch_config.enable_guild_event_log:
            raise NoLogException(adapter_name='nonebot-adapter-onebot')
        else:
            return super().get_log_string()


@register_event
class ChannelCreatedNoticeEvent(ChannelNoticeEvent):
    """子频道创建"""
    notice_type: Literal["channel_created"]
    operator_id: int
    channel_info: ChannelInfo

    def get_log_string(self) -> str:
        if not guild_patch_config.enable_guild_event_log:
            raise NoLogException(adapter_name='nonebot-adapter-onebot')
        else:
            return super().get_log_string()


@register_event
class ChannelDestroyedNoticeEvent(ChannelNoticeEvent):
    """子频道删除"""
    notice_type: Literal["channel_destroyed"]
    operator_id: int
    channel_info: ChannelInfo

    def get_log_string(self) -> str:
        if not guild_patch_config.enable_guild_event_log:
            raise NoLogException(adapter_name='nonebot-adapter-onebot')
        else:
            return super().get_log_string()


__all__ = [
    'GuildMessageEvent',
    'ChannelNoticeEvent',
    'MessageReactionUpdatedNoticeEvent',
    'ChannelUpdatedNoticeEvent',
    'ChannelCreatedNoticeEvent',
    'ChannelDestroyedNoticeEvent',
    'ReactionInfo',
    'SlowModeInfo',
    'ChannelInfo'
]
