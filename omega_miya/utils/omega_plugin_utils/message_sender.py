"""
@Author         : Ailitonia
@Date           : 2021/05/27 22:04
@FileName       : message_sender.py
@Project        : nonebot2_miya 
@Description    : Bot Message Sender
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
from nonebot import logger
from typing import Optional, List, Tuple, Union, Any
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.message import Message, MessageSegment
from nonebot.adapters.cqhttp.event import MessageEvent
from omega_miya.database import DBBot, DBBotGroup, DBFriend, DBSubscription


class MsgSentException(Exception):
    pass


class MsgSender(object):
    def __init__(self, bot: Bot, log_flag: Optional[str] = 'DefaultSender'):
        self.bot = bot
        self.self_bot = DBBot(self_qq=int(bot.self_id))
        self.log_flag = f'MsgSender/{log_flag}/Bot[{bot.self_id}]'

    async def safe_broadcast_groups_subscription(
            self, subscription: DBSubscription, message: Union[str, Message, MessageSegment]
    ) -> List[Union[Any, Exception]]:
        """
        向所有具有某个订阅且启用了通知权限 notice permission 的群组发送消息
        """
        # 获取所有需要通知的群组
        notice_group_res = await subscription.sub_group_list_by_notice_permission(self_bot=self.self_bot,
                                                                                  notice_permission=1)
        if notice_group_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send subscription '
                f'{subscription.sub_type}/{subscription.sub_id} broadcast message, '
                f'getting sub group list with notice permission failed, error: {notice_group_res.info}')
            return [MsgSentException('Getting group list failed')]

        result_list = []
        for group_id in notice_group_res.result:
            try:
                result = await self.bot.send_group_msg(group_id=group_id, message=message)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending subscription '
                    f'{subscription.sub_type}/{subscription.sub_id} broadcast message '
                    f'to group: {group_id} failed, error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list

    async def safe_broadcast_groups_subscription_node_custom(
            self, subscription: DBSubscription, message_list: List[Union[str, Message, MessageSegment]],
            *,
            custom_nickname: str = 'Ωμεγα'
    ) -> List[Union[Any, Exception]]:
        """
        向所有具有某个订阅且启用了通知权限 notice permission 的群组发送自定义转发消息节点
        仅支持 cq-http
        """
        # 获取所有需要通知的群组
        notice_group_res = await subscription.sub_group_list_by_notice_permission(self_bot=self.self_bot,
                                                                                  notice_permission=1)
        if notice_group_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send subscription '
                f'{subscription.sub_type}/{subscription.sub_id} broadcast node_custom message, '
                f'getting sub group list with notice permission failed, error: {notice_group_res.info}')
            return [MsgSentException('Getting group list failed')]

        # 构造自定义消息节点
        custom_user_id = self.bot.self_id
        node_message = []
        for msg in message_list:
            if not msg:
                logger.opt(colors=True).warning(
                    f'<Y><lw>{self.log_flag}</lw></Y> | A None-type message in message_list.')
                continue
            node_message.append({
                "type": "node",
                "data": {
                    "name": custom_nickname,
                    "user_id": custom_user_id,
                    "uin": custom_user_id,
                    "content": msg
                }
            })

        result_list = []
        for group_id in notice_group_res.result:
            try:
                result = await self.bot.send_group_forward_msg(group_id=group_id, messages=node_message)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending subscription '
                    f'{subscription.sub_type}/{subscription.sub_id} broadcast node_custom message '
                    f'to group: {group_id} failed, error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list

    async def safe_send_group_node_custom(
            self, group_id: int, message_list: List[Union[str, Message, MessageSegment]],
            *,
            custom_nickname: str = 'Ωμεγα'
    ) -> Union[Any, Exception]:
        """
        向某个群组发送自定义转发消息节点
        仅支持 cq-http
        """
        # 构造自定义消息节点
        custom_user_id = self.bot.self_id
        node_message = []
        for msg in message_list:
            if not msg:
                logger.opt(colors=True).warning(
                    f'<Y><lw>{self.log_flag}</lw></Y> | A None-type message in message_list.')
                continue
            node_message.append({
                "type": "node",
                "data": {
                    "name": custom_nickname,
                    "user_id": custom_user_id,
                    "uin": custom_user_id,
                    "content": msg
                }
            })

        try:
            result = await self.bot.send_group_forward_msg(group_id=group_id, messages=node_message)
            return result
        except Exception as e:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Sending node_custom message '
                f'to group: {group_id} failed, error: {repr(e)}')
            return e

    async def safe_broadcast_friends_subscription(
            self, subscription: DBSubscription, message: Union[str, Message, MessageSegment]
    ) -> List[Union[Any, Exception]]:
        """
        向所有具有某个订阅且启用了通知权限 notice permission 的好友发送消息
        """
        # 获取所有需要通知的好友
        notice_friends_res = await subscription.sub_user_list_by_private_permission(self_bot=self.self_bot,
                                                                                    private_permission=1)
        if notice_friends_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send subscription '
                f'{subscription.sub_type}/{subscription.sub_id} broadcast message, '
                f'getting sub friends list with private permission failed, error: {notice_friends_res.info}')
            return [MsgSentException('Getting friends list failed')]

        result_list = []
        for user_id in notice_friends_res.result:
            try:
                result = await self.bot.send_private_msg(user_id=user_id, message=message)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending subscription '
                    f'{subscription.sub_type}/{subscription.sub_id} broadcast message '
                    f'to user: {user_id} failed, error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list

    async def safe_send_msg_enabled_friends(
            self, message: Union[str, Message, MessageSegment]
    ) -> List[Union[Any, Exception]]:
        """
        向所有具有好友权限 private permission (已启用bot命令) 的好友发送消息
        """
        # 获取所有启用 private permission 好友
        enabled_friends_res = await DBFriend.list_exist_friends_by_private_permission(self_bot=self.self_bot,
                                                                                      private_permission=1)
        if enabled_friends_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send message to friends, '
                f'getting enabled friends list with private permission failed, error: {enabled_friends_res.info}')
            return [MsgSentException('Getting friends list failed')]

        result_list = []
        for user_id in enabled_friends_res.result:
            try:
                result = await self.bot.send_private_msg(user_id=user_id, message=message)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending message to friend: {user_id} failed, error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list

    async def safe_send_msg_all_friends(
            self, message: Union[str, Message, MessageSegment]
    ) -> List[Union[Any, Exception]]:
        """
        向所有好友发送消息
        """
        # 获取数据库中所有好友
        all_friends_res = await DBFriend.list_exist_friends(self_bot=self.self_bot)
        if all_friends_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send message to friends, '
                f'getting all friends list with private permission failed, error: {all_friends_res.info}')
            return [MsgSentException('Getting friends list failed')]

        result_list = []
        for user_id in all_friends_res.result:
            try:
                result = await self.bot.send_private_msg(user_id=user_id, message=message)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending message to friend: {user_id} failed, error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list

    async def safe_send_msg_enabled_command_groups(
            self, message: Union[str, Message, MessageSegment]
    ) -> List[Union[Any, Exception]]:
        """
        向所有具有命令权限 command permission 的群组发送消息
        """
        # 获取所有需要通知的群组
        command_group_res = await DBBotGroup.list_exist_bot_groups_by_command_permissions(self_bot=self.self_bot,
                                                                                          command_permissions=1)
        if command_group_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send subscription message to command groups, '
                f'getting command group list failed, error: {command_group_res.info}')
            return [MsgSentException('Getting group list failed')]

        result_list = []
        for group_id in command_group_res.result:
            try:
                result = await self.bot.send_group_msg(group_id=group_id, message=message)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending message to group: {group_id} failed, error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list

    async def safe_send_msg_enabled_notice_groups(
            self, message: Union[str, Message, MessageSegment]
    ) -> List[Union[Any, Exception]]:
        """
        向所有具有通知权限 notice permission 的群组发送消息
        """
        # 获取所有需要通知的群组
        notice_group_res = await DBBotGroup.list_exist_bot_groups_by_notice_permissions(self_bot=self.self_bot,
                                                                                        notice_permissions=1)
        if notice_group_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send subscription message to notice groups, '
                f'getting notice group list failed, error: {notice_group_res.info}')
            return [MsgSentException('Getting group list failed')]

        result_list = []
        for group_id in notice_group_res.result:
            try:
                result = await self.bot.send_group_msg(group_id=group_id, message=message)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending message to group: {group_id} failed, error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list

    async def safe_send_msg_permission_level_groups(
            self, permission_level: int, message: Union[str, Message, MessageSegment]
    ) -> List[Union[Any, Exception]]:
        """
        向所有大于等于指定权限等级 permission level 的群组发送消息
        """
        # 获取所有需要通知的群组
        level_group_res = await DBBotGroup.list_exist_bot_groups_by_permission_level(self_bot=self.self_bot,
                                                                                     permission_level=permission_level)
        if level_group_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send subscription message to groups had level, '
                f'getting permission level group list failed, error: {level_group_res.info}')
            return [MsgSentException('Getting group list failed')]

        result_list = []
        for group_id in level_group_res.result:
            try:
                result = await self.bot.send_group_msg(group_id=group_id, message=message)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending message to group: {group_id} failed, error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list

    async def safe_send_msg_all_groups(
            self, message: Union[str, Message, MessageSegment]
    ) -> List[Union[Any, Exception]]:
        """
        向所有群组发送消息
        """
        # 获取所有需要通知的群组
        all_group_res = await DBBotGroup.list_exist_bot_groups(self_bot=self.self_bot)
        if all_group_res.error:
            logger.opt(colors=True).error(
                f'<Y><lw>{self.log_flag}</lw></Y> | Can not send subscription message to all groups, '
                f'getting permission all group list failed, error: {all_group_res.info}')
            return [MsgSentException('Getting group list failed')]

        result_list = []
        for group_id in all_group_res.result:
            try:
                result = await self.bot.send_group_msg(group_id=group_id, message=message)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Sending message to group: {group_id} failed, error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list

    async def safe_send_msgs_and_recall(
            self, event: MessageEvent, message_list: List[Union[str, Message, MessageSegment]],
            *,
            recall_time: int = 20
    ) -> Tuple[List[Union[Any, Exception]], List[Union[Any, Exception]]]:
        """
        发送消息后并自动撤回
        """
        sent_msg_ids = []
        sent_results = []
        for msg_seg in message_list:
            try:
                sent_result = await self.bot.send(event=event, message=msg_seg)
                sent_results.append(sent_result)
                sent_msg_ids.append(sent_result.get('message_id') if isinstance(sent_result, dict) else None)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Auto-recall-message send message failed '
                    f'in event: {event.get_session_id()}, error: {repr(e)}')
                sent_results.append(e)
                continue

        logger.opt(colors=True).info(
            f'<G><lw>{self.log_flag}</lw></G> | Auto-recall-message will recall message '
            f'after {recall_time} second(s) in event: {event.get_session_id()}')
        await asyncio.sleep(recall_time)

        delete_results = []
        for msg_id in sent_msg_ids:
            if not msg_id:
                delete_results.append(None)
                continue
            try:
                delete_result = await self.bot.delete_msg(message_id=msg_id)
                delete_results.append(delete_result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Auto-recall-message recalling failed '
                    f'in event: {event.get_session_id()}, msg_id: {msg_id}. error: {repr(e)}')
                delete_results.append(e)
                continue
        return sent_results, delete_results

    async def safe_send_msgs(
            self, event: MessageEvent, message_list: List[Union[str, Message, MessageSegment]]
    ) -> List[Union[Any, Exception]]:
        """
        向某个群组发送多条消息
        """
        result_list = []
        for msg_seg in message_list:
            try:
                result = await self.bot.send(event=event, message=msg_seg)
                result_list.append(result)
            except Exception as e:
                logger.opt(colors=True).error(
                    f'<Y><lw>{self.log_flag}</lw></Y> | Send group message failed in event: {event.get_session_id()}, '
                    f'error: {repr(e)}')
                result_list.append(e)
                continue
        return result_list


__all__ = [
    'MsgSender'
]
