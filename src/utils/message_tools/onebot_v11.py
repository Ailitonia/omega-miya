"""
@Author         : Ailitonia
@Date           : 2022/12/11 20:44
@FileName       : onebot_v11.py
@Project        : nonebot2_miya 
@Description    : OneBot v11 消息工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
import ujson as json
from copy import deepcopy
from nonebot import get_bot, logger
from nonebot.adapters.onebot.v11.bot import Bot
from nonebot.adapters.onebot.v11.event import Event, GroupMessageEvent, PrivateMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment

from src.service.onebot_api.v11 import Gocqhttp
from src.service.omega_base import OmegaEntity
from src.service.gocqhttp_guild_patch import GuildMessageEvent
from src.service.omega_requests import OmegaRequests
from src.utils.process_utils import semaphore_gather

from .config import message_tools_config


class OneBotV11MessageSender(object):
    """OneBot v11 消息发送工具集"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @classmethod
    def init_from_bot_self_id(cls, bot_id: str) -> "OneBotV11MessageSender":
        bot = get_bot(self_id=bot_id)
        return cls(bot=bot)

    async def send_entity_msg(
            self,
            entity: OmegaEntity,
            message: str | Message | MessageSegment
    ) -> int:
        """根据 Entity 对象发送消息"""
        bot = Gocqhttp(bot=self.bot)
        match entity.entity_type:
            case 'qq_user':
                sent_result = await bot.send_private_msg(user_id=entity.entity_id, message=message)
            case 'qq_group':
                sent_result = await bot.send_group_msg(group_id=entity.entity_id, message=message)
            case 'qq_guild_channel':
                sent_result = await bot.send_guild_channel_msg(guild_id=entity.parent_id, channel_id=entity.entity_id,
                                                               message=message)
            case _:
                raise ValueError(f'Entity({entity.entity_type}) not support send message')

        return sent_result.message_id

    @staticmethod
    def _construct_node_custom(
            custom_user_id: int,
            message_list: list[str | Message | MessageSegment],
            custom_nickname: str = 'Ωμεγα_Μιγα'
    ) -> list[dict]:
        """构造自定义转发消息节点"""
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
        return node_message

    async def send_node_custom(
            self,
            message_list: list[str | Message | MessageSegment],
            user_id: int | str | None = None,
            group_id: int | str | None = None,
            event: Event | None = None,
            *,
            custom_nickname: str = 'Ωμεγα_Μιγα'
    ) -> int:
        """发送自定义转发消息节点 (仅支持 cq-http)"""
        bot = Gocqhttp(bot=self.bot)

        # 构造自定义消息节点
        node_message = self._construct_node_custom(custom_user_id=bot.self_id, custom_nickname=custom_nickname,
                                                   message_list=message_list)

        if isinstance(event, GroupMessageEvent):
            sent_result = await bot.send_group_forward_msg(group_id=event.group_id, messages=node_message)
        elif isinstance(event, PrivateMessageEvent):
            sent_result = await bot.send_private_forward_msg(user_id=event.user_id, messages=node_message)
        else:
            sent_result = await bot.send_forward_msg(user_id=user_id, group_id=group_id, messages=node_message)

        return sent_result.message_id

    async def send_node_custom_and_recall(
            self,
            message_list: list[str | Message | MessageSegment],
            user_id: int | str | None = None,
            group_id: int | str | None = None,
            event: Event | None = None,
            *,
            recall_time: int = 30,
            custom_nickname: str = 'Ωμεγα_Μιγα'
    ) -> asyncio.TimerHandle:
        """发送自定义转发消息节点并在指定时间后自动撤回 (仅支持 cq-http)"""
        message_id = await self.send_node_custom(message_list=message_list, user_id=user_id, group_id=group_id,
                                                 event=event, custom_nickname=custom_nickname)

        logger.opt(colors=True).debug(
            f'<lc>MessageSender</lc>| Message({message_id}) will be auto-recalled after {recall_time} seconds'
        )

        loop = asyncio.get_running_loop()
        return loop.call_later(
            recall_time,
            lambda: loop.create_task(self.bot.delete_msg(message_id=message_id)),
        )

    async def send_msgs_and_recall(
            self,
            event: Event,
            message_list: list[str | Message | MessageSegment],
            *,
            recall_time: int = 30
    ) -> asyncio.TimerHandle | None:
        """发出多条消息消息并在指定时间后自动撤回"""
        send_tasks = [self.bot.send(event=event, message=msg) for msg in message_list]
        sent_results = await semaphore_gather(tasks=send_tasks, semaphore_num=1)

        if isinstance(event, GuildMessageEvent):
            logger.opt(colors=True).debug('<lc>MessageSender</lc> | Can not recall message in guild-channel, ignore')
            return

        sent_msg = [x for x in sent_results if not isinstance(x, BaseException)]
        recall_tasks = [self.bot.delete_msg(message_id=msg["message_id"]) for msg in sent_msg]

        logger.opt(colors=True).debug(
            f'<lc>MessageSender</lc>| Messages({", ".join(str(x["message_id"]) for x in sent_msg)}) '
            f'will be auto-recalled after {recall_time} seconds'
        )

        loop = asyncio.get_running_loop()
        return loop.call_later(
            recall_time,
            lambda: loop.create_task(semaphore_gather(tasks=recall_tasks, semaphore_num=1)),
        )


def extract_image_urls(message: Message) -> list[str]:
    """提取消息中的图片链接"""
    return [
        segment.data["url"]
        for segment in message
        if (segment.type == "image") and ("url" in segment.data)
    ]


def extract_at_qq(message: Message) -> list[int]:
    """提取消息中的被@人的qq(不包括@所有人)"""
    return [
        int(qq)
        for qq in (
            segment.data["qq"]
            for segment in message
            if (segment.type == "at") and ("qq" in segment.data)
        )
        if str(qq).isdigit()
    ]


async def dumps_with_image(message: Message) -> str:
    """将 Message 转化为 json 字符串导出"""
    segments = []
    for segment in message:
        # 缓存消息中图片
        if segment.type == 'image' and 'url' in segment.data:
            file = message_tools_config.tmp_message_data_folder(
                'onebot_v11', 'image', OmegaRequests.hash_url_file_name('image', url=segment.data['url'])
            )
            await OmegaRequests().download(url=segment.data['url'], file=file)
            data = deepcopy(segment.data)
            data.pop('url')
            data.update({'file': file.file_uri})
            segments.append({'type': segment.type, 'data': data})
        else:
            segments.append({"type": segment.type, "data": segment.data})

    message_data = json.dumps(segments, ensure_ascii=False)
    return message_data


def dumps(message: Message) -> str:
    """将 Message 转化为 json 字符串导出"""
    message_data = json.dumps([{"type": seg.type, "data": seg.data} for seg in message], ensure_ascii=False)
    return message_data


def loads(message_data: str) -> Message:
    """将导出的消息 json 字符串转化为 Message 对象"""
    message = Message(MessageSegment(**seg) for seg in json.loads(message_data))
    return message


def filter_message(message: Message, allow_type: list[str] | None = None) -> Message:
    """过滤消息, 仅保留允许的消息段类型

    :param message: 待过滤的消息
    :param allow_type: 允许的消息段类型, 默认为 text
    :return: 过滤后的 Message
    """
    allow_type = ['text'] if allow_type is None else allow_type

    filtered_msg_seg = [msg_seg for msg_seg in message if msg_seg.type in allow_type]
    return Message(filtered_msg_seg)


__all__ = [
    'OneBotV11MessageSender',
    'extract_image_urls',
    'extract_at_qq',
    'dumps_with_image',
    'dumps',
    'loads',
    'filter_message'
]
