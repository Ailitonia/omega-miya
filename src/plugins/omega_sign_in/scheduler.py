"""
@Author         : Ailitonia
@Date           : 2021/08/27 0:48
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 签到插件定时任务
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.log import logger

from src.service import scheduler
from src.service.artwork_collection import PixivArtworkCollection
from src.utils.pixiv_api import PixivArtwork
from src.utils.process_utils import semaphore_gather
from .config import sign_in_config


async def _prepare_signin_image() -> None:
    """预缓存签到头图资源, 使用 Pixiv 图库内容"""
    logger.debug(f'SignIn Utils | Started preparing sign in image')
    # 获取图片信息并下载图片
    random_artworks = await PixivArtworkCollection.random(num=100, nsfw_tag=0, ratio=1)

    tasks = [PixivArtwork(pid=artwork.pid).get_page_file() for artwork in random_artworks]
    pre_download_result = await semaphore_gather(tasks=tasks, semaphore_num=20)

    success_count = 0
    failed_count = 0
    for result in pre_download_result:
        if isinstance(result, Exception):
            failed_count += 1
        else:
            success_count += 1
    logger.info(f'SignIn Utils | Preparing sign in image completed with {success_count} success, {failed_count} failed')


if sign_in_config.signin_enable_preparing_scheduler:
    """下载签到图片的定时任务"""
    scheduler.add_job(
        _prepare_signin_image,
        'cron',
        # year=None,
        # month=None,
        # day='*/1',
        # week=None,
        # day_of_week=None,
        hour='*/3',
        minute=7,
        second=13,
        # start_date=None,
        # end_date=None,
        # timezone=None,
        id='prepare_signin_image',
        coalesce=True,
        misfire_grace_time=120
    )


__all__ = [
    'scheduler'
]
