"""
@Author         : Ailitonia
@Date           : 2021/08/14 19:42
@FileName       : message_tools.py
@Project        : nonebot2_miya 
@Description    : 消息解析工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
import ujson as json
from nonebot import get_bot
from nonebot.log import logger
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.message import Message, MessageSegment
from nonebot.adapters.onebot.v11.event import Event

from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.database import EventEntityHelper
from omega_miya.database.internal.entity import BaseInternalEntity
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather


class MessageTools(object):
    def __init__(self, message: Message):
        self._message = message

    @classmethod
    def dumps(cls, message: Message) -> str:
        """将 Message 转化为 json 字符串导出"""
        message_data = json.dumps([{"type": seg.type, "data": seg.data} for seg in message], ensure_ascii=False)
        return message_data

    @classmethod
    def loads(cls, message_data: str) -> Message:
        """将导出的消息 json 字符串转化为 Message 对象"""
        message = Message(MessageSegment(**seg) for seg in json.loads(message_data))
        return message

    def filter_message_segment(self, *args: str) -> Message:
        """过滤消息, 仅保留允许的消息段类型

        :param args: 允许的消息段类型
        :return: 过滤后的 Message
        """
        filtered_msg_seg = [msg_seg for msg_seg in self._message if msg_seg.type in args]
        return Message(filtered_msg_seg)

    def get_all_img_url(self) -> list[str]:
        """获取消息中所有图片的 url"""
        return [str(msg_seg.data.get('url')) for msg_seg in self._message if msg_seg.type == 'image']

    def get_all_at_qq(self) -> list[int]:
        """获取消息中所有被 @ 人的 qq (不包括 @所有人)"""
        at_list = [msg_seg.data.get('qq') for msg_seg in self._message if msg_seg.type == 'at']
        return [int(at_text) for at_text in at_list if str(at_text).isdigit()]


class MessageSender(object):
    def __init__(self, bot: Bot):
        self.bot = GoCqhttpBot(bot=bot)

    @classmethod
    def init_from_bot_id(cls, bot_id: str) -> "MessageSender":
        bot = get_bot(self_id=bot_id)
        return cls(bot=bot)

    @run_async_catching_exception
    async def send_internal_entity_msg(
            self,
            entity: BaseInternalEntity,
            message: str | Message | MessageSegment
    ) -> int:
        """根据 InternalEntity 对象发送消息"""
        match entity.relation.relation_type:
            case 'bot_group':
                sent_result = await self.bot.send_group_msg(group_id=entity.entity_id, message=message)
            case 'bot_user':
                sent_result = await self.bot.send_private_msg(user_id=entity.entity_id, message=message)
            case 'group_user':
                sent_result = await self.bot.send_stranger_msg(group_id=entity.parent_id, user_id=entity.entity_id,
                                                               message=message)
            case 'guild_channel':
                sent_result = await self.bot.send_guild_channel_msg(guild_id=entity.parent_id,
                                                                    channel_id=entity.entity_id, message=message)
            case _:
                raise ValueError(f'InternalEntity({entity.relation}) not support send message')

        return sent_result.message_id

    @run_async_catching_exception
    async def send_group_node_custom(
            self,
            group_id: int | str,
            message_list: list[str | Message | MessageSegment],
            *,
            custom_nickname: str = 'Ωμεγα_Μιγα'
    ) -> int:
        """向某个群组发送自定义转发消息节点 (仅支持 cq-http)"""
        # 构造自定义消息节点
        custom_user_id = self.bot.self_id
        node_message = []
        for msg in message_list:
            if not msg:
                continue
            node_message.append({
                'type': 'node',
                'data': {
                    'name': custom_nickname,
                    'user_id': custom_user_id,
                    'uin': custom_user_id,
                    'content': msg
                }
            })

        sent_result = await self.bot.send_group_forward_msg(group_id=group_id, messages=node_message)
        return sent_result.message_id

    @run_async_catching_exception
    async def send_group_node_custom_and_recall(
            self,
            group_id: int | str,
            message_list: list[str | Message | MessageSegment],
            *,
            recall_time: int = 30,
            custom_nickname: str = 'Ωμεγα_Μιγα'
    ) -> int:
        """向某个群组发送自定义转发消息节点并自动撤回 (仅支持 cq-http)"""
        # 构造自定义消息节点
        custom_user_id = self.bot.self_id
        node_message = []
        for msg in message_list:
            if not msg:
                continue
            node_message.append({
                'type': 'node',
                'data': {
                    'name': custom_nickname,
                    'user_id': custom_user_id,
                    'uin': custom_user_id,
                    'content': msg
                }
            })

        sent_result = await self.bot.send_group_forward_msg(group_id=group_id, messages=node_message)
        await asyncio.sleep(recall_time)
        await self.bot.delete_msg(message_id=sent_result.message_id)
        return sent_result.message_id

    @run_async_catching_exception
    async def send_msgs_and_recall(
            self,
            event: Event,
            message_list: list[str | Message | MessageSegment],
            *,
            recall_time: int = 30
    ) -> list[int]:
        """发送消息后并自动撤回"""
        entity = EventEntityHelper(bot=self.bot.bot, event=event).get_event_entity()
        send_tasks = [self.send_internal_entity_msg(entity=entity, message=msg) for msg in message_list]

        sent_results = await semaphore_gather(tasks=send_tasks, semaphore_num=1)
        exceptions = [x for x in sent_results if isinstance(x, Exception)]
        sent_msg_id = [x for x in sent_results if not isinstance(x, Exception)]

        if entity.relation_type == 'guild_channel':
            logger.opt(colors=True).debug('<lc>MessageSender</lc> | Can not recall message in guild-channel, ignore')
            if exceptions:
                raise RuntimeError(*exceptions)
            return [x for x in sent_results if not isinstance(x, Exception)]
        else:
            logger.opt(colors=True).debug(f'<lc>MessageSender</lc>| Message({", ".join(str(x) for x in sent_msg_id)}) '
                                          f'will be auto-recalled after {recall_time} seconds')

        await asyncio.sleep(recall_time)

        delete_tasks = [self.bot.delete_msg(message_id=msg_id) for msg_id in sent_msg_id]
        delete_results = await semaphore_gather(tasks=delete_tasks, semaphore_num=1)
        exceptions.extend(x for x in delete_results if isinstance(x, Exception))

        if exceptions:
            raise RuntimeError(*exceptions)

        return sent_msg_id


__all__ = [
    'MessageTools',
    'MessageSender'
]
