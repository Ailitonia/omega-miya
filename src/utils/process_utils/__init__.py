"""
@Author         : Ailitonia
@Date           : 2021/07/29 19:29
@FileName       : process_utils.py
@Project        : nonebot2_miya 
@Description    : 异步任务工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import asyncio
import inspect
from asyncio import Future
from functools import wraps
from typing import Any, Awaitable, Callable, Coroutine, Literal, Sequence, overload

from nonebot import logger


def run_async_delay(delay_time: float = 5):
    """一个用于包装 async function 使其延迟运行的装饰器

    :param delay_time: 延迟的时间, 单位秒
    """

    def decorator[R, ** P](func: Callable[P, Coroutine[None, None, R]]) -> Callable[P, Coroutine[None, None, R]]:
        if not inspect.iscoroutinefunction(func):
            raise ValueError('The decorated function must be coroutine function')

        @wraps(func)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            _module = inspect.getmodule(func)
            logger.opt(colors=True).debug(
                f'<lc>Decorator RunAsyncDelay</lc> | <ly>{_module.__name__ if _module is not None else "Unknown"}.'
                f'{func.__name__}</ly> <c>></c> will delay execution after {delay_time} second(s)')
            await asyncio.sleep(delay=delay_time)
            return await func(*args, **kwargs)

        return _wrapper

    return decorator


@overload
async def semaphore_gather[T](
        tasks: Sequence[Future[T] | Coroutine[Any, Any, T] | Awaitable[T]],
        semaphore_num: int,
        *,
        return_exceptions: Literal[True] = True,
        filter_exception: Literal[False] = False,
) -> tuple[T | Exception, ...]:
    ...


@overload
async def semaphore_gather[T](
        tasks: Sequence[Future[T] | Coroutine[Any, Any, T] | Awaitable[T]],
        semaphore_num: int,
        *,
        return_exceptions: Literal[True] = True,
        filter_exception: Literal[True] = True,
) -> tuple[T, ...]:
    ...


@overload
async def semaphore_gather[T](
        tasks: Sequence[Future[T] | Coroutine[Any, Any, T] | Awaitable[T]],
        semaphore_num: int,
        *,
        return_exceptions: Literal[False] = False,
        filter_exception: bool = False,
) -> tuple[T, ...]:
    ...


async def semaphore_gather[T](
        tasks: Sequence[Future[T] | Coroutine[Any, Any, T] | Awaitable[T]],
        semaphore_num: int,
        *,
        return_exceptions: bool = True,
        filter_exception: bool = False,
) -> tuple[T | Exception, ...]:
    """使用 asyncio.Semaphore 来限制一批需要并行的异步函数
    Python 3.11 推荐使用 asyncio.TaskGroup 创建和并发运行任务并等待它们完成

    :param tasks: 任务序列
    :param semaphore_num: 单次并行的信号量限制
    :param return_exceptions: 是否将异常视为成功结果, 并在结果列表中聚合
    :param filter_exception: 是否过滤掉返回值中的异常
    """
    _stack_frame = inspect.stack()[1].frame
    _f_name = _stack_frame.f_code.co_name
    _f_filename = _stack_frame.f_code.co_filename

    _semaphore = asyncio.Semaphore(semaphore_num)
    logger.opt(colors=True).debug(
        f'<lc>SemaphoreGather</lc> | <lc>"{_f_name}"</lc> in <lc>"{_f_filename}"</lc> created {len(tasks)} task(s) '
        f'and will be executed immediately'
    )

    async def _wrap_coro(
            coro: Future[T] | Coroutine[Any, Any, T] | Awaitable[T]
    ) -> T | Exception:
        """使用 asyncio.Semaphore 限制单个任务"""
        async with _semaphore:
            try:
                _result = await coro
                return _result
            except Exception as e:
                if return_exceptions:
                    return e
                else:
                    raise e

    async with asyncio.TaskGroup() as tg:
        group_tasks = [tg.create_task(_wrap_coro(coro)) for coro in tasks]

    result = tuple(task.result() for task in group_tasks)

    # 输出错误日志
    for i, r in enumerate(result):
        if isinstance(r, ExceptionGroup):
            logger.opt(colors=True).error(
                f'<lc>SemaphoreGather</lc> | Task(s) called by <lc>"{_f_name}"</lc> in <lc>"{_f_filename}"</lc> '
                f'raised <r>{r.__class__.__name__}</r> exceptions in task(<ly>{i}</ly>): '
                f'<ly>{", ".join(str(x) for x in r.exceptions)}</ly>'
            )
        if isinstance(r, Exception):
            logger.opt(colors=True).error(
                f'<lc>SemaphoreGather</lc> | Task(s) called by <lc>"{_f_name}"</lc> in <lc>"{_f_filename}"</lc> '
                f'raised <r>{r.__class__.__name__}</r> exception in task(<ly>{i}</ly>): <ly>{r}</ly>'
            )

    # 过滤异常
    if filter_exception:
        result = tuple(x for x in result if not isinstance(x, Exception))

    logger.opt(colors=True).debug(
        f'<lc>SemaphoreGather</lc> | All task(s) called by <lc>"{_f_name}"</lc> in <lc>"{_f_filename}"</lc> '
        f'had be executed completed'
    )

    return result


__all__ = [
    'run_async_delay',
    'semaphore_gather'
]
