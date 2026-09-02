"""
@Author         : Ailitonia
@Date           : 2023/7/17 20:31
@FileName       : types
@Project        : nonebot2_miya
@Description    : 数据库 types 兼容
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from sqlalchemy.dialects import mysql, postgresql, sqlite
from sqlalchemy.types import JSON, BigInteger, Boolean, LargeBinary, Text

# BigInt 在 sqlite 中不能作为自增主键
# SQLAlchemy does not map BigInt to Int by default on the sqlite dialect.
# https://stackoverflow.com/questions/18835740/does-bigint-auto-increment-work-for-sqlalchemy-with-sqlite/23175518#23175518
IndexInt = BigInteger().with_variant(sqlite.INTEGER(), 'sqlite')

# SQLite 显式回退到 INTEGER, 避免某些驱动/工具把它当成 TEXT
CommonBool = Boolean().with_variant(sqlite.INTEGER(), 'sqlite')

# MySQL 下升级为 LONGBLOB, 用于存储文件, 图片等大对象
CommonLargeBlob = LargeBinary().with_variant(mysql.LONGBLOB(), 'mysql')

# MySQL 下升级为 LONGTEXT, 用于储存超长文本
CommonLongText = Text().with_variant(mysql.LONGTEXT(), 'mysql')

# JSON 类型兼容
CommonJSON = JSON().with_variant(postgresql.JSONB(), 'postgresql')


__all__ = [
    'IndexInt',
    'CommonBool',
    'CommonLargeBlob',
    'CommonLongText',
    'CommonJSON',
]
