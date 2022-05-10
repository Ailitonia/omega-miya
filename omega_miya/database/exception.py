"""
@Author         : Ailitonia
@Date           : 2022/04/13 23:13
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : 数据库异常
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from omega_miya.exception import DatabaseException


class DatabaseQueryError(DatabaseException):
    """数据库查询异常"""


class DatabaseUpgradeError(DatabaseException):
    """数据库新增或更新异常"""


class DatabaseDeleteError(DatabaseException):
    """数据库删除异常异常"""


__all__ = [
    'DatabaseQueryError',
    'DatabaseUpgradeError',
    'DatabaseDeleteError'
]
