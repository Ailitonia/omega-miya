"""
@Author         : Ailitonia
@Date           : 2022/04/13 23:13
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : 数据库异常
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


class DatabaseBaseException(Exception):
    """用于在外部操作中抛出的数据库异常"""


class DatabaseQueryError(DatabaseBaseException):
    """数据库查询异常"""


class DatabaseUpgradeError(DatabaseBaseException):
    """数据库新增或更新异常"""


class DatabaseDeleteError(DatabaseBaseException):
    """数据库删除异常异常"""


__all__ = [
    'DatabaseBaseException',
    'DatabaseQueryError',
    'DatabaseUpgradeError',
    'DatabaseDeleteError'
]
