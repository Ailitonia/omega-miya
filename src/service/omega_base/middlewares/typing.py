"""
@Author         : Ailitonia
@Date           : 2024/8/20 10:23:22
@FileName       : typing.py
@Project        : omega-miya
@Description    : Omega 中间件类型
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal, Union

from nonebot.internal.adapter import Message as BaseMessage, MessageSegment as BaseMessageSegment

type EntityAcquireType = Literal['event', 'user']
"""从 Event 提取 Entity 对象的类型, event: 事件本身所在场景的对象(群组频道等), user: 触发事件的用户对象"""

type BaseMessageType[Seg_T: BaseMessageSegType] = BaseMessage[Seg_T]
"""Nonebot 消息基类类型"""

type BaseMessageSegType[Msg_T: BaseMessageType] = BaseMessageSegment[Msg_T]
"""Nonebot 消息段基类类型"""

type BaseSentMessageType[Msg_T: BaseMessageType] = Union[str, BaseMessageSegType[Msg_T], Msg_T]
"""Nonebot 可发送消息基类类型"""

__all__ = [
    'EntityAcquireType',
    'BaseMessageType',
    'BaseMessageSegType',
    'BaseSentMessageType',
]
