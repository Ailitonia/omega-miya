"""
@Author         : Ailitonia
@Date           : 2022/04/13 23:35
@FileName       : user.py
@Project        : nonebot2_miya 
@Description    : OneBot User Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from .base_model import BaseOneBotModel


class LoginInfo(BaseOneBotModel):
    """登录号信息

    - user_id: QQ 号
    - nickname: QQ 昵称
    """
    user_id: str
    nickname: str


class FriendInfo(LoginInfo):
    """好友信息

    - user_id: QQ 号
    - nickname: QQ 昵称
    - remark: 备注名
    """
    remark: str


class StrangerInfo(LoginInfo):
    """陌生人信息"""
    sex: Literal['male', 'female', 'unknown']
    age: int


class GroupUser(LoginInfo):
    group_id: str
    card: str
    sex: Literal['male', 'female', 'unknown']
    age: int
    area: str
    join_time: int
    last_sent_time: int
    level: str
    role: Literal['owner', 'admin', 'member']
    unfriendly: bool
    title: str
    title_expire_time: int
    card_changeable: bool


__all__ = [
    'LoginInfo',
    'FriendInfo',
    'StrangerInfo',
    'GroupUser'
]
