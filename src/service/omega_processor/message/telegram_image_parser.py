"""
@Author         : Ailitonia
@Date           : 2026/9/11 11:06
@FileName       : telegram_image_parser
@Project        : omega-miya
@Description    : Telegram 消息图片解析器, 将 photo 消息段中的图片 file_id 替换为真实图片 url
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from urllib.parse import quote

from nonebot.adapters.telegram import Bot as TelegramBot
from nonebot.adapters.telegram.event import Event as TelegramEvent
from nonebot.adapters.telegram.event import MessageEvent as TelegramMessageEvent
from nonebot.adapters.telegram.message import Message as TelegramMessage
from nonebot.adapters.telegram.message import MessageSegment as TelegramMessageSegment
from nonebot.log import logger
from nonebot.message import event_preprocessor


async def _parse_photo_segment(bot: TelegramBot, seg: TelegramMessageSegment) -> TelegramMessageSegment:
    """解析图片消息段中图片的真实 url"""
    if seg.type not in ['photo', 'sticker']:
        return seg

    file = await bot.get_file(file_id=seg.data.get('file', ''))
    if file.file_path is None:
        return seg

    # 该链接不能直接作为向 Telegram 平台发送图片的 url, 会返回错误: "wrong file identifier/HTTP URL specified"
    url = f'https://api.telegram.org/file/bot{quote(bot.bot_config.token)}/{quote(file.file_path)}'

    seg.data.update({'_parsed_url': url})
    return seg


async def _parse_message(bot: TelegramBot, message: TelegramMessage) -> TelegramMessage:
    output_message = TelegramMessage()
    for seg in message:
        if seg.type in ['photo', 'sticker']:
            try:
                parsed_seg = await _parse_photo_segment(bot=bot, seg=seg)
                output_message.append(parsed_seg)
            except Exception as e:
                logger.warning(f'parsing telegram message image {seg.data} failed, {e}')
                output_message.append(seg)
        else:
            output_message.append(seg)

    return output_message


async def handle_parse_message_image_event_preprocessor(bot: TelegramBot, event: TelegramMessageEvent):
    """事件预处理, 将图片消息段中的图片 file_id 解析为真实图片 url"""
    event.message = await _parse_message(bot=bot, message=event.message.copy())
    if event.reply_to_message:
        event.reply_to_message.message = await _parse_message(bot=bot, message=event.reply_to_message.message.copy())


@event_preprocessor
async def handle_telegram_event_preprocessor(bot: TelegramBot, event: TelegramEvent):
    """事件预处理, 将图片消息段中的图片 file_id 解析为真实图片 url"""
    # 针对消息事件的处理
    if isinstance(event, TelegramMessageEvent):
        # 处理消息段图片解析
        await handle_parse_message_image_event_preprocessor(bot=bot, event=event)


__all__ = []
