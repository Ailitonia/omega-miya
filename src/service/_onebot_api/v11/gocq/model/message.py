"""
@Author         : Ailitonia
@Date           : 2022/04/16 14:35
@FileName       : message.py
@Project        : nonebot2_miya 
@Description    : go-cqhttp Message Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from nonebot.adapters.onebot.v11.message import Message
from nonebot.adapters.onebot.v11.event import Sender

from ...model import BaseOnebotModel
from ...model import SentMessage as OnebotSentMessage

from .user import Anonymous


class SentMessage(OnebotSentMessage):
    """已发送的消息"""


class SentForwardMessage(OnebotSentMessage):
    """已发送的合并转发消息"""
    forward_id: str


class ReceiveMessage(BaseOnebotModel):
    """Api /get_msg 收到的消息

    这个字段 go-cqhttp 魔改严重

    - message_id: 消息id
    - real_id: 消息真实id
    - sender: 发送者
    - time: 发送时间
    - message: 消息内容
    """
    group: bool
    group_id: Optional[int]
    message_id: int
    real_id: int
    message_type: str
    sender: Sender
    time: int
    message: Message
    message_raw: Optional[Message]
    raw_message: Optional[Message]
    message_id_v2: Optional[str]
    message_seq: Optional[int]


class GroupMessageHistory(BaseOnebotModel):
    """群消息历史记录"""

    class _MessageHistory(BaseOnebotModel):
        anonymous: Optional[Anonymous]
        group_id: str
        message: Message
        message_id: int
        message_seq: int
        message_type: str
        post_type: str
        raw_message: str
        self_id: str
        sender: Sender
        sub_type: str
        time: int
        user_id: int

    messages: list[_MessageHistory]


class ReceiveForwardMessage(BaseOnebotModel):
    """合并转发消息"""

    class _MessageNode(BaseOnebotModel):

        class _Sender(BaseOnebotModel):
            nickname: str
            user_id: str

        content: Message
        sender: _Sender
        time: int

    messages: list[_MessageNode]


__all__ = [
    'SentMessage',
    'SentForwardMessage',
    'ReceiveMessage',
    'GroupMessageHistory',
    'ReceiveForwardMessage'
]
