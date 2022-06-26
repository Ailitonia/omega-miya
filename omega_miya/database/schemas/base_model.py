"""
@Author         : Ailitonia
@Date           : 2022/02/22 18:01
@FileName       : base_model.py
@Project        : nonebot2_miya
@Description    : Model ABC
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from datetime import datetime
from typing import List, Union, Type, Optional, Any
from enum import Enum, unique
from pydantic import BaseModel
from nonebot import logger
from omega_miya.result import BaseResult, BoolResult

from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy.sql.selectable import Select as Select
from sqlalchemy.sql.dml import Update as Update
from sqlalchemy.sql.dml import Delete as Delete
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.orm.session import sessionmaker

from ..connector import PersistentDatabase
from ..model import Base as BaseOrm


class BaseDatabaseModel(BaseModel):
    """数据库外部模型基类"""
    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class DatabaseModelResult(BaseResult[BaseDatabaseModel]):
    """数据库查询结果基类"""
    result: Optional["BaseDatabaseModel"]


class DatabaseModelListResult(BaseResult[BaseDatabaseModel]):
    """数据库查询结果基类"""
    result: List["BaseDatabaseModel"]


@unique
class DatabaseErrorInfo(Enum):
    """数据库操作错误信息"""
    no_ret_f = 'NoResultFound'
    multi_rets_f = 'MultipleResultsFound'
    query_f = 'QueryOrmFailed'
    exe_f = 'ExecuteFailed'
    add_f = 'AddOrmFailed'
    update_f = 'UpdateOrmFailed'
    del_f = 'DeleteOrmFailed'


class BaseDatabase(abc.ABC):
    """数据库操作对象

    参数:
        - orm_model: 数据库操作对象对应的 sqlalchemy model
        - unique_model: 应当是一个派生自 BaseDatabaseModel 的 UniqueModel, 该模型必须能唯一确定数据库中的一行
        - require_model: 应当是一个派生自 UniqueModel 的 RequireModel, 该模型必须具备初始化对应 sqlalchemy model 对象的全部必须参数
        - data_model: 应当是一个派生自 RequireModel 的 Model, 用于构造数据库查询结果对象, 必须包含对应 sqlalchemy model 的全部参数
        - self_model: 应当是对应的 UniqueModel 实列, 用于初始化数据库操作实列
        - database_session: 数据库 sessionmaker 实例
    """
    orm_model: Type["BaseOrm"]
    unique_model: Type["BaseDatabaseModel"]
    require_model: Type["BaseDatabaseModel"]
    data_model: Type["BaseDatabaseModel"]
    self_model: "BaseDatabaseModel"
    database_session: sessionmaker = PersistentDatabase.get_async_session()

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        """实例化对象时应当通过参数实例化 self_mode 而非直接传入模型"""
        raise NotImplementedError

    def __repr__(self):
        return f'<{self.__class__.__name__}>(orm={self.orm_model}, model={repr(self.self_model)})'

    @classmethod
    @abc.abstractmethod
    def _make_all_select(cls) -> Select:
        """构造一个 select 语句, 可以查询数据库 orm_model 对应的数据表全部行, order_by 自行实现"""
        raise NotImplementedError

    @classmethod
    async def _query_custom_all(cls, *, stmt: Optional["Select"] = None, scalar: bool = True) -> List[Any]:
        """在数据库查询符合该操作对象对应表的全部行, 条件任意"""
        if stmt is None:
            stmt = cls._make_all_select()

        async with cls.database_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(stmt)
                    if scalar:
                        result = list(session_result.scalars().all())
                    else:
                        result = list(session_result.all())
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.opt(colors=True).error(
                    f'<ly>{cls.__module__}._query_custom_all</ly> <c>></c> operating failed, '
                    f'{DatabaseErrorInfo.query_f.value}, error: {repr(e)}')
                raise e
        return result

    @classmethod
    async def _query_all(cls, *, stmt: Optional["Select"] = None) -> DatabaseModelListResult:
        """在数据库查询该表单一目标对象的全部行并转换成 model 输出"""
        try:
            _query_result = await cls._query_custom_all(stmt=stmt, scalar=True)
            results_list = [cls.data_model.from_orm(x) for x in _query_result]
        except Exception as e:
            logger.opt(colors=True).error(
                f'<ly>{cls.__module__}._query_all</ly> <c>></c> operating failed, '
                f'{DatabaseErrorInfo.query_f.value}, error: {repr(e)}')
            raise e
        return DatabaseModelListResult(error=False, info='Success', result=results_list)

    @classmethod
    async def _query_custom_one(cls, stmt: "Select", *, scalar: bool = True) -> Any:
        """在数据库查询符合该操作对象对应表的唯一行, 条件任意"""
        async with cls.database_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(stmt)
                    if scalar:
                        result = session_result.scalar_one()
                    else:
                        result = session_result.one()
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.opt(colors=True).debug(
                    f'<ly>{cls.__module__}._query_custom_one</ly> <c>></c> operating failed, '
                    f'{DatabaseErrorInfo.query_f.value}, error: {repr(e)}')
                raise e
        return result

    @classmethod
    async def _query_unique_one(cls, stmt: "Select") -> DatabaseModelResult:
        """在数据库查询符合该操作对象对应表的唯一行, 条件任意, 解析为 DatabaseModelResult 返回"""
        try:
            unique_result = cls.data_model.from_orm(await cls._query_custom_one(stmt=stmt))
            result = DatabaseModelResult(error=False, info='Success', result=unique_result)
        except NoResultFound:
            logger.opt(colors=True).debug(
                f'<ly>{cls.__module__}._query_unique_one</ly> <c>></c> operating failed, '
                f'{DatabaseErrorInfo.no_ret_f.value}')
            result = DatabaseModelResult(error=True, info=DatabaseErrorInfo.no_ret_f.value, result=None)
        except MultipleResultsFound:
            logger.opt(colors=True).error(
                f'<ly>{cls.__module__}._query_unique_one</ly> <c>></c> operating failed, '
                f'{DatabaseErrorInfo.multi_rets_f.value}')
            result = DatabaseModelResult(error=True, info=DatabaseErrorInfo.multi_rets_f.value, result=None)
        except Exception as e:
            logger.opt(colors=True).error(
                f'<ly>{cls.__module__}._query_unique_one</ly> <c>></c> operating failed, '
                f'{DatabaseErrorInfo.query_f.value}, error: {repr(e)}')
            raise e
        return result

    async def query_unique_self(self) -> DatabaseModelResult:
        """在数据库查询符合 self_model 的唯一结果行, 解析为 DatabaseModelResult 返回"""
        stmt = self._make_unique_self_select()
        return await self._query_unique_one(stmt=stmt)

    async def exist(self) -> bool:
        return (await self.query_unique_self()).success

    @classmethod
    async def _execute(cls, stmt: Union["Update", "Delete"]) -> BoolResult:
        """在执行数据库 update 或 delete 操作并返回 Result

        参数:
            - stmt: 构造的 select 语句
            - session: 当前的 session
        """
        async with cls.database_session() as session:
            try:
                async with session.begin():
                    await session.execute(stmt)
                await session.commit()
                result = BoolResult(error=False, info='Success', result=True)
            except Exception as e:
                await session.rollback()
                logger.opt(colors=True).error(
                    f'<ly>{cls.__module__}._execute</ly> <c>></c> operating failed, '
                    f'{DatabaseErrorInfo.exe_f.value}, error: {repr(e)}')
                raise e
        return result

    @abc.abstractmethod
    def _make_unique_self_select(self) -> Select:
        """构造一个 select 语句, 可以查询数据库到 self_model 对应的, 被 UniqueModel 模型唯一确定的数据库中的一行结果"""
        raise NotImplementedError

    @abc.abstractmethod
    def _make_unique_self_update(self, new_model: "BaseDatabaseModel") -> Update:
        """构造一个 update 语句, 可以匹配并 update 由 self_model 对应的, 被 UniqueModel 模型唯一确定的数据库中的一行结果

        参数:
            - new_model: 应当是一个派生自 BaseDatabaseModel 的 RequireModel 实例, 具备新对象的全部必须参数"""
        raise NotImplementedError

    @abc.abstractmethod
    def _make_unique_self_delete(self) -> Delete:
        """构造一个 delete 语句, 可以匹配并 delete 由 self_model 对应的, 被 UniqueModel 模型唯一确定的数据库中的一行结果"""
        raise NotImplementedError

    async def _update_unique_self(self, new_model: "BaseDatabaseModel") -> BoolResult:
        """在数据库更新符合 self_model 的唯一结果行

        参数:
            - new_model: 应当是一个派生自 BaseDatabaseModel 的 RequireModel 实例, 具备新对象的全部必须参数"""
        return await self._execute(stmt=self._make_unique_self_update(new_model=new_model))

    @abc.abstractmethod
    async def update_unique_self(self, *args, **kwargs) -> BoolResult:
        """在数据库更新符合 self_model 的唯一结果行, 应当传入实例化 RequireModel 对象时必须的参数而非直接传入模型"""
        return await self._update_unique_self(new_model=self.require_model.parse_obj(**kwargs))

    async def delete_unique_self(self) -> BoolResult:
        """在数据库删除符合 self_model 的唯一结果行"""
        return await self._execute(stmt=self._make_unique_self_delete())

    async def query_and_delete_unique_self(self) -> BoolResult:
        """查询并删除符合 self_model 的唯一结果行, 若查询结果不存在则返回 Error Result"""
        async with self.database_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(self._make_unique_self_select())
                    exist_unique_self = session_result.scalar_one()
                    await session.delete(exist_unique_self)
                await session.commit()
                result = BoolResult(error=False, info='Success', result=True)
            except NoResultFound:
                await session.rollback()
                logger.opt(colors=True).debug(
                    f'<ly>{self.__module__}.query_and_delete_unique_self</ly> <c>></c> operating failed, '
                    f'{DatabaseErrorInfo.no_ret_f.value}')
                result = BoolResult(error=True, info=DatabaseErrorInfo.no_ret_f.value, result=False)
            except Exception as e:
                await session.rollback()
                logger.opt(colors=True).error(
                    f'<ly>{self.__module__}.query_and_delete_unique_self</ly> <c>></c> operating failed, '
                    f'{DatabaseErrorInfo.query_f.value}/{DatabaseErrorInfo.del_f.value}, error: {repr(e)}')
                raise e
        return result

    async def _add_upgrade_unique_self(self, new_model: "BaseDatabaseModel") -> BoolResult:
        """在数据库新增或更新符合 self_model 的唯一对象, 即: 若 self_model 对应行存在则更新, 不存在则新增

        参数:
            - new_model: 应当是一个派生自 BaseDatabaseModel 的 RequireModel 实例, 具备新对象的全部必须参数
        """
        async with self.database_session() as session:
            try:
                async with session.begin():
                    try:
                        # 首先尝试查询对象是否已经存在, 已存在行则直接更新
                        session_result = await session.execute(self._make_unique_self_select())
                        unique_result = self.data_model.from_orm(session_result.scalar_one())
                        upgrade_data = unique_result.dict()
                        upgrade_data.update(**new_model.dict())
                        upgrade_data.update({'updated_at': datetime.now()})
                        upgrade_stmt = self._make_unique_self_update(new_model=self.data_model.parse_obj(upgrade_data))
                        await session.execute(upgrade_stmt)
                        result = BoolResult(error=False, info='Upgrade Success', result=True)
                    except NoResultFound:
                        new_data = new_model.dict()
                        new_data.update({'created_at': datetime.now()})
                        new_orm_model = self.orm_model(**new_data)
                        session.add(new_orm_model)
                        result = BoolResult(error=False, info='Add Success', result=True)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.opt(colors=True).error(
                    f'<ly>{self.__module__}._add_upgrade_unique_self</ly> <c>></c> operating failed, '
                    f'{DatabaseErrorInfo.query_f.value}/{DatabaseErrorInfo.add_f.value}, error: {repr(e)}')
                raise e
        return result

    async def _add_only_without_upgrade_unique_self(self, new_model: "BaseDatabaseModel") -> BoolResult:
        """在数据库仅新增符合 self_model 的唯一对象, 即: 若 self_model 对应行存在则忽略, 不存在则新增

        参数:
            - new_model: 应当是一个派生自 BaseDatabaseModel 的 RequireModel 实例, 具备新对象的全部必须参数
        """
        async with self.database_session() as session:
            try:
                async with session.begin():
                    try:
                        # 首先尝试查询对象是否已经存在, 已存在行则忽略
                        session_result = await session.execute(self._make_unique_self_select())
                        unique_result = self.data_model.from_orm(session_result.scalar_one())
                        result = BoolResult(error=False, info=f'Exist item: {unique_result}', result=True)
                    except NoResultFound:
                        new_data = new_model.dict()
                        new_data.update({'created_at': datetime.now()})
                        new_orm_model = self.orm_model(**new_data)
                        session.add(new_orm_model)
                        result = BoolResult(error=False, info='Add Success', result=True)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.opt(colors=True).error(
                    f'<ly>{self.__module__}._add_upgrade_unique_self</ly> <c>></c> operating failed, '
                    f'{DatabaseErrorInfo.add_f.value}, error: {repr(e)}')
                raise e
        return result

    @abc.abstractmethod
    async def add_upgrade_unique_self(self, *args, **kwargs) -> BoolResult:
        """在数据库新增或更新符合 self_model 的唯一对象, 即: 若 self_model 对应行存在则更新, 不存在则新增.
         应当传入实例化 RequireModel 对象时必须的参数而非直接传入模型"""
        return await self._add_upgrade_unique_self(new_model=self.require_model.parse_obj(**kwargs))


__all__ = [
    'BaseDatabase',
    'BaseDatabaseModel',
    'DatabaseModelResult',
    'DatabaseModelListResult',
    'DatabaseErrorInfo',
    'Session',
    'Select',
    'Update',
    'Delete'
]
