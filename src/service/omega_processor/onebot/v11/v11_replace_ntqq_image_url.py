"""
@Author         : Ailitonia
@Date           : 2024/5/26 上午2:03
@FileName       : v11_replace_ntqq_image_url
@Project        : nonebot2_miya
@Description    : 替换 ntqq 图片域名解决证书验证问题
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Callable, Literal, Optional

from nonebot import get_plugin_config, logger
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from pydantic import BaseModel, ConfigDict

type SegReplacerType = Callable[[MessageSegment], MessageSegment]


class OneBotV11ImageUrlReplacerConfig(BaseModel):
    """OneBot V11 图片 URL 替换处理配置"""
    onebot_v11_image_url_replacer: Literal['http', 'domain'] | None = 'http'

    model_config = ConfigDict(extra="ignore")


def _ger_image_url_replacer(replacer: Optional[str]) -> SegReplacerType:
    match replacer:
        case 'http':
            old_ = 'https://'
            new_ = 'http://'
        case 'domain':
            old_ = 'https://multimedia.nt.qq.com.cn'
            new_ = 'https://gchat.qpic.cn'
        case _:
            old_ = ''
            new_ = ''

    def _image_url_replacer(seg: MessageSegment) -> MessageSegment:
        """替换 image 消息段中图片的 url"""
        if seg.type != 'image':
            return seg

        file = seg.data.get('file')
        url = seg.data.get('url')

        if file is not None and str(file).startswith('https://'):
            seg.data['file'] = str(file).replace(old_, new_)

        if url is not None and str(url).startswith('https://'):
            seg.data['url'] = str(url).replace(old_, new_)

        return seg

    return _image_url_replacer


def _get_confined_replacer() -> SegReplacerType:
    try:
        replacer_config = get_plugin_config(OneBotV11ImageUrlReplacerConfig).onebot_v11_image_url_replacer
    except Exception as e:
        logger.warning(f'OneBotV11 图片 Url 替换处理配置验证失败, 错误信息:\n{e}')
        replacer_config = None

    return _ger_image_url_replacer(replacer_config)


_REPLACER: SegReplacerType = _get_confined_replacer()


def _parse_message(message: Message) -> Message:
    output_message = Message()
    for seg in message:
        if seg.type == 'image':
            try:
                replaced_seg = _REPLACER(seg)
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
