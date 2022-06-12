"""
@Author         : Ailitonia
@Date           : 2022/06/12 18:20
@FileName       : api_failed.py
@Project        : nonebot2_miya 
@Description    : api 调用失败处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.exception import ActionFailed


async def handle_send_msg_failed(bot: Bot, exception: Optional[ActionFailed], api: str, data: dict, **_):
    """处理消息发送失败(风控)"""
    send_msg_api = [
        'send_msg',
        'send_private_msg',
        'send_group_msg',
        'send_forward_msg',
        'send_private_forward_msg',
        'send_group_forward_msg',
        'send_guild_channel_msg'
    ]
    if api not in send_msg_api:
        return
    elif not isinstance(exception, ActionFailed):
        return

    failed_msg = Message('消息发送失败, 可能被风控QAQ')
    data.update({'message': failed_msg})

    if data.get('guild_id') and data.get('channel_id'):
        await bot.call_api('send_guild_channel_msg', **data)
    else:
        await bot.call_api('send_msg', **data)


__all__ = [
    'handle_send_msg_failed'
]
