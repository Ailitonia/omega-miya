"""
@Author         : Ailitonia
@Date           : 2022/05/02 23:50
@FileName       : monitor.py
@Project        : nonebot2_miya 
@Description    : Bilibili Dynamic monitor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from asyncio import Queue as AsyncQueue
from datetime import datetime, timedelta

from nonebot.log import logger

from src.exception import PluginException, WebSourceException
from src.service import scheduler
from src.utils import semaphore_gather
from .consts import AVERAGE_CHECKING_PER_MINUTE, CHECKING_DELAY_UNDER_RATE_LIMITING, MONITOR_JOB_ID
from .helpers import bili_dynamic_monitor_main, query_all_subscribed_dynamic_sub_source

_UID_CHECKING_QUEUE: AsyncQueue[int] = AsyncQueue()
"""用于动态更新监控使用的已订阅用户 UID 队列"""


class NullBiliDynamicSubscribedSource(PluginException):
    """当前没有任何已订阅的 bilibili 用户动态订阅源"""


async def _reload_uid_queue() -> None:
    """重新填充动态已订阅用户 UID 待检查队列"""
    subscribed_uid = await query_all_subscribed_dynamic_sub_source()
    if not subscribed_uid:
        logger.debug('BilibiliDynamicMonitor | Null of bilibili dynamic subscription source, ignored')
        raise NullBiliDynamicSubscribedSource

    for uid in subscribed_uid:
        await _UID_CHECKING_QUEUE.put(uid)

    logger.debug(
        f'BilibiliDynamicMonitor | Reloaded UID queue with {subscribed_uid}, remaining: {_UID_CHECKING_QUEUE.qsize()}'
    )


async def _get_next_check_uid(num: int) -> list[int]:
    """从待检查队列中获取接下来检查的用户 UID"""
    logger.debug(f'BilibiliDynamicMonitor | UID queue remaining: {_UID_CHECKING_QUEUE.qsize()}')
    if _UID_CHECKING_QUEUE.empty():
        await _reload_uid_queue()

    return [await _UID_CHECKING_QUEUE.get() for _ in range(min(num, _UID_CHECKING_QUEUE.qsize()))]


async def bili_dynamic_update_monitor() -> None:
    """Bilibili 用户动态订阅 动态更新监控"""
    logger.debug('BilibiliDynamicMonitor | Started checking bilibili user dynamics update from queue')

    try:
        subscribed_uid = await _get_next_check_uid(num=AVERAGE_CHECKING_PER_MINUTE)
        [_UID_CHECKING_QUEUE.task_done() for _ in range(len(subscribed_uid))]
    except NullBiliDynamicSubscribedSource:
        return

    # 检查新作品并发送消息
    tasks = [bili_dynamic_monitor_main(user_id=uid) for uid in subscribed_uid]
    sent_result = await semaphore_gather(tasks=tasks, semaphore_num=AVERAGE_CHECKING_PER_MINUTE)
    if any(isinstance(e, WebSourceException) for e in sent_result):
        # 如果 API 异常则大概率被风控, 推迟下一次检查
        monitor_job = scheduler.get_job(job_id=MONITOR_JOB_ID)
        if monitor_job is not None:
            monitor_job.modify(next_run_time=(datetime.now() + timedelta(minutes=CHECKING_DELAY_UNDER_RATE_LIMITING)))
            logger.warning(
                'BilibiliDynamicMonitor | Fetch bilibili dynamic data failed, maybe under the rate limiting, '
                f'delay the next checking until after {CHECKING_DELAY_UNDER_RATE_LIMITING} minutes, {monitor_job}'
            )

    logger.debug('BilibiliDynamicMonitor | Bilibili user dynamic update checking completed')


scheduler.add_job(
    bili_dynamic_update_monitor,
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour=None,
    minute='*/1',
    # second='*/50',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id=MONITOR_JOB_ID,
    coalesce=True,
    misfire_grace_time=120
)


__all__ = [
    'scheduler',
]
