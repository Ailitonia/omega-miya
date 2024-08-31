"""
@Author         : Ailitonia
@Date           : 2021/07/17 22:36
@FileName       : omega_recaller.py
@Project        : nonebot2_miya 
@Description    : 快速撤回 bot 发送的消息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.adapters.onebot.v11 import (
    Bot as OneBotV11Bot,
    MessageEvent as OneBotV11MessageEvent
)
from nonebot.adapters.telegram import Bot as TelegramBot
from nonebot.adapters.telegram.event import (
    PrivateMessageEvent as TelegramPrivateMessageEvent,
    GroupMessageEvent as TelegramGroupMessageEvent
)
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command

from src.service import enable_processor_state

self_recall = on_command(
    'self-recall',
    aliases={'撤回'},
    permission=SUPERUSER,
    priority=10,
    block=True,
    state=enable_processor_state(name='SelfRecall', enable_processor=False),
)


@self_recall.handle()
async def handle_recall_onebot_v11(bot: OneBotV11Bot, event: OneBotV11MessageEvent):
    if event.reply:
        if bot.self_id == str(event.reply.sender.user_id):
            message_id = event.reply.message_id
            try:
                await bot.delete_msg(message_id=message_id)
                logger.success(f'SelfRecall | 撤回了{bot}消息(message_id={message_id!r})')
            except Exception as e:
                logger.error(f'SelfRecall | 撤回{bot}消息(message_id={message_id!r})失败, {e!r}')
                await self_recall.finish('撤回消息部分或全部失败了', at_sender=True)


@self_recall.handle()
async def handle_recall_telegram(bot: TelegramBot, event: TelegramPrivateMessageEvent | TelegramGroupMessageEvent):
    if event.reply_to_message:
        if isinstance(event.reply_to_message, (TelegramPrivateMessageEvent, TelegramGroupMessageEvent)):
            if bot.self_id == str(event.reply_to_message.from_.id):
                chat_id = event.reply_to_message.chat.id
                message_id = event.reply_to_message.message_id
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=message_id)
                    logger.success(f'SelfRecall | 撤回了{bot}消息(chat_id={chat_id!r}, message_id={message_id!r})')
                except Exception as e:
                    logger.error(f'SelfRecall | 撤回{bot}消息(chat_id={chat_id!r}, message_id={message_id!r})失败, {e!r}')
                    await self_recall.finish('撤回消息部分或全部失败了')


__all__ = []
