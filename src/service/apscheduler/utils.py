"""
@Author         : Ailitonia
@Date           : 2022/05/03 14:39
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : apscheduler utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Literal

from apscheduler.job import Job
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger


def reschedule_job(job: Job, trigger_mode: Literal['date', 'cron', 'interval'], **trigger_args: Any) -> Job:
    """为计划任务构造新的触发器并更新其下一次运行时间"""
    match trigger_mode:
        case 'date':
            trigger = DateTrigger(**trigger_args)
        case 'cron':
            trigger = CronTrigger(**trigger_args)
        case 'interval':
            trigger = IntervalTrigger(**trigger_args)
        case _:
            raise ValueError('Invalid trigger_mode')

    rescheduled_job = job.reschedule(trigger=trigger)
    return rescheduled_job


__all__ = [
    'reschedule_job',
]
