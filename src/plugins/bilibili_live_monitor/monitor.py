"""
@Author         : Ailitonia
@Date           : 2022/05/03 19:41
@FileName       : monitor.py
@Project        : nonebot2_miya 
@Description    : Bilibili Live monitor
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.log import logger

from src.service import scheduler

from .helpers import bili_live_room_monitor_main


async def bili_live_room_update_monitor() -> None:
    """Bilibili 直播间订阅 直播间更新监控"""
    logger.debug('BilibiliLiveRoomSubscriptionMonitor | Started checking bilibili live room update')

    # 检查直播间更新并通知已订阅的用户或群组
    try:
        await bili_live_room_monitor_main()
        logger.debug('BilibiliLiveRoomSubscriptionMonitor | Bilibili user live room update checking completed')
    except Exception as e:
        logger.error(f'BilibiliLiveRoomSubscriptionMonitor | Bilibili user live room update checking failed, {e!r}')


scheduler.add_job(
    bili_live_room_update_monitor,
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour=None,
    # minute='*/1',
    second='*/30',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='bili_live_room_update_monitor',
    coalesce=True,
    misfire_grace_time=20
)


__all__ = [
    'scheduler'
]
