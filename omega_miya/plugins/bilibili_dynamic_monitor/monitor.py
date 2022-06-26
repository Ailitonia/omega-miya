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
from omega_miya.web_resource.bilibili.exception import BilibiliApiError
from omega_miya.utils.apscheduler import scheduler, reschedule_job
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather

from .utils import query_all_bili_user_dynamic_subscription_source, send_bili_user_new_dynamics


_MONITOR_JOB_ID: Literal['bili_user_dynamic_update_monitor'] = 'bili_user_dynamic_update_monitor'
"""动态检查的定时任务 ID"""
_AVERAGE_CHECKING_PER_MINUTE: float = 7.5
"""期望平均每分钟检查动态的用户数(数值大小影响风控概率, 请谨慎调整)"""
_CHECKING_DELAY_UNDER_RATE_LIMITING: int = 20
"""被风控时的延迟间隔"""


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
        interval_min = int(len(subscribed_uid) // _AVERAGE_CHECKING_PER_MINUTE)
        interval_min = interval_min if interval_min > 2 else 2
        reschedule_job(job=monitor_job, trigger_mode='interval', minutes=interval_min)

    # 检查新作品并发送消息
    tasks = [send_bili_user_new_dynamics(BilibiliUser(uid=uid)) for uid in subscribed_uid]
    sent_result = await semaphore_gather(tasks=tasks, semaphore_num=5, return_exceptions=True, filter_exception=False)
    if any(e for e in sent_result if isinstance(e, BilibiliApiError)):
        # 如果 API 异常则大概率被风控, 推迟下一次检查
        if monitor_job is not None:
            reschedule_job(job=monitor_job, trigger_mode='interval', minutes=_CHECKING_DELAY_UNDER_RATE_LIMITING)
        logger.warning('BilibiliUserDynamicSubscriptionMonitor | Fetch bilibili dynamic data failed, '
                       f'maybe under the rate limiting, '
                       f'delay the next checking until after {_CHECKING_DELAY_UNDER_RATE_LIMITING} minutes')

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
