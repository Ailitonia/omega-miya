"""
@Author         : Ailitonia
@Date           : 2022/05/02 23:50
@FileName       : monitor.py
@Project        : nonebot2_miya 
@Description    : Bilibili Dynamic monitor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from nonebot.log import logger
from omega_miya.web_resource.bilibili import BilibiliUser
from omega_miya.utils.apscheduler import scheduler, reschedule_job
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather

from .utils import query_all_bili_user_dynamic_subscription_source, send_bili_user_new_dynamics


_MONITOR_JOB_ID: Literal['bili_user_dynamic_update_monitor'] = 'bili_user_dynamic_update_monitor'


@run_async_catching_exception
async def bili_user_dynamic_update_monitor() -> None:
    """Bilibili 用户动态订阅 作品更新监控"""
    logger.debug('BilibiliUserDynamicSubscriptionMonitor | Started checking bilibili user dynamics update')

    # 获取所有已添加的 Bilibili 用户动态订阅源
    subscribed_uid = await query_all_bili_user_dynamic_subscription_source()
    if not subscribed_uid:
        logger.debug('BilibiliUserDynamicSubscriptionMonitor | No bilibili user dynamic subscription, ignore')
        return

    # 避免风控, 根据订阅的用户数动态调整检查时间间隔
    monitor_job = scheduler.get_job(job_id=_MONITOR_JOB_ID)
    if monitor_job is not None:
        interval_min = len(subscribed_uid) // 10
        interval_min = interval_min if interval_min >= 2 else 2
        reschedule_job(job=monitor_job, trigger_mode='interval', minutes=interval_min)

    # 检查新作品并发送消息
    tasks = [send_bili_user_new_dynamics(BilibiliUser(uid=uid)) for uid in subscribed_uid]
    sent_result = await semaphore_gather(tasks=tasks, semaphore_num=5)
    if error := [x for x in sent_result if isinstance(x, Exception)]:
        raise RuntimeError(*error)

    logger.debug('BilibiliUserDynamicSubscriptionMonitor | Bilibili user dynamic update checking completed')


scheduler.add_job(
    bili_user_dynamic_update_monitor,
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
    id=_MONITOR_JOB_ID,
    coalesce=True,
    misfire_grace_time=120
)


__all__ = [
    'scheduler'
]
