"""
@Author         : Ailitonia
@Date           : 2022/04/13 21:55
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Onebot Data Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .base_model import BaseOnebotModel
from .group import GroupInfo, GroupHonor
from .message import SentMessage, ReceiveMessage, CustomNodeMessage
from .user import LoginInfo, FriendInfo, StrangerInfo, GroupUser
from .file import ImageFile, RecordFile, CanSendImage, CanSendRecord, Cookies, CSRF, Credentials, Status, VersionInfo


__all__ = [
    'BaseOnebotModel',
    'GroupInfo',
    'GroupHonor',
    'SentMessage',
    'ReceiveMessage',
    'CustomNodeMessage',
    'LoginInfo',
    'FriendInfo',
    'StrangerInfo',
    'GroupUser',
    'RecordFile',
    'ImageFile',
    'CanSendImage',
    'CanSendRecord',
    'Cookies',
    'CSRF',
    'Credentials',
    'Status',
    'VersionInfo'
]
