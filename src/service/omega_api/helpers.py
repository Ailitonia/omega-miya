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

from nonebot.log import logger

from .model import BaseApiModel, StandardApiReturn


def return_standard_api_result[**P, T1, T2, R: BaseApiModel](
        func: Callable[P, Coroutine[T1, T2, R]]
) -> Callable[P, Coroutine[T1, T2, StandardApiReturn[R]]]:
    """装饰一个 api handler 捕获其运行时的异常并使其返回 StandardApiReturn"""

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> StandardApiReturn[R]:
        try:
            func_result = await func(*args, **kwargs)
            result = StandardApiReturn(error=False, body=func_result, message='Success', exception=None)
        except Exception as e:
            module = inspect.getmodule(func)
            logger.opt(colors=True).error(
                f'<lc>Omega API</lc> | <ly>{module.__name__ if module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> <r>Exception {e.__class__.__name__}</r>: {e}'
            )
            result = StandardApiReturn(error=True, body=None, message=e.__class__.__name__, exception=repr(e))
        return result

    return _wrapper


__all__ = [
    'return_standard_api_result',
]
