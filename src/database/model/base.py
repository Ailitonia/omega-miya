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
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, AsyncGenerator, Generic, Optional, Self, TypeVar

from ..connector import async_session_factory


T = TypeVar("T")


class BaseDatabaseResult(BaseModel, Generic[T]):
    """数据库操作返回的标准结果 Model"""
    error: bool
    info: str
    result: Optional[T] = None

    @property
    def success(self) -> bool:
        return not self.error


class BaseDataAccessLayerModel(abc.ABC):
    """数据库操作对象"""

    def __init__(self, session: AsyncSession):
        self.db_session = session
        if not self.db_session.is_active:
            raise RuntimeError('Session is not active')

    @classmethod
    async def dal_dependence(cls) -> AsyncGenerator[Self, None]:
        """获取 DAL 生成器依赖 (Dependence for database async session)"""
        async with async_session_factory() as session:
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

    async def commit_session(self) -> None:
        """强制提交所有数据库更改并结束 session"""
        await self.db_session.commit()
        await self.db_session.close()


__all__ = [
    'BaseDatabaseResult',
    'BaseDataAccessLayerModel'
]
