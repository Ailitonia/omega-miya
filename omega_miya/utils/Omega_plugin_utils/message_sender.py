"""
@Author         : Ailitonia
@Date           : 2021/05/27 22:04
@FileName       : message_sender.py
@Project        : nonebot2_miya 
@Description    : Bot Message Sender
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from typing import Optional, Union
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import Message, MessageSegment
from omega_miya.utils.Omega_Base import DBBot, DBSubscription


class MsgSender(object):
    def __init__(self, bot: Bot, log_flag: Optional[str] = 'DefaultSender'):
        self.bot = bot
        self.self_bot = DBBot(self_qq=int(bot.self_id))
        self.log_flag = f'MsgSender/{log_flag}/Bot<{bot.self_id}>'

    async def safe_broadcast_groups_subscription(
            self, subscription: DBSubscription, message: Union[str, Message, MessageSegment]):
        # 获取所有需要通知的群组
        notice_group_res = await subscription.sub_group_list_by_notice_permission(self_bot=self.self_bot,
                                                                                  notice_permission=1)
        if notice_group_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send subscription '
                f'{subscription.sub_type}/{subscription.sub_id} broadcast message, '
                f'get sub group list with notice permission failed, error: {notice_group_res.info}')
            return

        for group_id in notice_group_res.result:
            try:
                await self.bot.send_group_msg(group_id=group_id, message=message)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending subscription '
                    f'{subscription.sub_type}/{subscription.sub_id} broadcast message '
                    f'to group: {group_id} failed, error: {repr(e)}')
                continue

    async def safe_broadcast_friends_subscription(
            self, subscription: DBSubscription, message: Union[str, Message, MessageSegment]):
        # 获取所有需要通知的好友
        notice_friends_res = await subscription.sub_user_list_by_private_permission(self_bot=self.self_bot,
                                                                                    private_permission=1)
        if notice_friends_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send subscription '
                f'{subscription.sub_type}/{subscription.sub_id} broadcast message, '
                f'get sub friends list with private permission failed, error: {notice_friends_res.info}')
            return

        for user_id in notice_friends_res.result:
            try:
                await self.bot.send_private_msg(user_id=user_id, message=message)
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending subscription '
                    f'{subscription.sub_type}/{subscription.sub_id} broadcast message '
                    f'to user: {user_id} failed, error: {repr(e)}')
                continue


__all__ = [
    'MsgSender'
]
