"""https://gist.github.com/mnixry/57033047be55956e2168284bcf0bd4b6
NoneBot2 QQ 频道支持适配补丁

注: 本补丁没有经过充分测试, 不建议在生产环境使用, 如果发现任何问题请评论反馈

适用版本
go-cqhttp >= 1.0.0-beta8
已支持1.0.0-beta8-fix1新加入的事件
NoneBot2 >= 2.0.0a16
支持功能
 正常接收并处理频道消息事件
 支持字符串形式消息上报
 支持数组形式消息上报
 支持bot.send和matcher.send直接向频道发送消息
 支持event.to_me以支持to_me规则
 可选的事件转换器, 将频道消息事件转换为群消息 不会写， 有人能教教吗
使用方法
保存该文件为nonebot_guild_patch.py, 放到加载插件目录即可

如果它被成功加载, 你在调试模式下应该看到这样的日志:

11-13 09:14:52 [DEBUG] nonebot | Succeeded to load adapter "cqhttp"
11-13 09:14:52 [SUCCESS] nonebot | Succeeded to import "nonebot.plugins.echo"
+ 11-13 09:14:52 [SUCCESS] nonebot | Succeeded to import "nonebot_guild_patch"
11-13 09:14:52 [SUCCESS] nonebot | Running NoneBot...
11-13 09:14:52 [DEBUG] nonebot | Loaded adapters: cqhttp
11-13 09:14:52 [INFO] uvicorn | Started server process [114514]
11-13 09:14:52 [INFO] uvicorn | Waiting for application startup.
+ 11-13 09:14:52 [DEBUG] plugins | Patch for NoneBot2 guild adaptation has been applied.
11-13 09:14:52 [INFO] uvicorn | Application startup complete.
这里有一个示例插件, 它只会接收来自频道的消息

from nonebot.plugin import on_command
from nonebot.adapters.cqhttp import Bot, MessageSegment

from plugins.nonebot_guild_patch import GuildMessageEvent # 可能会根据目录结构和保存文件名的不同而不同

matcher = on_command('image')


@matcher.handle()
async def _(bot: Bot, event: GuildMessageEvent):
    await matcher.send(
        MessageSegment.image(
            file='https://1mg.obfs.dev/',
            cache=False,
        ))
"""

import inspect
from typing_extensions import Literal
from typing import List, Union, Optional

from pydantic import Field, BaseModel, validator

import nonebot
from nonebot.log import logger
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.utils import escape
from nonebot.adapters.cqhttp.message import Message, MessageSegment
from nonebot.adapters.cqhttp.event import Event, NoticeEvent, MessageEvent


class GuildMessageEvent(MessageEvent):
    __event__ = "message.guild"
    self_tiny_id: int

    message_type: Literal["guild"]
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
            return str(Message(raw_message))
        raise ValueError('unknown raw message type')


class ReactionInfo(BaseModel):
    emoji_id: str
    emoji_index: int
    emoji_type: int
    emoji_name: str
    count: int
    clicked: bool

    class Config:
        extra = "allow"


class ChannelNoticeEvent(NoticeEvent):
    __event__ = "notice.channel"
    self_tiny_id: int
    guild_id: int
    channel_id: int
    user_id: int

    sub_type: None = None


class MessageReactionUpdatedNoticeEvent(ChannelNoticeEvent):
    __event__ = "notice.message_reactions_updated"
    notice_type: Literal["message_reactions_updated"]
    message_id: str
    current_reactions: Optional[List[ReactionInfo]] = None


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
    creator_id: int
    creator_tiny_id: int
    talk_permission: int
    visible_type: int
    current_slow_mode: int
    slow_modes: List[SlowModeInfo] = []

    class Config:
        extra = "allow"


class ChannelUpdatedNoticeEvent(ChannelNoticeEvent):
    __event__ = "notice.channel_updated"
    notice_type: Literal["channel_updated"]
    operator_id: int
    old_info: ChannelInfo
    new_info: ChannelInfo


class ChannelCreatedNoticeEvent(ChannelNoticeEvent):
    __event__ = "notice.channel_created"
    notice_type: Literal["channel_created"]
    operator_id: int
    channel_info: ChannelInfo


class ChannelDestoryedNoticeEvent(ChannelNoticeEvent):
    __event__ = "notice.channel_destoryed"
    notice_type: Literal["channel_destoryed"]
    operator_id: int
    channel_info: ChannelInfo


original_send = Bot.send


async def patched_send(self: Bot, event: Event,
                       message: Union[Message, MessageSegment, str], **kwargs):
    guild_id: Optional[int] = getattr(event, "guild_id", None)
    channel_id: Optional[int] = getattr(event, 'channel_id', None)
    if not (guild_id and channel_id):
        return await original_send(self, event, message, **kwargs)

    user_id: Optional[int] = getattr(event, 'user_id', None)
    message = escape(message, escape_comma=False) if isinstance(
        message, str) else message

    message_sent = message if isinstance(message, Message) else Message(message)
    if user_id and kwargs.get('at_sender', False):
        message_sent = MessageSegment.at(user_id) + ' ' + message_sent

    return await self.send_guild_channel_msg(guild_id=guild_id,
                                             channel_id=channel_id,
                                             message=message_sent)


driver = nonebot.get_driver()


@driver.on_startup
def patch():
    import nonebot.adapters.cqhttp.event as events

    Bot.send = patched_send

    for model in globals().values():
        if not inspect.isclass(model) or not issubclass(model, Event):
            continue
        events._t["." + model.__event__] = model

    logger.debug('Patch for NoneBot2 guild adaptation has been applied.')
