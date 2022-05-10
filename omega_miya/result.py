"""
@Author         : Ailitonia
@Date           : 2022/02/20 17:04
@FileName       : result.py
@Project        : nonebot2_miya 
@Description    : Omega Results Models and Tools
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


import inspect
from datetime import date
from functools import wraps
from typing import Dict, List, Set, Tuple, Any, Optional, TypeVar, Generic, ParamSpec, Callable, Coroutine
from pydantic import Json
from pydantic.generics import GenericModel
from nonebot import logger


T = TypeVar('T')


class BaseResult(GenericModel, Generic[T]):
    error: bool
    info: str
    result: Optional[T] = None

    @property
    def success(self) -> bool:
        return not self.error


class DictResult(BaseResult):
    result: dict


class IntDictResult(BaseResult):
    result: Dict[int, int]


class TextDictResult(BaseResult):
    result: Dict[str, str]


class JsonDictResult(BaseResult):
    result: Json


class ListResult(BaseResult):
    result: list


class IntListResult(BaseResult):
    result: List[int]


class TextListResult(BaseResult):
    result: List[str]


class TupleListResult(BaseResult):
    result: List[tuple]


class DictListResult(BaseResult):
    result: List[dict]


class DateListResult(BaseResult):
    result: List[date]


class SetResult(BaseResult):
    result: set


class IntSetResult(BaseResult):
    result: Set[int]


class TextSetResult(BaseResult):
    result: Set[str]


class TupleResult(BaseResult):
    result: tuple


class IntTupleResult(BaseResult):
    result: Tuple[int, ...]


class TextTupleResult(BaseResult):
    result: Tuple[str, ...]


class IntResult(BaseResult):
    result: int


class TextResult(BaseResult):
    result: str


class BoolResult(BaseResult):
    result: bool


class BytesResult(BaseResult):
    result: bytes


class AnyResult(BaseResult):
    result: Any


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
