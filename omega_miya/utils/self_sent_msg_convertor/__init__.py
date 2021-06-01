"""
@Author         : Ailitonia
@Date           : 2021/05/31 21:14
@FileName       : __init__.py.py
@Project        : nonebot2_miya
@Description    : go-cqhttp 适配专用, 用于人工登陆 bot 时将自己发送的消息转成 message 类型便于执行命令, 需将 bot 设置为 SUPERUSER
                  bot 账号发送命令前添加 !SC 即可将消息事件由 message_sent 转换为 group_message, 仅限群组中生效
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""
import re
from datetime import datetime
from nonebot import logger
from nonebot.plugin import on
from nonebot.typing import T_State
from nonebot.message import handle_event
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import Message
from nonebot.adapters.cqhttp.event import Event, GroupMessageEvent


self_sent_msg_convertor = on(
    type='message_sent',
    priority=10,
    block=False
)


@self_sent_msg_convertor.handle()
async def _handle(bot: Bot, event: Event, state: T_State):
    self_id = event.dict().get('self_id', -1)
    user_id = event.dict().get('user_id', -1)

    try:
        if self_id == user_id and str(self_id) == bot.self_id and str(self_id) in bot.config.superusers:
            raw_message = event.dict().get('raw_message', '')
            if str(raw_message).startswith('!SC'):
                raw_message = re.sub(r'^!SC', '', str(raw_message)).strip()
                message = Message(raw_message)
                time = event.dict().get('time', int(datetime.now().timestamp()))
                sub_type = event.dict().get('sub_type', 'normal')
                group_id = event.dict().get('group_id', -1)
                message_type = event.dict().get('message_type', 'group')
                message_id = event.dict().get('message_id', -1)
                font = event.dict().get('font', 0)
                sender = event.dict().get('sender', {'user_id': user_id})

                new_event = GroupMessageEvent(**{
                    'time': time,
                    'self_id': self_id,
                    'post_type': 'message',
                    'sub_type': sub_type,
                    'user_id': user_id,
                    'group_id': group_id,
                    'message_type': message_type,
                    'message_id': message_id,
                    'message': message,
                    'raw_message': raw_message,
                    'font': font,
                    'sender': sender
                })

                await handle_event(bot=bot, event=new_event)
    except Exception as e:
        logger.error(f'Self sent msg convertor convert an self_sent event failed, error: {repr(e)}, event: {event}.')
