"""
@Author         : Ailitonia
@Date           : 2021/06/12 0:28
@FileName       : invite_request.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import on_request, on_notice, logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import MessageSegment, Message
from nonebot.adapters.cqhttp.event import FriendRequestEvent, GroupRequestEvent, GroupIncreaseNoticeEvent
from omega_miya.utils.Omega_Base import DBBot, DBBotGroup

# 注册事件响应器
add_and_invite_request = on_request(priority=100)


# 处理加好友申请
@add_and_invite_request.handle()
async def handle_friend_request(bot: Bot, event: FriendRequestEvent, state: T_State):
    user_id = event.user_id
    detail_type = event.request_type
    comment = event.comment

    # 加好友验证消息
    auth_str = f'Miya好萌好可爱{int(user_id) % 9}'

    if detail_type == 'friend' and comment == auth_str:
        await bot.call_api('set_friend_add_request', flag=event.flag, approve=True)
        logger.info(f'已同意用户: {user_id} 的好友申请')
    elif detail_type == 'friend':
        await bot.call_api('set_friend_add_request', flag=event.flag, approve=False)
        logger.info(f'已拒绝用户: {user_id} 的好友申请')


# 处理被邀请进群
@add_and_invite_request.handle()
async def handle_group_invite(bot: Bot, event: GroupRequestEvent, state: T_State):
    user_id = event.user_id
    group_id = event.group_id
    sub_type = event.sub_type
    detail_type = event.request_type
    if detail_type == 'group' and sub_type == 'invite':
        await bot.call_api('set_group_add_request', flag=event.flag, sub_type='invite', approve=True)
        logger.info(f'已处理群组请求, 被用户: {user_id} 邀请加入群组: {group_id}.')


__all__ = [
    'add_and_invite_request'
]
