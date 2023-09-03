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

from src.service import scheduler

from .helpers import pixivision_monitor_main


async def pixivision_article_monitor() -> None:
    logger.debug(f'PixivisionArticleMonitor | Start checking new pixivision articles')

    # 检查新特辑并发送消息
    try:
        await pixivision_monitor_main()
    except Exception as e:
        logger.error(f'PixivisionArticleMonitor | Processing pixivision article updating failed, {e!r}')

    logger.debug('PixivisionArticleMonitor | Pixivision article update checking completed')


scheduler.add_job(
    pixivision_article_monitor,
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour=None,
    minute='*/20',
    second='17',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='pixivision_article_monitor',
    coalesce=True,
    misfire_grace_time=120
)


__all__ = [
    'scheduler'
]
