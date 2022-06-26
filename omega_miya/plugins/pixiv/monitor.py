"""
@Author         : Ailitonia
@Date           : 2022/04/29 18:41
@FileName       : monitor.py
@Project        : nonebot2_miya 
@Description    : Pixiv User Artwork Update Monitor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.log import logger
from omega_miya.web_resource.pixiv import PixivUser
from omega_miya.utils.process_utils import run_async_catching_exception, semaphore_gather
from omega_miya.utils.apscheduler import scheduler

from .utils import query_all_pixiv_user_subscription_source, send_pixiv_user_new_artworks


@run_async_catching_exception
async def pixiv_user_artwork_update_monitor() -> None:
    """Pixiv 用户订阅 作品更新监控"""
    logger.debug('PixivUserSubscriptionMonitor | Started checking pixiv user artworks update')

    # 获取所有已添加的 Pixiv 用户订阅源
    subscribed_uid = await query_all_pixiv_user_subscription_source()
    if not subscribed_uid:
        logger.debug('PixivUserSubscriptionMonitor | No pixiv user subscription, ignore')
        return

    # 检查新作品并发送消息
    tasks = [send_pixiv_user_new_artworks(PixivUser(uid=uid)) for uid in subscribed_uid]
    await semaphore_gather(tasks=tasks, semaphore_num=3, return_exceptions=True)

    logger.debug('PixivUserSubscriptionMonitor | Pixiv user artworks update checking completed')


scheduler.add_job(
    pixiv_user_artwork_update_monitor,
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour=None,
    minute='*/5',
    # second='*/30',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='pixiv_user_artwork_update_monitor',
    coalesce=True,
    misfire_grace_time=120
)


__all__ = [
    'scheduler'
]
