"""
@Author         : Ailitonia
@Date           : 2021/05/31 21:14
@FileName       : __init__.py.py
@Project        : nonebot2_miya
@Description    : go-cqhttp 适配专用, 用于人工同时登陆 bot 账号时将自己发送的消息转成 message 类型便于执行命令,
                  bot 账号发送命令前添加 !SU 即可将消息事件由 message_sent 转换为 group_message, 仅限群组中生效,
                  为避免命令恶意执行, bot 不能为 superuser
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re
from datetime import datetime
from nonebot import logger
from nonebot.plugin import on, CommandGroup
from nonebot.typing import T_State
from nonebot.message import handle_event
from nonebot.rule import to_me
from nonebot.permission import SUPERUSER
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import Message
from nonebot.adapters.cqhttp.event import Event, MessageEvent, GroupMessageEvent


SU_TAG: bool = False

# 注册事件响应器
Su = CommandGroup('Su', rule=to_me(), permission=SUPERUSER, priority=10, block=True)

su_on = Su.command('on', aliases={'EnableSu'})
su_off = Su.command('off', aliases={'DisableSu'})


@su_on.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    global SU_TAG
    SU_TAG = True
    logger.info(f'Su: 特权命令已启用, 下一条!SU命令将以管理员身份执行')
    await su_on.finish(f'特权命令已启用, 下一条!SU命令将以管理员身份执行')


@su_off.handle()
async def handle_first_receive(bot: Bot, event: MessageEvent, state: T_State):
    global SU_TAG
    SU_TAG = False
    logger.info(f'Su: 特权命令已禁用')
    await su_off.finish(f'特权命令已禁用')


self_sent_msg_convertor = on(
    type='message_sent',
    priority=10,
    block=False
)


@self_sent_msg_convertor.handle()
async def _handle(bot: Bot, event: Event, state: T_State):
    self_id = event.self_id
    user_id = getattr(event, 'user_id', -1)
    if self_id == user_id and str(self_id) == bot.self_id and str(self_id) not in bot.config.superusers:
        raw_message = getattr(event, 'raw_message', '')
        if str(raw_message).startswith('!SU'):
            global SU_TAG
            try:
                if SU_TAG and list(bot.config.superusers):
                    user_id = int(list(bot.config.superusers)[0])
                raw_message = re.sub(r'^!SU', '', str(raw_message)).strip()
                message = Message(raw_message)
                time = getattr(event, 'time', int(datetime.now().timestamp()))
                sub_type = getattr(event, 'sub_type', 'normal')
                group_id = getattr(event, 'group_id', -1)
                message_type = getattr(event, 'message_type', 'group')
                message_id = getattr(event, 'message_id', -1)
                font = getattr(event, 'font', 0)
                sender = getattr(event, 'sender', {'user_id': user_id})

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
                logger.error(f'Self sent msg convertor convert an self_sent event failed, '
                             f'error: {repr(e)}, event: {event}.')
            finally:
                SU_TAG = False
                logger.info(f'Su: !SU命令已执行, SU_TAG已复位.')
