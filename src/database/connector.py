"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:20
@FileName       : connector.py
@Project        : nonebot2_miya 
@Description    : omega database connector
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from asyncio import current_task
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from nonebot.log import logger
from nonebot.matcher import current_event, current_matcher
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_scoped_session, async_sessionmaker, create_async_engine)

from .config import database_config


engine: AsyncEngine
async_session_factory: async_sessionmaker[AsyncSession]


def _init_database() -> None:
    """创建数据库连接并初始化数据库"""
    global engine, async_session_factory

    try:
        # 创建数据库连接
        engine = create_async_engine(
            database_config.connector.url,
            future=True,  # 使用 2.0 API，向后兼容
            pool_recycle=3600, pool_pre_ping=True, echo=False,  # 连接池配置
            **database_config.connector.connect_args  # 数据库连接参数
        )
        logger.opt(colors=True).info(f'<lc>Database</lc> | 已配置 <lg>{database_config.database}</lg> 数据库连接')

        # expire_on_commit=False will prevent attributes from being expired after commit.
        async_session_factory = async_sessionmaker(
            engine, class_=AsyncSession, autoflush=True, expire_on_commit=False
        )
    except Exception as e:
        import sys
        logger.opt(colors=True).critical(f'<r>创建数据库连接失败</r>, 错误信息: {e}')
        sys.exit(f'创建数据库连接失败, {e}')


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


# init database when import
_init_database()


__all__ = [
    'engine',
    'begin_db_session',
    'get_db_session',
]
