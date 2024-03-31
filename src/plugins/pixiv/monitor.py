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

from src.service import scheduler
from src.utils.pixiv_api import PixivUser
from src.utils.process_utils import semaphore_gather

from .helpers import query_all_subscribed_pixiv_user_sub_source, pixiv_user_new_artworks_monitor_main


async def pixiv_user_new_artworks_monitor() -> None:
    """Pixiv 用户订阅 作品更新监控"""
    logger.debug('PixivUserSubscriptionMonitor | Started checking pixiv user artworks update')

    # 获取所有已添加的 Pixiv 用户订阅源
    subscribed_uid = await query_all_subscribed_pixiv_user_sub_source()
    if not subscribed_uid:
        logger.debug('PixivUserSubscriptionMonitor | No pixiv user subscription, ignore')
        return

    # 检查新作品并发送消息
    tasks = [pixiv_user_new_artworks_monitor_main(pixiv_user=PixivUser(uid=uid)) for uid in subscribed_uid]
    await semaphore_gather(tasks=tasks, semaphore_num=3, return_exceptions=True)

    logger.debug('PixivUserSubscriptionMonitor | Pixiv user artworks update checking completed')


scheduler.add_job(
    pixiv_user_new_artworks_monitor,
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour=None,
    minute='*/5',
    second='47',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='pixiv_user_new_artworks_monitor',
    coalesce=True,
    misfire_grace_time=120
)


__all__ = [
    'scheduler'
]
