"""
统一封装Omega的所有数据库操作
其他插件不得单独写入数据库操作逻辑
"""

from .database import DBTable
from .class_result import Result
from .model import \
    DBUser, DBFriend, DBBot, DBBotGroup, DBGroup, DBSkill, DBSubscription, DBDynamic, \
    DBPixivillust, DBPixivtag, DBPixivision, \
    DBEmail, DBEmailBox, DBHistory, DBAuth, DBCoolDownEvent, DBStatus


__all__ = [
    'DBTable',
    'DBUser',
    'DBFriend',
    'DBBot',
    'DBBotGroup',
    'DBGroup',
    'DBSkill',
    'DBSubscription',
    'DBDynamic',
    'DBPixivillust',
    'DBPixivtag',
    'DBPixivision',
    'DBEmail',
    'DBEmailBox',
    'DBHistory',
    'DBAuth',
    'DBCoolDownEvent',
    'DBStatus',
    'Result'
]
