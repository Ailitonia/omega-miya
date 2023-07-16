"""
@Author         : Ailitonia
@Date           : 2022/04/16 15:06
@FileName       : user.py
@Project        : nonebot2_miya 
@Description    : go-cqhttp User Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from ...model import BaseOneBotModel
from ...model import StrangerInfo as OneBotStrangerInfo, LoginInfo as OneBotLoginInfo, FriendInfo as OneBotFriendInfo
from ...model import GroupUser as OneBotGroupUser


class StrangerInfo(OneBotStrangerInfo):
    """陌生人"""
    qid: str
    level: int
    login_days: str


class LoginInfo(OneBotLoginInfo):
    """登录号信息"""


class FriendInfo(OneBotFriendInfo):
    """好友信息"""


class GroupUser(OneBotGroupUser):
    """群成员"""
    shut_up_timestamp: int


class Anonymous(BaseOneBotModel):
    """匿名用户"""
    flag: str
    id: int
    name: str


class QidianAccountUser(BaseOneBotModel):
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
