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
from .user import Anonymous


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
    message: Message
    message_id: int
    message_id_v2: str
    message_seq: int
    message_type: str
    real_id: int
    sender: Sender
    time: int


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
    'ReceiveMessage',
    'GroupMessageHistory',
    'ReceiveForwardMessage'
]
