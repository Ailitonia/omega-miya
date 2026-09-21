"""
@Author         : Ailitonia
@Date           : 2026/9/20 11:25
@FileName       : test_005_process_utils
@Project        : omega-miya
@Description    : 异步任务工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio

import pytest


class TestRunAsyncDelay:
    """run_async_delay 装饰器"""

    def test_decorate_non_coroutine_raises(self):
        from src.utils.process_utils import run_async_delay

        def _sync_func() -> int:
            return 1

        with pytest.raises(ValueError, match='coroutine'):
            run_async_delay(delay_time=1)(_sync_func)

    async def test_result_and_args_passthrough(self):
        from src.utils.process_utils import run_async_delay

        @run_async_delay(delay_time=0)
        async def _func(a: int, *, b: int) -> tuple[int, int]:
            return a, b

        assert await _func(1, b=2) == (1, 2)

    async def test_wraps_metadata_preserved(self):
        from src.utils.process_utils import run_async_delay

        @run_async_delay(delay_time=0)
        async def _named() -> None:
            return None

        assert _named.__name__ == '_named'
        assert _named.__wrapped__ is not None

    async def test_delay_applied(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.process_utils import run_async_delay

        _recorded: list[float | None] = []

        async def _fake_sleep(*, delay: float | None = None) -> None:
            _recorded.append(delay)

        monkeypatch.setattr('src.utils.process_utils.asyncio.sleep', _fake_sleep)

        @run_async_delay(delay_time=0.2)
        async def _func() -> str:
            return 'ok'

        assert await _func() == 'ok'
        assert _recorded == [0.2]

    async def test_random_sigma_uses_absolute_delay(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.process_utils import run_async_delay

        _recorded: list[float | None] = []

        async def _fake_sleep(*, delay: float | None = None) -> None:
            _recorded.append(delay)

        monkeypatch.setattr('src.utils.process_utils.random.gauss', lambda mu, sigma: -1.0)
        monkeypatch.setattr('src.utils.process_utils.asyncio.sleep', _fake_sleep)

        @run_async_delay(delay_time=5, random_sigma=1)
        async def _func() -> str:
            return 'ok'

        assert await _func() == 'ok'
        assert _recorded == [1.0]

    def test_negative_delay_time_raises(self):
        from src.utils.process_utils import run_async_delay

        with pytest.raises(ValueError, match='delay_time'):
            run_async_delay(delay_time=-1)

    def test_zero_random_sigma_raises(self):
        from src.utils.process_utils import run_async_delay

        with pytest.raises(ValueError, match='random_sigma'):
            run_async_delay(delay_time=5, random_sigma=0)

    def test_negative_random_sigma_raises(self):
        from src.utils.process_utils import run_async_delay

        with pytest.raises(ValueError, match='random_sigma'):
            run_async_delay(delay_time=5, random_sigma=-0.1)

    async def test_default_delay_time(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.process_utils import run_async_delay

        _recorded: list[float | None] = []

        async def _fake_sleep(*, delay: float | None = None) -> None:
            _recorded.append(delay)

        monkeypatch.setattr('src.utils.process_utils.asyncio.sleep', _fake_sleep)

        @run_async_delay()
        async def _func() -> str:
            return 'ok'

        assert await _func() == 'ok'
        assert _recorded == [5]

    def test_nan_delay_time_raises(self):
        from src.utils.process_utils import run_async_delay

        with pytest.raises(ValueError, match='delay_time'):
            run_async_delay(delay_time=float('nan'))

    def test_inf_delay_time_raises(self):
        from src.utils.process_utils import run_async_delay

        with pytest.raises(ValueError, match='delay_time'):
            run_async_delay(delay_time=float('inf'))

    def test_nan_random_sigma_raises(self):
        from src.utils.process_utils import run_async_delay

        with pytest.raises(ValueError, match='random_sigma'):
            run_async_delay(delay_time=5, random_sigma=float('nan'))

    def test_inf_random_sigma_raises(self):
        from src.utils.process_utils import run_async_delay

        with pytest.raises(ValueError, match='random_sigma'):
            run_async_delay(delay_time=5, random_sigma=float('inf'))


class TestRunAsyncWithTimeLimited:
    """run_async_with_time_limited 装饰器"""

    def test_decorate_non_coroutine_raises(self):
        from src.utils.process_utils import run_async_with_time_limited

        def _sync_func() -> int:
            return 1

        with pytest.raises(ValueError, match='coroutine'):
            run_async_with_time_limited(delay_time=1)(_sync_func)

    async def test_completes_within_limit_and_passthrough(self):
        from src.utils.process_utils import run_async_with_time_limited

        @run_async_with_time_limited(delay_time=5)
        async def _func(a: int, *, b: int) -> tuple[int, int]:
            await asyncio.sleep(0.01)
            return a, b

        assert await _func(1, b=2) == (1, 2)

    async def test_timeout_raises_timeout_error(self):
        from src.utils.process_utils import run_async_with_time_limited

        @run_async_with_time_limited(delay_time=0.05)
        async def _func() -> str:
            await asyncio.sleep(1)
            return 'ok'

        with pytest.raises(TimeoutError):
            await _func()

    async def test_timeout_raises_timeout_error_with_shield(self):
        from src.utils.process_utils import run_async_with_time_limited

        @run_async_with_time_limited(delay_time=0.05, shield=True)
        async def _func() -> str:
            await asyncio.sleep(1)
            return 'ok'

        with pytest.raises(TimeoutError):
            await _func()

    async def test_original_exception_passthrough(self):
        from src.utils.process_utils import run_async_with_time_limited

        @run_async_with_time_limited(delay_time=5)
        async def _func() -> None:
            raise ValueError('boom')

        with pytest.raises(ValueError, match='boom'):
            await _func()

    async def test_float_delay_time_accepted(self):
        from src.utils.process_utils import run_async_with_time_limited

        @run_async_with_time_limited(delay_time=0.5)
        async def _func() -> str:
            return 'ok'

        assert await _func() == 'ok'

    def test_negative_delay_time_raises(self):
        from src.utils.process_utils import run_async_with_time_limited

        with pytest.raises(ValueError, match='delay_time'):
            run_async_with_time_limited(delay_time=-1)

    async def test_zero_delay_time_times_out_immediately(self):
        from src.utils.process_utils import run_async_with_time_limited

        @run_async_with_time_limited(delay_time=0)
        async def _func() -> str:
            await asyncio.sleep(0.01)
            return 'ok'

        with pytest.raises(TimeoutError):
            await _func()

    def test_nan_delay_time_raises(self):
        from src.utils.process_utils import run_async_with_time_limited

        with pytest.raises(ValueError, match='delay_time'):
            run_async_with_time_limited(delay_time=float('nan'))

    def test_inf_delay_time_raises(self):
        from src.utils.process_utils import run_async_with_time_limited

        with pytest.raises(ValueError, match='delay_time'):
            run_async_with_time_limited(delay_time=float('inf'))


class TestSemaphoreGather:
    """semaphore_gather 并发任务聚合"""

    @staticmethod
    async def _ok_coro(value: str = 'ok') -> str:
        await asyncio.sleep(0.01)
        return value

    @staticmethod
    async def _fail_coro() -> None:
        raise ValueError('bad')

    async def test_empty_tasks_returns_empty(self):
        from src.utils.process_utils import semaphore_gather

        assert await semaphore_gather(tasks=[], semaphore_num=1) == ()

    async def test_results_in_input_order(self):
        from src.utils.process_utils import semaphore_gather

        async def _coro(i: int) -> int:
            await asyncio.sleep(0.01 * (5 - i))
            return i * 10

        assert await semaphore_gather([_coro(i) for i in range(5)], 2) == (0, 10, 20, 30, 40)

    async def test_semaphore_limits_concurrency(self):
        from src.utils.process_utils import semaphore_gather

        _state = {'current': 0, 'max': 0}

        async def _coro(i: int) -> int:
            _state['current'] += 1
            _state['max'] = max(_state['max'], _state['current'])
            await asyncio.sleep(0.05)
            _state['current'] -= 1
            return i

        _results = await semaphore_gather([_coro(i) for i in range(6)], 2)
        assert _results == tuple(range(6))
        assert 1 <= _state['max'] <= 2

    async def test_return_exceptions_true_aggregates_in_place(self):
        from src.utils.process_utils import semaphore_gather

        _tasks = [self._ok_coro('a'), self._fail_coro(), self._ok_coro('b')]
        _result = await semaphore_gather(tasks=_tasks, semaphore_num=3, return_exceptions=True)

        assert _result[0] == 'a'
        assert isinstance(_result[1], ValueError)
        assert str(_result[1]) == 'bad'
        assert _result[2] == 'b'

    async def test_return_exceptions_false_raises_original_exception(self):
        from src.utils.process_utils import semaphore_gather

        _tasks = [self._ok_coro('a'), self._fail_coro(), self._ok_coro('b')]
        with pytest.raises(ValueError, match='bad'):
            await semaphore_gather(tasks=_tasks, semaphore_num=3, return_exceptions=False)

    async def test_return_exceptions_false_siblings_not_cancelled(self):
        from src.utils.process_utils import semaphore_gather

        _completed: list[str] = []

        async def _slow_ok() -> str:
            await asyncio.sleep(0.15)
            _completed.append('slow')
            return 'slow'

        async def _fast_ok() -> str:
            _completed.append('fast')
            return 'fast'

        _tasks = [_slow_ok(), self._fail_coro(), _fast_ok()]
        with pytest.raises(ValueError, match='bad'):
            await semaphore_gather(tasks=_tasks, semaphore_num=3, return_exceptions=False)

        assert sorted(_completed) == ['fast', 'slow']

    async def test_filter_exception_filters_results(self):
        from src.utils.process_utils import semaphore_gather

        _tasks = [self._ok_coro('a'), self._fail_coro(), self._ok_coro('b')]
        _result = await semaphore_gather(tasks=_tasks, semaphore_num=3, filter_exception=True)
        assert _result == ('a', 'b')

    async def test_filter_exception_with_return_exceptions_false_still_raises(self):
        from src.utils.process_utils import semaphore_gather

        _tasks = [self._ok_coro('a'), self._fail_coro()]
        with pytest.raises(ValueError, match='bad'):
            await semaphore_gather(
                tasks=_tasks, semaphore_num=2, return_exceptions=False, filter_exception=True
            )

    async def test_accepts_scheduled_task_and_future(self):
        from src.utils.process_utils import semaphore_gather

        async def _coro(value: str) -> str:
            await asyncio.sleep(0.01)
            return value

        _task = asyncio.ensure_future(_coro('task'))
        _future = asyncio.get_running_loop().create_future()

        async def _resolve_future() -> None:
            await asyncio.sleep(0.01)
            _future.set_result('future')

        asyncio.get_running_loop().create_task(_resolve_future())

        _result = await semaphore_gather([_task, _future, _coro('coro')], 2)
        assert _result == ('task', 'future', 'coro')

    async def test_cancelled_error_propagates(self):
        from src.utils.process_utils import semaphore_gather

        async def _cancel_coro() -> None:
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await semaphore_gather(tasks=[_cancel_coro()], semaphore_num=1)

    async def test_exception_group_returned_as_result(self):
        from src.utils.process_utils import semaphore_gather

        async def _grouped_coro() -> str:
            async with asyncio.TaskGroup():
                raise ValueError('inner')
            return 'unreachable'

        _result = await semaphore_gather([_grouped_coro(), self._ok_coro()], 2, return_exceptions=True)
        assert isinstance(_result[0], ExceptionGroup)
        assert any(isinstance(x, ValueError) for x in _result[0].exceptions)
        assert _result[1] == 'ok'

    async def test_semaphore_num_zero_raises_value_error(self):
        from src.utils.process_utils import semaphore_gather

        with pytest.raises(ValueError, match='semaphore_num'):
            await semaphore_gather(tasks=[], semaphore_num=0)

    async def test_semaphore_num_negative_raises_value_error(self):
        from src.utils.process_utils import semaphore_gather

        with pytest.raises(ValueError, match='semaphore_num'):
            await semaphore_gather(tasks=[], semaphore_num=-1)

    async def test_semaphore_num_non_int_raises_value_error(self):
        from src.utils.process_utils import semaphore_gather

        with pytest.raises(ValueError, match='semaphore_num'):
            await semaphore_gather(tasks=[], semaphore_num='2')

    async def test_semaphore_num_bool_raises_value_error(self):
        from src.utils.process_utils import semaphore_gather

        with pytest.raises(ValueError, match='semaphore_num'):
            await semaphore_gather(tasks=[], semaphore_num=True)

    async def test_semaphore_num_float_raises_value_error(self):
        from src.utils.process_utils import semaphore_gather

        with pytest.raises(ValueError, match='semaphore_num'):
            await semaphore_gather(tasks=[], semaphore_num=2.0)


class TestModuleExports:
    """模块导出完整性"""

    def test_all_exports(self):
        from src.utils import process_utils

        assert set(process_utils.__all__) == {'run_async_delay', 'run_async_with_time_limited', 'semaphore_gather'}
        for _name in process_utils.__all__:
            assert callable(getattr(process_utils, _name))
