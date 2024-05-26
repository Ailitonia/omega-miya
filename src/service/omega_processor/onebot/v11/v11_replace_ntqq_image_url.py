"""
@Author         : Ailitonia
@Date           : 2024/5/26 上午2:03
@FileName       : v11_replace_ntqq_image_url
@Project        : nonebot2_miya
@Description    : 替换 ntqq 图片域名解决证书验证问题
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment


def _replace_image_url(seg: MessageSegment) -> MessageSegment:
    """替换 image 消息段中图片的 url 域名"""
    old_ = 'https://multimedia.nt.qq.com.cn'
    new_ = 'https://gchat.qpic.cn'

    if seg.type != 'image':
        return seg

    file = seg.data.get('file')
    url = seg.data.get('url')

    if file is not None and str(file).startswith('https://'):
        seg.data['file'] = str(file).replace(old_, new_)

    if url is not None and str(url).startswith('https://'):
        seg.data['url'] = str(url).replace(old_, new_)

    return seg


def _parse_message(message: Message) -> Message:
    output_message = Message()
    for seg in message:
        if seg.type == 'image':
            try:
                replaced_seg = _replace_image_url(seg=seg)
                output_message.append(replaced_seg)
            except Exception as e:
                logger.warning(f'replace ntqq image {seg.data} url failed, {e}')
                output_message.append(seg)
        else:
            output_message.append(seg)

    return output_message


async def handle_replace_image_url_event_preprocessor(event: MessageEvent):
    """事件预处理, 替换 image 消息段中的图片 url 域名"""
    event.message = _parse_message(message=event.message.copy())


__all__ = [
    'handle_replace_image_url_event_preprocessor'
]
