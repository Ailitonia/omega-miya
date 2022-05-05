"""
@Author         : Ailitonia
@Date           : 2022/02/20 17:04
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : Omega Results Models and Tools
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import inspect
from functools import wraps
from typing import TypeVar, ParamSpec, Callable, Coroutine
from nonebot import logger
from .results import (
    BaseResult,
    DictResult,
    IntDictResult,
    TextDictResult,
    JsonDictResult,
    ListResult,
    IntListResult,
    TextListResult,
    TupleListResult,
    DictListResult,
    DateListResult,
    SetResult,
    IntSetResult,
    TextSetResult,
    TupleResult,
    IntTupleResult,
    TextTupleResult,
    IntResult,
    TextResult,
    BoolResult,
    BytesResult,
    AnyResult
)


P = ParamSpec("P")
R = TypeVar("R")


def sync_return_result(func: Callable[P, R]) -> Callable[P, BaseResult[R]]:
    """一个用于包装 sync function 捕获其运行时的异常并使其返回 Result 的装饰器"""

    @wraps(func)
    def _wrapper(*args: P.args, **kwargs: P.kwargs) -> BaseResult[R]:
        try:
            _func_ret = func(*args, **kwargs)
            _ret = BaseResult[R](error=False, info='Success', result=_func_ret)
        except Exception as e:
            _module = inspect.getmodule(func)
            logger.opt(colors=True).exception(
                f'<lc>Decorator SyncReturnResult</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> <r>Exception {e.__class__.__name__}</r>: {e}')
            _ret = BaseResult[R](error=True, info=repr(e))
        return _ret

    return _wrapper


def async_return_result(
        func: Callable[P, Coroutine[None, None, R]]) -> Callable[P, Coroutine[None, None, BaseResult[R]]]:
    """一个用于包装 async function 捕获其运行时的异常并使其返回 Result 的装饰器"""

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> BaseResult[R]:
        try:
            _func_ret = await func(*args, **kwargs)
            _ret = BaseResult[R](error=False, info='Success', result=_func_ret)
        except Exception as e:
            _module = inspect.getmodule(func)
            logger.opt(colors=True).exception(
                f'<lc>Decorator AsyncReturnResult</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> <r>Exception {e.__class__.__name__}</r>: {e}')
            _ret = BaseResult[R](error=True, info=repr(e))
        return _ret

    return _wrapper


__all__ = [
    'BaseResult',
    'DictResult',
    'IntDictResult',
    'TextDictResult',
    'JsonDictResult',
    'ListResult',
    'IntListResult',
    'TextListResult',
    'TupleListResult',
    'DictListResult',
    'DateListResult',
    'SetResult',
    'IntSetResult',
    'TextSetResult',
    'TupleResult',
    'IntTupleResult',
    'TextTupleResult',
    'IntResult',
    'TextResult',
    'BoolResult',
    'BytesResult',
    'AnyResult',
    'sync_return_result',
    'async_return_result'
]
