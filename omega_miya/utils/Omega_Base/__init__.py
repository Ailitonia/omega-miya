"""
统一封装Omega的所有数据库操作
其他插件不得单独写入数据库操作逻辑
"""

from .database import DBTable
from .user import DBUser
from .group import DBGroup
from .skill import DBSkill
from .subscription import DBSubscription
from .bilidynamic import DBDynamic
from .history import DBHistory
from .database import DBResult as Result


__all__ = [
    'DBTable',
    'DBUser',
    'DBGroup',
    'DBSkill',
    'DBSubscription',
    'DBDynamic',
    'DBHistory',
    'Result'
]
