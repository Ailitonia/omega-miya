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
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Self

from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .helpers import database_session

if TYPE_CHECKING:
    from .schema_base import OmegaDeclarativeBase as Base


class BaseDataOutModel(BaseModel):
    """数据库导出数据模型基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True, frozen=True)


class BaseDataAccessLayer[ORM_T: 'Base', DATA_T: BaseDataOutModel](abc.ABC):
    """数据库操作对象 (DAL) 基类

    Note: 为保证兼容性, 只使用 ORM 层相关方法, 对于 add_ignore_exist 或 add_update_exist 等操作不使用
    on_duplicate_key_update()/on_conflict_do_nothing()/on_conflict_do_update() 等方言, 对于常见竞态
    使用唯一约束+捕获冲突异常或加锁处理, 可能会导致并发性能降低;
    为约束事务范围, ORM 实例对象应当仅在 DAL 层内部传递, 返回给外部的应当为 DataOutModel 数据模型
    """

    def __init__(self, session: AsyncSession):
        self.db_session = session

    @classmethod
    @asynccontextmanager
    async def create(cls) -> AsyncGenerator[Self, None]:
        """创建数据库 session, 初始化 DAL 并开始会话"""
        async with database_session() as session:
            yield cls(session)

    @classmethod
    async def dal_dependence(cls) -> AsyncGenerator[Self, None]:
        """获取 DAL 生成器依赖 (Dependence for database async session)"""
        async with cls.create() as dal:
            yield dal

    @asynccontextmanager
    async def safe_begin_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """安全开启一个事务或嵌套事务

        若当前 session 已有事务则开 SAVEPOINT 嵌套事务;
        无事务则显式开启顶层事务, 但本方法不执行提交:
        顶层事务的提交统一交由会话边界 (database_session) 或显式 commit_session 处理,
        以保证多个 DAL 方法组合调用时的整体原子性 (避免纯写方法在 fresh session 上自行 commit)
        """
        if not self.db_session.is_active:
            raise RuntimeError('Current session is not active')

        if self.db_session.in_transaction():
            async with self.db_session.begin_nested():
                yield self.db_session
        else:
            # 显式开启顶层事务但不在此处提交: 一方面保证后续 must_begin_nested_in_transaction 可用
            # (SAVEPOINT 需要已存在的外层事务, autobegin 在首个 SQL 前不会自动开启事务);
            # 另一方面提交统一交由会话边界 (database_session) 或显式 commit_session 处理,
            # 以保证多个 DAL 方法组合调用时的整体原子性 (避免纯写方法在 fresh session 上自行 commit)
            await self.db_session.begin().start()
            try:
                yield self.db_session
            except BaseException:
                await self.db_session.rollback()
                raise

    @asynccontextmanager
    async def must_begin_nested_in_transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """开启嵌套事务

        若当前 session 已有事务则开 SAVEPOINT, 无事务则抛出异常
        """
        if not self.db_session.is_active:
            raise RuntimeError('Current session is not active')

        if not self.db_session.in_transaction():
            raise RuntimeError('Must be executed within a session already in active transaction')

        async with self.db_session.begin_nested():
            yield self.db_session

    @staticmethod
    def _is_unique_conflict_error(exc: IntegrityError) -> bool:
        """内部方法, 用于判断 IntegrityError 是否由唯一约束冲突引起 (跨方言甄别)

        用于 upsert 场景的冲突兜底: 只有确认是唯一约束冲突时才应进入"已存在则更新/忽略"分支,
        其他类型的完整性冲突 (外键/非空/CHECK 等) 必须原样抛出, 避免掩盖真实错误。

        - PostgreSQL (asyncpg/psycopg): sqlstate 23505 (unique_violation)
        - MySQL (aiomysql/asyncmy): errno 1062 (ER_DUP_ENTRY)
        - SQLite (aiosqlite/sqlite3): extended error code 1555 (CONSTRAINT_PRIMARYKEY) / 2067 (CONSTRAINT_UNIQUE)
        """
        orig = exc.orig
        if orig is None:
            return False

        # MySQL (aiomysql/asyncmy): errno 1062 (ER_DUP_ENTRY)
        # 注意必须最先检查: MySQL 所有完整性冲突的 SQLSTATE 均为 23000, 不具备区分度
        if orig.args and orig.args[0] == 1062:
            return True

        # PostgreSQL (asyncpg/psycopg): sqlstate/pgcode 23505 (unique_violation)
        sqlstate = getattr(orig, 'sqlstate', None) or getattr(orig, 'pgcode', None)
        if sqlstate is not None:
            return sqlstate == '23505'

        # SQLite (aiosqlite/sqlite3): extended error code 1555 (CONSTRAINT_PRIMARYKEY) / 2067 (CONSTRAINT_UNIQUE)
        sqlite_errorcode = getattr(orig, 'sqlite_errorcode', None)
        if sqlite_errorcode is not None:
            return sqlite_errorcode in (1555, 2067)

        return False

    @classmethod
    def _escape_like(cls, keyword: str) -> str:
        """转义 LIKE 特殊字符：\\ % _

        防注入, 用户输入里的 % / _ 会变成通配符
        转义后配合 `.like(pattern, escape='\\')` 生成 ... ESCAPE '\\'。
        """
        return (
            keyword
            .replace('\\', '\\\\')
            .replace('%', '\\%')
            .replace('_', '\\_')
        )

    @abc.abstractmethod
    async def _select_unique(self, *args, **kwargs) -> ORM_T:
        """内部方法, 根据非索引的条件查询唯一行, 使用 scalar_one() 获取实例对象, 若查询结果为空或不唯一则抛出异常"""
        raise NotImplementedError

    @abc.abstractmethod
    async def query_unique(self, *args, **kwargs) -> DATA_T:
        """根据非索引的条件查询唯一行, 若查询结果为空或不唯一则抛出异常"""
        raise NotImplementedError

    async def commit_session(self) -> None:
        """提交所有数据库更改"""
        await self.db_session.commit()

    async def rollback_session(self) -> None:
        """回滚所有数据库更改"""
        await self.db_session.rollback()


__all__ = [
    'BaseDataAccessLayer',
    'BaseDataOutModel',
]
