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
from functools import wraps
from typing import Callable, Coroutine

from nonebot.log import logger

from .model import BaseApiReturn


def return_standard_api_result[R, ** P](
        func: Callable[P, Coroutine[None, None, R]]
) -> Callable[P, Coroutine[None, None, BaseApiReturn]]:
    """装饰一个 api handler 捕获其运行时的异常并使其返回 BaseApiReturn"""

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> BaseApiReturn:
        try:
            func_result = await func(*args, **kwargs)
            if isinstance(func_result, Exception):
                raise func_result
            else:
                result = BaseApiReturn(error=False, body=func_result, message='Success')
        except Exception as e:
            module = inspect.getmodule(func)
            logger.opt(colors=True).error(
                f'<lc>OmegaAPI</lc> | <ly>{module.__name__ if module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> <r>Exception {e.__class__.__name__}</r>: {e}'
            )
            result = BaseApiReturn(error=True, body=None, message=e.__class__.__name__, exception=repr(e))

        return result

    return _wrapper


__all__ = [
    'return_standard_api_result',
]
