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
from sqlalchemy.types import BigInteger

# BigInt 在 sqlite 中不能作为自增主键
# SQLAlchemy does not map BigInt to Int by default on the sqlite dialect.
# https://stackoverflow.com/questions/18835740/does-bigint-auto-increment-work-for-sqlalchemy-with-sqlite/23175518#23175518
IndexInt = BigInteger()
IndexInt = IndexInt.with_variant(postgresql.BIGINT(), 'postgresql')
IndexInt = IndexInt.with_variant(mysql.BIGINT(), 'mysql')
IndexInt = IndexInt.with_variant(sqlite.INTEGER(), 'sqlite')


__all__ = [
    'IndexInt',
]
