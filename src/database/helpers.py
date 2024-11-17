"""
@Author         : Ailitonia
@Date           : 2022/12/02 19:28
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Database utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from asyncio import current_task
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from nonebot import get_driver, logger
from nonebot.matcher import current_event, current_matcher
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session

from .connector import async_session_factory, engine
from .schema_base import OmegaDeclarativeBase


@get_driver().on_startup
async def __database_init_models():
    """初始化数据库表结构"""

    logger.opt(colors=True).info('<lc>Database</lc> | <ly>正在初始化数据库</ly>')
    try:
        # conn is an instance of AsyncConnection
        async with engine.begin() as conn:
            # to support SQLAlchemy DDL methods as well as legacy functions, the
            # AsyncConnection.run_sync() awaitable method will pass a "sync"
            # version of the AsyncConnection object to any synchronous method,
            # where synchronous IO calls will be transparently translated for
            # await.
            await conn.run_sync(OmegaDeclarativeBase.metadata.create_all)
        logger.opt(colors=True).success('<lc>Database</lc> | <lg>数据库初始化已完成</lg>')
    except Exception as _e:
        import sys
        logger.opt(colors=True).critical(f'<lc>Database</lc> | <r>数据库初始化失败</r>, 错误信息: {_e}')
        sys.exit(f'数据库初始化失败, {_e}')


@get_driver().on_shutdown
async def __database_dispose():
    """断开数据库链接 (for AsyncEngine created in function scope, close and clean-up pooled connections)"""

    await engine.dispose()
    logger.opt(colors=True).info('<lc>Database</lc> | <ly>已断开数据库连接</ly>')


def _get_current_task_id() -> Any:
    try:
        return id(current_event.get()), current_matcher.get()
    except LookupError:
        return id(current_task())


def _get_scoped_session_factory() -> async_scoped_session[AsyncSession]:
    return async_scoped_session(async_session_factory, scopefunc=_get_current_task_id)


@asynccontextmanager
async def begin_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库 session 并开始事务"""
    scoped_session_factory = _get_scoped_session_factory()
    try:
        async with scoped_session_factory() as session:
            async with session.begin():
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise
    except Exception:
        await scoped_session_factory.rollback()
        raise
    else:
        await scoped_session_factory.commit()
    finally:
        await scoped_session_factory.remove()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库 session 生成器依赖 (Dependence for database async session)"""
    async with begin_db_session() as session:
        yield session


__all__ = [
    'begin_db_session',
    'get_db_session',
]
