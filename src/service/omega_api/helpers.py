"""
@Author         : Ailitonia
@Date           : 2024/5/26 下午2:38
@FileName       : helpers
@Project        : nonebot2_miya
@Description    : Omega API helpers
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import inspect
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

from nonebot.log import logger

from .model import StandardOmegaAPIReturn


def return_standard_api_result[**P, T1, T2, R: Any](
        func: Callable[P, Coroutine[T1, T2, R]]
) -> Callable[P, Coroutine[T1, T2, StandardOmegaAPIReturn[R]]]:
    """装饰一个异步 API handler 捕获其运行时的异常并使其返回 StandardOmegaAPIReturn"""

    if not inspect.iscoroutinefunction(func):
        raise TypeError(f'{func.__name__} is not coroutine function')

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> StandardOmegaAPIReturn[R]:
        try:
            func_result = await func(*args, **kwargs)
            result = StandardOmegaAPIReturn(error=False, body=func_result, message='success')
        except Exception as e:
            module = inspect.getmodule(func)
            logger.opt(colors=True).error(
                f'<lc>Omega API</lc> | <ly>{module.__name__ if module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> <r>Exception {e.__class__.__name__}</r>: {e}'
            )
            result = StandardOmegaAPIReturn(error=True, body=None, message='internal error')
        return result

    return _wrapper


__all__ = [
    'return_standard_api_result',
]
