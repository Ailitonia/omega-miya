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
import math
import random
from asyncio import Future
from collections.abc import Awaitable, Callable, Coroutine, Sequence
from functools import wraps
from typing import Any, Literal, overload

from anyio import fail_after
from nonebot import logger


def run_async_delay(delay_time: float = 5, *, random_sigma: float | None = None):
    """一个用于包装 async function 使其延迟运行的装饰器

    启用 random_sigma 时实际延迟为 abs(random.gauss(delay_time, random_sigma)), 呈折叠正态分布 (负值截断为正)。
    注意: 正态分布无理论上限, 极端情况下实际延迟可能远超 delay_time。

    :param delay_time: 延迟的时间, 单位秒, 必须为有限的非负数
    :param random_sigma: 启用延迟随机分布的标准差, 必须为有限的正数
    """
    if not math.isfinite(delay_time) or delay_time < 0:
        raise ValueError(f'delay_time must be a finite number >= 0, got {delay_time!r}')
    if random_sigma is not None and (not math.isfinite(random_sigma) or random_sigma <= 0):
        raise ValueError(f'random_sigma must be a finite positive number, got {random_sigma!r}')

    def decorator[**P, R, T1, T2](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
        if not inspect.iscoroutinefunction(func):
            raise ValueError('The decorated function must be coroutine function')

        _module = inspect.getmodule(func)
        _func_full_name = f'{_module.__name__ if _module is not None else "Unknown"}.{func.__name__}'

        @wraps(func)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            delay = abs(random.gauss(delay_time, random_sigma)) if random_sigma is not None else delay_time
            logger.opt(colors=True).debug(
                f'<lc>Decorator RunAsyncDelay</lc> | <ly>{_func_full_name}</ly> <c>></c> '
                f'will delay execution after {delay:.2f} second(s)'
            )
            await asyncio.sleep(delay=delay)
            return await func(*args, **kwargs)

        return _wrapper

    return decorator


def run_async_with_time_limited(delay_time: float, *, shield: bool = False):
    """一个用于包装 async function 为其设置超时, 超时后直接抛出 TimeoutError 异常

    :param delay_time: 超时的时间, 单位秒, 必须为有限的非负数 (0 表示立即超时)
    :param shield: set True to shield the cancel scope from external cancellation
    """
    if not math.isfinite(delay_time) or delay_time < 0:
        raise ValueError(f'delay_time must be a finite number >= 0, got {delay_time!r}')

    def decorator[**P, R, T1, T2](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
        if not inspect.iscoroutinefunction(func):
            raise ValueError('The decorated function must be coroutine function')

        @wraps(func)
        async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with fail_after(delay_time, shield=shield):
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
        filter_exception: Literal[False] = False,
) -> tuple[T, ...]:
    ...


@overload
async def semaphore_gather[T](
        tasks: Sequence[Future[T] | Coroutine[Any, Any, T] | Awaitable[T]],
        semaphore_num: int,
        *,
        return_exceptions: Literal[False] = False,
        filter_exception: Literal[True] = True,
) -> tuple[T, ...]:
    ...


@overload
async def semaphore_gather[T](
        tasks: Sequence[Future[T] | Coroutine[Any, Any, T] | Awaitable[T]],
        semaphore_num: int,
        *,
        return_exceptions: bool = ...,
        filter_exception: bool = ...,
) -> tuple[T | Exception, ...]:
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

    所有任务都会执行完成, 单个任务失败不会取消其余任务。
    当 return_exceptions 为 False 时, 等待全部任务执行完成后抛出首个原始异常 (不包装 ExceptionGroup);
    CancelledError 等外部取消仍会立即向外传播。

    注意:
        - tasks 必须为 Sequence (内部依赖 len() 统计任务数量), 不支持生成器等一次性迭代器;
        - 参数校验失败会立即抛出 ValueError, 此时调用方已创建的 coroutine 对象不会被 awaited/closed;
        - KeyboardInterrupt/SystemExit 等 BaseException 不受"所有任务都会执行完成"保证约束, 会中止其余任务并直接传播。

    :param tasks: 任务序列
    :param semaphore_num: 单次并行的信号量限制, 必须为 >= 1 的整数 (不接受 bool)
    :param return_exceptions: 是否将异常视为成功结果, 并在结果列表中聚合
    :param filter_exception: 是否过滤掉返回值中的异常, 仅在 return_exceptions 为 True 时有意义
    """
    if isinstance(semaphore_num, bool) or not isinstance(semaphore_num, int) or semaphore_num < 1:
        raise ValueError(f'semaphore_num must be an integer >= 1, got {semaphore_num!r}')

    # 仅提取调用方函数名与文件名用于日志, 避免 inspect.stack() 的全栈遍历开销及帧引用驻留
    _caller_frame = getattr(inspect.currentframe(), 'f_back', None)
    _f_name = _caller_frame.f_code.co_name if _caller_frame is not None else 'Unknown'
    _f_filename = _caller_frame.f_code.co_filename if _caller_frame is not None else 'Unknown'
    del _caller_frame

    _semaphore = asyncio.Semaphore(semaphore_num)
    logger.opt(colors=True).debug(
        f'<lc>SemaphoreGather</lc> | <lc>"{_f_name}"</lc> in <lc>"{_f_filename}"</lc> created {len(tasks)} task(s) '
        f'and will be executed immediately'
    )

    async def _wrap_coro(
            coro: Future[T] | Coroutine[Any, Any, T] | Awaitable[T]
    ) -> T | Exception:
        """使用 asyncio.Semaphore 限制单个任务, 并将异常统一捕获为返回值, 避免单个任务失败取消其余任务"""
        async with _semaphore:
            try:
                return await coro
            except Exception as e:
                return e

    async with asyncio.TaskGroup() as tg:
        wrapped_tasks = [tg.create_task(_wrap_coro(coro)) for coro in tasks]

    result = tuple(task.result() for task in wrapped_tasks)

    # 输出错误日志
    for i, r in enumerate(result):
        if isinstance(r, ExceptionGroup):
            logger.opt(colors=True).error(
                f'<lc>SemaphoreGather</lc> | Task(s) called by <lc>"{_f_name}"</lc> in <lc>"{_f_filename}"</lc> '
                f'raised <r>{r.__class__.__name__}</r> exceptions in task(<ly>{i}</ly>): '
                f'<ly>{", ".join(str(x) for x in r.exceptions)}</ly>'
            )
        elif isinstance(r, Exception):
            logger.opt(colors=True).error(
                f'<lc>SemaphoreGather</lc> | Task(s) called by <lc>"{_f_name}"</lc> in <lc>"{_f_filename}"</lc> '
                f'raised <r>{r.__class__.__name__}</r> exception in task(<ly>{i}</ly>): <ly>{r}</ly>'
            )

    # 抛出首个原始异常
    if not return_exceptions:
        for r in result:
            if isinstance(r, Exception):
                raise r

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
    'run_async_with_time_limited',
    'semaphore_gather',
]
