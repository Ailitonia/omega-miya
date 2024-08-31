"""
@Author         : Ailitonia
@Date           : 2024/5/26 下午2:06
@FileName       : schema_base
@Project        : nonebot2_miya
@Description    : database declarative base
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class OmegaDeclarativeBase(AsyncAttrs, DeclarativeBase):
    """数据表声明基类"""


__all__ = [
    'OmegaDeclarativeBase',
]
