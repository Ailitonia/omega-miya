"""
统一封装Omega的所有数据库操作
其他插件不得单独写入数据库操作逻辑
"""

from .class_result import BaseResult, Result
from .model import (
    DBUser, DBFriend, DBBot, DBBotGroup, DBGroup, DBSkill, DBSubscription, DBDynamic,
    DBPixivUserArtwork, DBPixivillust, DBPixivision, DBEmail, DBEmailBox, DBHistory,
    DBAuth, DBCoolDownEvent, DBStatus, DBStatistic, DBPlugin)


__all__ = [
    'DBUser',
    'DBFriend',
    'DBBot',
    'DBBotGroup',
    'DBGroup',
    'DBSkill',
    'DBSubscription',
    'DBDynamic',
    'DBPixivUserArtwork',
    'DBPixivillust',
    'DBPixivision',
    'DBEmail',
    'DBEmailBox',
    'DBHistory',
    'DBAuth',
    'DBCoolDownEvent',
    'DBStatus',
    'DBStatistic',
    'DBPlugin',
    'BaseResult',
    'Result'
]
