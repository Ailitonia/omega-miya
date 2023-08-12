"""
@Author         : Ailitonia
@Date           : 2023/8/13 4:20
@FileName       : qqguild_adapter_patch
@Project        : nonebot2_miya
@Description    : QQGuild adapter patch
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Dict, Optional, Union

from nonebot.adapters.qqguild import Bot, Event, MessageEvent, DirectMessageCreateEvent, Message, MessageSegment
from nonebot.log import logger


@staticmethod
def _extract_send_message(message: Union[str, Message, MessageSegment]) -> Dict[str, Any]:
    message = MessageSegment.text(message) if isinstance(message, str) else message
    message = message if isinstance(message, Message) else Message(message)

    kwargs = {}
    content = message.extract_content() or None
    kwargs["content"] = content
    if embed := (message["embed"] or None):
        embed = embed[-1].data["embed"]
        kwargs["embed"] = embed
    if ark := (message["ark"] or None):
        ark = ark[-1].data["ark"]
        kwargs["ark"] = ark
    if image := (message["attachment"] or None):
        image = image[-1].data["url"]
        kwargs["image"] = image
    if file_image := (message["file_image"] or None):
        file_image = file_image[-1].data["content"]
        kwargs["file_image"] = file_image
    if markdown := (message["markdown"] or None):
        markdown = markdown[-1].data["markdown"]
        kwargs["markdown"] = markdown
    if reference := (message["reference"] or None):
        reference = reference[-1].data["reference"]
        kwargs["reference"] = reference

    return kwargs


async def send_to_dms(
        self: Bot,
        message: Union[str, Message, MessageSegment],
        guild_id: int,
        *,
        msg_id: Optional[int] = None
) -> Any:
    return await self.post_dms_messages(
        guild_id=guild_id,  # type: ignore
        msg_id=msg_id,
        **self._extract_send_message(message=message)
    )


async def send_to(
        self: Bot,
        message: Union[str, Message, MessageSegment],
        channel_id: int,
        *,
        msg_id: Optional[int] = None
) -> Any:
    return await self.post_messages(
        channel_id=channel_id,
        msg_id=msg_id,
        **self._extract_send_message(message=message)
    )


async def send(
        self: Bot,
        event: Event,
        message: Union[str, Message, MessageSegment],
        **kwargs,
) -> Any:
    if not isinstance(event, MessageEvent) or not event.channel_id or not event.id:
        raise RuntimeError("Event cannot be replied to!")

    if isinstance(event, DirectMessageCreateEvent):
        # 私信需要使用 post_dms_messages
        # https://bot.q.qq.com/wiki/develop/api/openapi/dms/post_dms_messages.html#%E5%8F%91%E9%80%81%E7%A7%81%E4%BF%A1
        return await self.send_to_dms(message=message, guild_id=event.guild_id, msg_id=event.id)
    else:
        return await self.send_to(message=message, channel_id=event.channel_id, msg_id=event.id)


Bot._extract_send_message = _extract_send_message
Bot.send_to_dms = send_to_dms
Bot.send_to = send_to
Bot.send = send

logger.opt(colors=True).info(f'<lc>QQGuild adapter patch</lc> loaded')


__all__ = []
