"""
@Author         : Ailitonia
@Date           : 2021/07/29 19:29
@FileName       : process_utils.py
@Project        : nonebot2_miya 
@Description    : 异步任务工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import inspect
import asyncio
from asyncio import Future
from asyncio.exceptions import TimeoutError as _TimeoutError
from typing import TypeVar, ParamSpec, Callable, Generator, Coroutine, Awaitable, Any
from functools import wraps, partial

from nonebot import logger
from nonebot.exception import AdapterException, NoneBotException
from omega_miya.exception import OmegaException, WebSourceException


P = ParamSpec("P")
T = TypeVar("T")
R = TypeVar("R")


class ExceededAttemptError(OmegaException):
    """重试次数超过限制异常"""


def retry(attempt_limit: int = 3):
    """装饰器, 自动重试, 仅用于异步函数

    :param attempt_limit: 重试次数上限
    """

    def decorator(func: Callable[P, Coroutine[None, None, R]]) -> Callable[P, Coroutine[None, None, R]]:
        if not inspect.iscoroutinefunction(func):
            raise ValueError('The decorated function must be coroutine function')

        @wraps(func)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            attempts_num = 0
            _module = inspect.getmodule(func)
            while attempts_num < attempt_limit:
                try:
                    return await func(*args, **kwargs)
                except _TimeoutError:
                    logger.opt(colors=True).debug(
                        f'<lc>Decorator Retry</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                        f'{func.__name__}</ly> <r>Attempted {attempts_num + 1} times</r> <c>></c> <r>TimeoutError</r>')
                except Exception as e:
                    logger.opt(colors=True).warning(
                        f'<lc>Decorator Retry</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                        f'{func.__name__}</ly> <r>Attempted {attempts_num + 1} times</r> <c>></c> '
                        f'<r>Exception {e.__class__.__name__}</r>: {e}')
                finally:
                    attempts_num += 1
            else:
                logger.opt(colors=True).error(
                    f'<lc>Decorator Retry</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                    f'{func.__name__}</ly> <r>Attempted {attempts_num} times</r> <c>></c> '
                    f'<r>Exception ExceededAttemptError</r>: The number of failures exceeds the limit of attempts. '
                    f'<lc>Parameters(args={args}, kwargs={kwargs})</lc>')
                raise ExceededAttemptError('The number of failures exceeds the limit of attempts')
        return _wrapper

    return decorator


def run_sync(func: Callable[P, R]) -> Callable[P, Coroutine[None, None, R]]:
    """一个用于包装 sync function 为 async function 的装饰器

    :param func: 被装饰的同步函数
    """

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        loop = asyncio.get_running_loop()
        p_func = partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, p_func)

    return _wrapper


def run_async_delay(delay_time: float = 5):
    """一个用于包装 async function 使其延迟运行的装饰器

    :param delay_time: 延迟的时间, 单位秒
    """

    def decorator(func: Callable[P, Coroutine[None, None, R]]) -> Callable[P, Coroutine[None, None, R]]:
        if not inspect.iscoroutinefunction(func):
            raise ValueError('The decorated function must be coroutine function')

        @wraps(func)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            _module = inspect.getmodule(func)
            logger.opt(colors=True).debug(
                f'<lc>Decorator RunAsyncDelay</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> Running delay {delay_time} second(s)')
            await asyncio.sleep(delay=delay_time)
            return await func(*args, **kwargs)

        return _wrapper

    return decorator


def run_async_catching_exception(
        func: Callable[P, Coroutine[None, None, R]]
) -> Callable[P, Coroutine[None, None, R | Exception]]:
    """一个用于包装 async function 捕获所有异常并作为返回值返回的装饰器

    :param func: 被装饰的异步函数
    """
    if not inspect.iscoroutinefunction(func):
        raise ValueError('The decorated function must be coroutine function')

    @wraps(func)
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R | Exception:
        _module = inspect.getmodule(func)
        _module_name = _module.__name__ if _module is not None else 'Unknown'
        try:
            result = await func(*args, **kwargs)
        except AdapterException as e:
            logger.opt(colors=True).error(
                f'<lc>Decorator RunAsyncCatchingException</lc> | <ly>{_module_name}.{func.__name__}</ly> '
                f'<r>raise AdapterException</r> <c>></c> <r>Exception {e.__class__.__name__}</r>: {e}')
            result = e
        except NoneBotException as e:
            logger.opt(colors=True).info(
                f'<lc>Decorator RunAsyncCatchingException</lc> | <ly>{_module_name}.{func.__name__}</ly> '
                f'<r>raise NoneBotException</r> <c>></c> <r>Exception {e.__class__.__name__}</r>: {e}')
            result = e
        except WebSourceException as e:
            logger.opt(colors=True).error(
                f'<lc>Decorator RunAsyncCatchingException</lc> | <ly>{_module_name}.{func.__name__}</ly> '
                f'<r>raise WebSourceException</r> <c>></c> <ly>Failed to fetch network resource</ly>: {e}')
            result = e
        except ExceededAttemptError as e:
            logger.opt(colors=True).error(
                f'<lc>Decorator RunAsyncCatchingException</lc> | <ly>{_module_name}.{func.__name__}</ly> '
                f'<r>raise ExceededAttemptError</r> <c>></c> <ly>Failed to attempt too many times</ly>: {e}')
            result = e
        except AssertionError as e:
            logger.opt(colors=True).error(
                f'<lc>Decorator RunAsyncCatchingException</lc> | <ly>{_module_name}.{func.__name__}</ly> '
                f'<r>raise AssertionError</r> <c>></c> {e}')
            result = e
        except Exception as e:
            logger.opt(colors=True).exception(
                f'<lc>Decorator RunAsyncCatchingException</lc> | <ly>{_module_name}.{func.__name__}</ly> '
                f'<r>raise Exception {e.__class__.__name__}</r> <c>></c> '
                f'There are something wrong(s) in function running')
            result = e
        return result

    return _wrapper


async def semaphore_gather(
        tasks: list[Future[T] | Coroutine[Any, Any, T] | Generator[Any, Any, T] | Awaitable[T]],
        semaphore_num: int,
        *,
        return_exceptions: bool = True) -> tuple[T | BaseException, ...]:
    """使用 asyncio.Semaphore 来限制一批需要并行的异步函数

    :param tasks: 任务序列
    :param semaphore_num: 单次并行的信号量限制
    :param return_exceptions: 是否在结果中包含异常
    """
    _semaphore = asyncio.Semaphore(semaphore_num)

    async def _wrap_coro(
            coro: Future[T] | Coroutine[Any, Any, T] | Generator[Any, Any, T] | Awaitable[T]) -> Coroutine[Any, Any, T]:
        async with _semaphore:
            return await coro

    return await asyncio.gather(*(_wrap_coro(coro) for coro in tasks), return_exceptions=return_exceptions)


__all__ = [
    'retry',
    'run_sync',
    'run_async_delay',
    'run_async_catching_exception',
    'semaphore_gather'
]
