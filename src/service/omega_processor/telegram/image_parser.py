"""
@Author         : Ailitonia
@Date           : 2023/6/12 1:06
@FileName       : image_parser
@Project        : nonebot2_miya
@Description    : Telegram 消息图片解析器, 将 photo 消息段中的图片 file_id 替换为真实图片 url
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from urllib.parse import quote

from nonebot.log import logger
from nonebot.adapters.telegram.bot import Bot
from nonebot.adapters.telegram.event import MessageEvent
from nonebot.adapters.telegram.message import Message, MessageSegment, File

from src.service.omega_requests import OmegaRequests
from src.resource import TemporaryResource


async def handle_parse_message_image_event_preprocessor(bot: Bot, event: MessageEvent):
    """事件预处理, 将 photo 消息段中的图片 file_id 替换为真实图片 url"""
    origin_message = event.message.copy()
    message = Message()

    for seg in origin_message:
        if seg.type == 'photo':
            try:
                parsed_seg = await parse_photo_segment(bot=bot, seg=seg)
                message.append(parsed_seg)
            except Exception as e:
                logger.warning(f'parsing telegram message image {seg.data} failed, {e}')
                message.append(seg)
        else:
            message.append(seg)

    event.message = message


async def parse_photo_segment(bot: Bot, seg: MessageSegment) -> MessageSegment:
    """解析 photo 消息段中图片的真实 url"""
    if seg.type != 'photo':
        return seg

    file = await bot.get_file(file_id=seg.data.get('file'))
    url = f"https://api.telegram.org/file/bot{quote(bot.bot_config.token)}/{quote(file.file_path)}"
    # 该链接不能直接作为发送图片的 url, 会返回错误: "wrong file identifier/HTTP URL specified"

    img_path = TemporaryResource('telegram', 'tmp', 'images')
    img_target_file = img_path(f'{file.file_unique_id}_{OmegaRequests.hash_url_file_name("photo", url=url)}')
    await OmegaRequests().download(url=url, file=img_target_file)

    parsed_seg = File.photo(file=img_target_file.resolve_path, has_spoiler=seg.data.get('has_spoiler'))

    return parsed_seg


__all__ = [
    'handle_parse_message_image_event_preprocessor'
]
