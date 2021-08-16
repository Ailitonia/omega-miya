"""
@Author         : Ailitonia
@Date           : 2021/07/29 4:14
@FileName       : history.py
@Project        : nonebot2_miya 
@Description    : 历史记录模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from nonebot.typing import T_State
from nonebot.adapters.cqhttp.bot import Bot
from nonebot.adapters.cqhttp.event import (Event, MessageEvent, PrivateMessageEvent, GroupMessageEvent,
                                           NoticeEvent, RequestEvent, MetaEvent)
from omega_miya.database import DBHistory


async def postprocessor_history(bot: Bot, event: Event, state: T_State):
    try:
        time = event.time
        self_id = event.self_id
        post_type = event.post_type
        if isinstance(event, MetaEvent):
            # 不记录元事件
            return
        elif isinstance(event, MessageEvent):
            detail_type = event.message_type
            sub_type = event.sub_type
            event_id = event.message_id
            if isinstance(event, GroupMessageEvent):
                group_id = event.group_id
            elif isinstance(event, PrivateMessageEvent):
                group_id = 0
            else:
                group_id = -1
            user_id = event.user_id
            user_name = f'{event.sender.nickname}/{event.sender.card}'
            raw_data = repr(event)
            msg_data = str(event.message)
        elif isinstance(event, NoticeEvent):
            detail_type = event.notice_type
            sub_type = getattr(event, 'sub_type', 'Undefined')
            event_id = -1
            group_id = getattr(event, 'group_id', -1)
            user_id = getattr(event, 'user_id', -1)
            user_name = ''
            raw_data = repr(event)
            msg_data = ''
        elif isinstance(event, RequestEvent):
            detail_type = event.request_type
            sub_type = getattr(event, 'sub_type', 'Undefined')
            event_id = -1
            group_id = getattr(event, 'group_id', -1)
            user_id = getattr(event, 'user_id', -1)
            user_name = ''
            raw_data = repr(event)
            msg_data = ''
        else:
            detail_type = event.get_event_name()
            sub_type = getattr(event, 'sub_type', 'Undefined')
            event_id = -1
            group_id = getattr(event, 'group_id', -1)
            user_id = getattr(event, 'user_id', -1)
            user_name = ''
            raw_data = repr(event)
            msg_data = getattr(event, 'message', None)

        raw_data = str(raw_data) if not isinstance(raw_data, str) else raw_data
        msg_data = str(msg_data) if not isinstance(msg_data, str) else msg_data
        if len(raw_data) > 4096:
            logger.warning(f'History raw_data is longer than field limited and it will be reduce, <{raw_data}>')
            raw_data = raw_data[:4096]
        if len(msg_data) > 4096:
            logger.warning(f'History raw_data is longer than field limited and it will be reduce, <{msg_data}>')
            msg_data = msg_data[:4096]

        new_history = DBHistory(time=time, self_id=self_id, post_type=post_type, detail_type=detail_type)
        add_result = await new_history.add(
            sub_type=sub_type, event_id=event_id, group_id=group_id, user_id=user_id, user_name=user_name,
            raw_data=raw_data, msg_data=msg_data)
        if add_result.error:
            logger.error(f'History recording failed with database error: {add_result.info}, event: {repr(event)}')
    except Exception as e:
        logger.error(f'History recording Failed, error: {repr(e)}, event: {repr(event)}')


__all__ = [
    'postprocessor_history'
]
