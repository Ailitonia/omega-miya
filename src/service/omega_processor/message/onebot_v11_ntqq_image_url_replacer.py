"""
@Author         : Ailitonia
@Date           : 2026/9/12 10:08
@FileName       : onebot_v11_ntqq_image_url_replacer
@Project        : omega-miya
@Description    : 简单粗暴替换 ntqq 图片域名解决证书验证问题
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from nonebot.adapters.onebot.v11 import Bot as OneBotV11Bot
from nonebot.adapters.onebot.v11 import Message as OneBotV11Message
from nonebot.adapters.onebot.v11 import MessageEvent as OneBotV11MessageEvent
from nonebot.adapters.onebot.v11 import MessageSegment as OneBotV11MessageSegment
from nonebot.log import logger
from nonebot.message import event_preprocessor

_ORIGIN_DOMAIN: Literal['https://multimedia.nt.qq.com.cn'] = 'https://multimedia.nt.qq.com.cn'
"""ntqq 原始图片域名"""
_REPLACED_DOMAIN: Literal['https://gchat.qpic.cn'] = 'https://gchat.qpic.cn'
"""替换用图片域名"""


def _replace_image_segment(seg: OneBotV11MessageSegment) -> OneBotV11MessageSegment:
    """替换 image 消息段中图片的 url"""
    if seg.type != 'image':
        return seg

    if (file := seg.data.get('file', None)) is not None and str(file).startswith(_ORIGIN_DOMAIN):
        seg.data['_original_file'] = seg.data['file']
        seg.data['file'] = f'{_REPLACED_DOMAIN}{str(file).removeprefix(_ORIGIN_DOMAIN)}'

    if (url := seg.data.get('url', None)) is not None and str(url).startswith(_ORIGIN_DOMAIN):
        seg.data['_original_url'] = seg.data['url']
        seg.data['url'] = f'{_REPLACED_DOMAIN}{str(url).removeprefix(_ORIGIN_DOMAIN)}'

    return seg


def _replace_message_image(_: OneBotV11Bot, message: OneBotV11Message) -> OneBotV11Message:
    output_message = OneBotV11Message()
    for seg in message:
        if seg.type == 'image':
            try:
                replaced_seg = _replace_image_segment(seg)
                output_message.append(replaced_seg)
            except Exception as e:
                logger.warning(f'replace ntqq image {seg.data} url failed, {e}')
                output_message.append(seg)
        else:
            output_message.append(seg)

    return output_message


@event_preprocessor
async def handle_replace_image_url_event_preprocessor(bot: OneBotV11Bot, event: OneBotV11MessageEvent):
    """事件预处理, 替换 image 消息段中的图片 url 域名"""
    event.message = _replace_message_image(bot, event.message.copy())
    if event.reply is not None:
        event.reply.message = _replace_message_image(bot, event.reply.message.copy())


__all__ = []
