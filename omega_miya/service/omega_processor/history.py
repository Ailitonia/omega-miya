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
from nonebot.adapters.onebot.v11.event import Event, MetaEvent
from omega_miya.database import History


async def postprocessor_history(event: Event):
    """历史记录处理"""
    try:
        if isinstance(event, MetaEvent):
            # 不记录元事件
            return

        time = event.time
        self_id = str(event.self_id)
        event_type = getattr(event, 'post_type', 'Undefined')
        message_id = getattr(event, 'message_id', -1)
        raw_data = event.json()
        message_data = getattr(event, 'message', '')

        raw_data = str(raw_data) if not isinstance(raw_data, str) else raw_data
        msg_data = str(message_data) if not isinstance(message_data, str) else message_data
        if len(raw_data) > 4096:
            logger.warning(f'History | Raw data is longer than field limited and it will be reduce, <{raw_data}>')
            raw_data = raw_data[:4096]
        if len(msg_data) > 4096:
            logger.warning(f'History | Raw data is longer than field limited and it will be reduce, <{msg_data}>')
            msg_data = msg_data[:4096]

        new_history = History(time=time, self_id=self_id, event_type=event_type, event_id=message_id)
        add_result = await new_history.add_upgrade_unique_self(raw_data=raw_data, msg_data=msg_data)
        if add_result.error:
            logger.error(f'History | Recording failed with database error: {add_result.info}, event: {repr(event)}')
    except Exception as e:
        logger.error(f'History | Recording Failed, error: {repr(e)}, event: {repr(event)}')


__all__ = [
    'postprocessor_history'
]
