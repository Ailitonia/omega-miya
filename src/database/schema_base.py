"""
@Author         : Ailitonia
@Date           : 2024/5/26 下午2:06
@FileName       : schema_base
@Project        : nonebot2_miya
@Description    : database declarative base
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

_NAMING_CONVENTION = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}
"""定义约束命名规则"""


class OmegaDeclarativeBase(AsyncAttrs, DeclarativeBase):
    """数据表声明基类"""
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


__all__ = [
    'OmegaDeclarativeBase',
]
