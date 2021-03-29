"""
统一封装Omega的所有数据库操作
其他插件不得单独写入数据库操作逻辑
"""

from .database import DBTable
from .model import \
    DBUser, DBGroup, DBSkill, DBSubscription, DBDynamic, \
    DBPixivillust, DBPixivtag, DBPixivision, \
    DBEmail, DBEmailBox, DBHistory, DBAuth, DBCoolDownEvent, DBStatus
from .database import DBResult as Result


__all__ = [
    'DBTable',
    'DBUser',
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
