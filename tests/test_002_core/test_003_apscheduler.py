"""
@Author         : Ailitonia
@Date           : 2026/9/4 18:00
@FileName       : test_003_apscheduler
@Project        : omega-miya
@Description    : src.service.apscheduler 定时任务模块单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

_TEST_JOB_ID = 'test_apscheduler_job'
"""测试用计划任务 ID"""


def _dummy_job_func() -> None:
    """add_job 测试用空函数(模块级定义以保证 func_ref 可解析)"""


@pytest.fixture
def mock_job() -> MagicMock:
    """Job 的 Mock 对象(隔离真实调度器, 仅校验 reschedule_job 内部交互)"""
    return MagicMock(spec=Job)


@pytest.fixture
def fresh_scheduler() -> AsyncIOScheduler:
    """未启动的新建调度器实例, 与模块全局 scheduler 隔离"""
    return AsyncIOScheduler()


@pytest.fixture
def pending_job(fresh_scheduler: AsyncIOScheduler) -> Job:
    """未启动调度器上的 pending job(默认 cron 触发器)"""
    return fresh_scheduler.add_job(_dummy_job_func, 'cron', minute='0', id=_TEST_JOB_ID)


@pytest.fixture
async def running_scheduler() -> AsyncGenerator[AsyncIOScheduler, None]:
    """已启动的新建调度器实例(覆盖 jobstore 更新路径), 测试后关闭清理"""
    scheduler = AsyncIOScheduler()
    scheduler.start()
    yield scheduler
    scheduler.shutdown()


class TestModuleContract:
    """模块导出契约测试"""

    def test_all_exports(self):
        import src.service.apscheduler

        assert src.service.apscheduler.__all__ == ['scheduler', 'reschedule_job']

    def test_scheduler_is_plugin_scheduler(self):
        from nonebot_plugin_apscheduler import scheduler as plugin_scheduler

        from src.service.apscheduler import scheduler

        assert scheduler is plugin_scheduler
        assert isinstance(scheduler, AsyncIOScheduler)

    def test_reschedule_job_is_utils_function(self):
        from src.service.apscheduler import reschedule_job
        from src.service.apscheduler.utils import reschedule_job as utils_reschedule_job

        assert reschedule_job is utils_reschedule_job

    def test_utils_all_exports(self):
        import src.service.apscheduler.utils

        assert src.service.apscheduler.utils.__all__ == ['reschedule_job']


class TestTriggerModeDispatch:
    """trigger_mode 分派测试(Mock Job 层)"""

    def test_date_mode_constructs_date_trigger(self, mock_job: MagicMock):
        from src.service.apscheduler import reschedule_job

        run_date = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
        reschedule_job(job=mock_job, trigger_mode='date', run_date=run_date)

        trigger = mock_job.reschedule.call_args.kwargs['trigger']
        assert isinstance(trigger, DateTrigger)
        assert trigger.run_date == run_date

    def test_cron_mode_constructs_cron_trigger(self, mock_job: MagicMock):
        from src.service.apscheduler import reschedule_job

        reschedule_job(job=mock_job, trigger_mode='cron', hour='12', minute='*/5')

        trigger = mock_job.reschedule.call_args.kwargs['trigger']
        assert isinstance(trigger, CronTrigger)
        fields = {field.name: str(field) for field in trigger.fields}
        assert fields['hour'] == '12'
        assert fields['minute'] == '*/5'

    def test_interval_mode_constructs_interval_trigger(self, mock_job: MagicMock):
        from src.service.apscheduler import reschedule_job

        reschedule_job(job=mock_job, trigger_mode='interval', minutes=5, seconds=30)

        trigger = mock_job.reschedule.call_args.kwargs['trigger']
        assert isinstance(trigger, IntervalTrigger)
        assert trigger.interval == timedelta(minutes=5, seconds=30)

    def test_trigger_args_passed_to_trigger_not_reschedule(self, mock_job: MagicMock):
        """trigger_args 应仅用于构造触发器, 不应泄漏给 Job.reschedule"""
        from src.service.apscheduler import reschedule_job

        reschedule_job(job=mock_job, trigger_mode='interval', minutes=5)

        mock_job.reschedule.assert_called_once()
        assert mock_job.reschedule.call_args.args == ()
        assert set(mock_job.reschedule.call_args.kwargs) == {'trigger'}

    @pytest.mark.parametrize('mode', ['DATE', 'unknown', '', None, 123, b'date'])
    def test_invalid_trigger_mode_raises(self, mock_job: MagicMock, mode: Any):
        from src.service.apscheduler import reschedule_job

        with pytest.raises(ValueError, match='Invalid trigger_mode'):
            reschedule_job(job=mock_job, trigger_mode=mode)
        mock_job.reschedule.assert_not_called()


class TestTriggerArgsValidation:
    """trigger_args 透传校验与错误传播测试(Mock Job 层)"""

    @pytest.mark.parametrize('mode', ['date', 'cron', 'interval'])
    def test_unknown_trigger_arg_raises_type_error(self, mock_job: MagicMock, mode: Any):
        from src.service.apscheduler import reschedule_job

        with pytest.raises(TypeError, match='unexpected keyword argument'):
            reschedule_job(job=mock_job, trigger_mode=mode, unexpected_arg=1)
        mock_job.reschedule.assert_not_called()

    def test_invalid_cron_field_value_raises(self, mock_job: MagicMock):
        from src.service.apscheduler import reschedule_job

        with pytest.raises(ValueError, match='Unrecognized expression'):
            reschedule_job(job=mock_job, trigger_mode='cron', minute='not-a-cron')
        mock_job.reschedule.assert_not_called()

    def test_invalid_date_run_date_type_raises(self, mock_job: MagicMock):
        from src.service.apscheduler import reschedule_job

        with pytest.raises(TypeError, match='Unsupported type for run_date'):
            reschedule_job(job=mock_job, trigger_mode='date', run_date=123)
        mock_job.reschedule.assert_not_called()


class TestRescheduleReturnValue:
    """返回值与内部异常传播测试(Mock Job 层)"""

    def test_returns_reschedule_result(self, mock_job: MagicMock):
        """返回值为 Job.reschedule 的结果(APScheduler 3.x 为 job 自身)"""
        from src.service.apscheduler import reschedule_job

        sentinel = object()
        mock_job.reschedule.return_value = sentinel

        assert reschedule_job(job=mock_job, trigger_mode='interval', minutes=5) is sentinel

    def test_reschedule_error_propagates(self, mock_job: MagicMock):
        """Job.reschedule 内部异常应原样传播, 不被静默吞掉"""
        from src.service.apscheduler import reschedule_job

        mock_job.reschedule.side_effect = RuntimeError('boom')

        with pytest.raises(RuntimeError, match='boom'):
            reschedule_job(job=mock_job, trigger_mode='interval', minutes=5)


class TestRescheduleOnPendingJob:
    """未启动调度器(pending job)上的 reschedule 行为测试(真实调度器, 同步路径)"""

    def test_job_is_pending_before_reschedule(self, pending_job: Job):
        assert pending_job.pending
        assert not hasattr(pending_job, 'next_run_time')

    def test_reschedule_to_interval(self, pending_job: Job):
        from src.service.apscheduler import reschedule_job

        before = datetime.now(UTC)
        result = reschedule_job(job=pending_job, trigger_mode='interval', minutes=5)
        after = datetime.now(UTC)

        assert result is pending_job
        assert isinstance(pending_job.trigger, IntervalTrigger)
        assert pending_job.trigger.interval == timedelta(minutes=5)
        assert before + timedelta(minutes=5) <= pending_job.next_run_time <= after + timedelta(minutes=5)

    def test_reschedule_to_cron(self, pending_job: Job):
        from src.service.apscheduler import reschedule_job

        result = reschedule_job(job=pending_job, trigger_mode='cron', minute='*/5')

        assert result is pending_job
        assert isinstance(pending_job.trigger, CronTrigger)
        fields = {field.name: str(field) for field in pending_job.trigger.fields}
        assert fields['minute'] == '*/5'
        assert pending_job.next_run_time is not None

    def test_reschedule_to_date(self, pending_job: Job):
        from src.service.apscheduler import reschedule_job

        run_date = datetime(2030, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = reschedule_job(job=pending_job, trigger_mode='date', run_date=run_date)

        assert result is pending_job
        assert isinstance(pending_job.trigger, DateTrigger)
        assert pending_job.trigger.run_date == run_date
        assert pending_job.next_run_time == run_date

    def test_reschedule_to_date_with_str_run_date(self, pending_job: Job):
        from src.service.apscheduler import reschedule_job

        reschedule_job(job=pending_job, trigger_mode='date', run_date='2030-01-01 12:00:00')

        assert isinstance(pending_job.trigger, DateTrigger)
        assert pending_job.trigger.run_date.replace(tzinfo=None) == datetime(2030, 1, 1, 12, 0, 0)

    def test_reschedule_to_date_default_run_date_is_now(self, pending_job: Job):
        """date 模式缺省 run_date 时默认当前时刻"""
        from src.service.apscheduler import reschedule_job

        before = datetime.now(UTC)
        reschedule_job(job=pending_job, trigger_mode='date')
        after = datetime.now(UTC)

        assert isinstance(pending_job.trigger, DateTrigger)
        assert before <= pending_job.trigger.run_date <= after
        assert before <= pending_job.next_run_time <= after

    def test_reschedule_to_past_date_not_blocked(self, pending_job: Job):
        """APScheduler 透传语义: 过去时刻不拦截, next_run_time 即为该时刻"""
        from src.service.apscheduler import reschedule_job

        run_date = datetime(2020, 1, 1, tzinfo=UTC)
        reschedule_job(job=pending_job, trigger_mode='date', run_date=run_date)

        assert pending_job.next_run_time == run_date

    def test_reschedule_to_interval_without_args_coerced(self, pending_job: Job):
        """interval 模式零参数时 APScheduler 静默修正为 1 秒间隔"""
        from src.service.apscheduler import reschedule_job

        reschedule_job(job=pending_job, trigger_mode='interval')

        assert isinstance(pending_job.trigger, IntervalTrigger)
        assert pending_job.trigger.interval_length == 1

    def test_sequential_reschedule(self, pending_job: Job):
        """连续多次 reschedule 可组合, 最终触发器与下次运行时间以最后一次为准"""
        from src.service.apscheduler import reschedule_job

        reschedule_job(job=pending_job, trigger_mode='interval', minutes=5)
        assert isinstance(pending_job.trigger, IntervalTrigger)

        run_date = datetime(2030, 1, 1, tzinfo=UTC)
        reschedule_job(job=pending_job, trigger_mode='date', run_date=run_date)

        assert isinstance(pending_job.trigger, DateTrigger)
        assert pending_job.next_run_time == run_date

    def test_job_attributes_preserved_after_reschedule(self, pending_job: Job):
        from src.service.apscheduler import reschedule_job

        reschedule_job(job=pending_job, trigger_mode='interval', minutes=5)

        assert pending_job.id == _TEST_JOB_ID
        assert pending_job.func is _dummy_job_func

    def test_reschedule_removed_job_raises(self, pending_job: Job, fresh_scheduler: AsyncIOScheduler):
        from apscheduler.jobstores.base import JobLookupError

        from src.service.apscheduler import reschedule_job

        fresh_scheduler.remove_job(pending_job.id)

        with pytest.raises(JobLookupError):
            reschedule_job(job=pending_job, trigger_mode='interval', minutes=5)


class TestRescheduleOnRunningScheduler:
    """已启动调度器(jobstore 落库 job)上的 reschedule 行为测试(异步路径)"""

    async def test_reschedule_updates_stored_job(self, running_scheduler: AsyncIOScheduler):
        from src.service.apscheduler import reschedule_job

        job = running_scheduler.add_job(_dummy_job_func, 'cron', minute='0', id=_TEST_JOB_ID)
        assert not job.pending

        result = reschedule_job(job=job, trigger_mode='interval', minutes=5)

        assert result is job
        stored_job = running_scheduler.get_job(_TEST_JOB_ID)
        assert stored_job is not None
        assert isinstance(stored_job.trigger, IntervalTrigger)
        assert stored_job.trigger.interval == timedelta(minutes=5)
        assert stored_job.next_run_time is not None

    async def test_reschedule_recomputes_next_run_time(self, running_scheduler: AsyncIOScheduler):
        from src.service.apscheduler import reschedule_job

        job = running_scheduler.add_job(_dummy_job_func, 'cron', minute='0', id=_TEST_JOB_ID)
        before = datetime.now(UTC)
        reschedule_job(job=job, trigger_mode='interval', minutes=5)
        after = datetime.now(UTC)

        stored_job = running_scheduler.get_job(_TEST_JOB_ID)
        assert stored_job is not None
        assert before + timedelta(minutes=5) <= stored_job.next_run_time <= after + timedelta(minutes=5)

    async def test_reschedule_removed_job_raises(self, running_scheduler: AsyncIOScheduler):
        from apscheduler.jobstores.base import JobLookupError

        from src.service.apscheduler import reschedule_job

        job = running_scheduler.add_job(_dummy_job_func, 'cron', minute='0', id=_TEST_JOB_ID)
        running_scheduler.remove_job(job.id)

        with pytest.raises(JobLookupError):
            reschedule_job(job=job, trigger_mode='interval', minutes=5)
