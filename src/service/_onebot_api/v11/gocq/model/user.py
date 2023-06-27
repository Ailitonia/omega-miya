"""
@Author         : Ailitonia
@Date           : 2022/04/16 15:06
@FileName       : user.py
@Project        : nonebot2_miya 
@Description    : go-cqhttp User Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from ...model import BaseOnebotModel
from ...model import StrangerInfo as OnebotStrangerInfo, LoginInfo as OnebotLoginInfo, FriendInfo as OnebotFriendInfo
from ...model import GroupUser as OnebotGroupUser


class StrangerInfo(OnebotStrangerInfo):
    """陌生人"""
    qid: str
    level: int
    login_days: str


class LoginInfo(OnebotLoginInfo):
    """登录号信息"""


class FriendInfo(OnebotFriendInfo):
    """好友信息"""


class GroupUser(OnebotGroupUser):
    """群成员"""
    shut_up_timestamp: int


class Anonymous(BaseOnebotModel):
    """匿名用户"""
    flag: str
    id: int
    name: str


class QidianAccountUser(BaseOnebotModel):
    """企点账号信息"""
    master_id: int
    ext_name: str
    create_time: int


__all__ = [
    'StrangerInfo',
    'LoginInfo',
    'FriendInfo',
    'GroupUser',
    'Anonymous',
    'QidianAccountUser'
]
