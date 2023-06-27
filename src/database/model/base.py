"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:48
@FileName       : base.py
@Project        : nonebot2_miya 
@Description    : Database Model ABC
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from pydantic.generics import GenericModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional, TypeVar, Generic

from ..connector import async_session


T = TypeVar("T")


class BaseDatabaseResult(GenericModel, Generic[T]):
    """数据库操作返回的标准结果 Model"""
    error: bool
    info: str
    result: Optional[T] = None

    @property
    def success(self) -> bool:
        return not self.error


class BaseDataAccessLayerModel(abc.ABC):
    """数据库操作对象"""

    @abc.abstractmethod
    def __init__(self, session: AsyncSession):
        """实例化对象时应当同时初始化 self.orm_model 为对应表 ORM Model"""
        self.db_session = session
        raise NotImplementedError

    @classmethod
    async def dal_dependence(cls):
        """获取 DAL 生成器依赖 (Dependence for database async session)"""
        async with async_session() as session:
            async with session.begin():
                yield cls(session)

    @abc.abstractmethod
    async def query_unique(self, *args, **kwargs) -> Any:
        """查询唯一行"""
        raise NotImplementedError

    @abc.abstractmethod
    async def query_all(self) -> list[Any]:
        """查询全部行"""
        raise NotImplementedError

    @abc.abstractmethod
    async def add(self, *args, **kwargs) -> None:
        """新增行"""
        raise NotImplementedError

    @abc.abstractmethod
    async def update(self, *args, **kwargs) -> None:
        """更新行"""
        raise NotImplementedError

    @abc.abstractmethod
    async def delete(self, *args, **kwargs) -> None:
        """删除行"""
        raise NotImplementedError


__all__ = [
    'BaseDatabaseResult',
    'BaseDataAccessLayerModel'
]
