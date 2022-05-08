"""
@Author         : Ailitonia
@Date           : 2022/05/01 13:53
@FileName       : monitor.py
@Project        : nonebot2_miya
@Description    : Pixiv User Artwork Update Monitor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.log import logger
from omega_miya.utils.process_utils import run_async_catching_exception
from omega_miya.utils.apscheduler import scheduler

from .utils import send_pixivision_new_article


@run_async_catching_exception
async def pixivision_article_update_monitor() -> None:
    logger.debug('PixivisionArticleUpdateMonitor | Started checking pixivision article update')
    # 检查新特辑并发送消息
    await send_pixivision_new_article()
    logger.debug('PixivisionArticleUpdateMonitor | Pixivision update checking completed')


scheduler.add_job(
    pixivision_article_update_monitor,
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour=None,
    minute='*/9',
    # second='*/30',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='pixivision_article_update_monitor',
    coalesce=True,
    misfire_grace_time=120
)


__all__ = [
    'scheduler'
]
