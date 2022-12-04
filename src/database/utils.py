"""
@Author         : Ailitonia
@Date           : 2022/12/02 19:28
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : Database utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import inspect
from functools import wraps
from nonebot import get_driver, logger
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from typing import TypeVar, ParamSpec, Callable, Coroutine

from .connector import engine, async_session
from .model import Base, BaseDatabaseResult


P = ParamSpec("P")
R = TypeVar("R")


@get_driver().on_startup
async def __database_init_models():
    """初始化数据库表结构"""

    logger.opt(colors=True).info(f'<lc>Database</lc> | <ly>正在初始化数据库</ly>')
    try:
        # conn is an instance of AsyncConnection
        async with engine.begin() as conn:
            # to support SQLAlchemy DDL methods as well as legacy functions, the
            # AsyncConnection.run_sync() awaitable method will pass a "sync"
            # version of the AsyncConnection object to any synchronous method,
            # where synchronous IO calls will be transparently translated for
            # await.
            await conn.run_sync(Base.metadata.create_all)
        logger.opt(colors=True).success(f'<lc>Database</lc> | <lg>数据库初始化已完成</lg>')
    except Exception as _e:
        import sys
        logger.opt(colors=True).critical(f'<lc>Database</lc> | <r>数据库初始化失败</r>, 错误信息: {_e}')
        sys.exit(f'数据库初始化失败, {_e}')


@get_driver().on_shutdown
async def __database_dispose():
    """断开数据库链接 (for AsyncEngine created in function scope, close and clean-up pooled connections)"""

    await engine.dispose()
    logger.opt(colors=True).info(f'<lc>Database</lc> | <ly>已断开数据库链接</ly>')


async def get_db_session():
    """获取数据库 session 生成器依赖 (Dependence for database async session)"""
    async with async_session() as session:
        async with session.begin():
            yield session


def return_query_standard_result(
        func: Callable[P, Coroutine[None, None, R]]
) -> Callable[P, Coroutine[None, None, BaseDatabaseResult[R]]]:
    """装饰一个数据库查询的 async function 捕获其运行时的异常并使其返回 BaseDatabaseResult"""

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> BaseDatabaseResult[R]:
        try:
            _func_ret = await func(*args, **kwargs)
            _ret = BaseDatabaseResult[R](error=False, info='Success', result=_func_ret)
        except NoResultFound as e:
            _module = inspect.getmodule(func)
            logger.opt(colors=True).debug(
                f'<lc>Database</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> <ly>NoResultFound</ly>: {e}'
            )
            _ret = BaseDatabaseResult[R](error=True, info=f'NoResultFound, {e}')
        except MultipleResultsFound as e:
            _module = inspect.getmodule(func)
            logger.opt(colors=True).error(
                f'<lc>Database</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> <r>MultipleResultsFound</r>: {e}'
            )
            _ret = BaseDatabaseResult[R](error=True, info=f'MultipleResultsFound, {e}')
        except Exception as e:
            _module = inspect.getmodule(func)
            logger.opt(colors=True).exception(
                f'<lc>Database</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> <r>Exception {e.__class__.__name__}</r>: {e}'
            )
            _ret = BaseDatabaseResult[R](error=True, info=f'{e.__class__.__name__}, {e}')
        return _ret

    return _wrapper


def return_execute_standard_result(
        func: Callable[P, Coroutine[None, None, R]]
) -> Callable[P, Coroutine[None, None, BaseDatabaseResult[R]]]:
    """装饰一个数据库操作的 async function 捕获其运行时的异常并使其返回 BaseDatabaseResult"""

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> BaseDatabaseResult[R]:
        try:
            _func_ret = await func(*args, **kwargs)
            _ret = BaseDatabaseResult[R](error=False, info='Success', result=_func_ret)
        except Exception as e:
            _module = inspect.getmodule(func)
            logger.opt(colors=True).exception(
                f'<lc>Database</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> <r>Exception {e.__class__.__name__}</r>: {e}'
            )
            _ret = BaseDatabaseResult[R](error=True, info=f'{e.__class__.__name__}, {e}')
        return _ret

    return _wrapper


__all__ = [
    'get_db_session',
    'return_query_standard_result',
    'return_execute_standard_result'
]
