"""
@Author         : Ailitonia
@Date           : 2021/08/27 0:48
@FileName       : utils.py
@Project        : nonebot2_miya 
@Description    : 签到插件定时任务
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Any, Callable, Coroutine

from nonebot.log import logger

from src.service import scheduler
from src.service.artwork_collection import PixivArtworkCollection
from src.utils.process_utils import semaphore_gather
from .config import sign_in_config

if TYPE_CHECKING:
    from src.service.artwork_collection.typing import ArtworkCollection_T


def _generate_collection_signin_image_preparing_handler(
        collection: "ArtworkCollection_T"
) -> Callable[[], Coroutine[Any, Any, None]]:
    """预缓存签到头图资源"""

    async def _collection_signin_image_preparing_handler() -> None:
        logger.debug(f'SignIn Utils | Started preparing {collection.__class__.__name__} sign in image')
        # 获取图片信息并下载图片
        random_artworks = await collection.random(num=100, ratio=1)

        tasks = [collection(artwork.aid).artwork_proxy.get_page_file() for artwork in random_artworks]
        await semaphore_gather(tasks=tasks, semaphore_num=20)

        logger.info(f'SignIn Utils | Preparing {collection.__class__.__name__} sign in image completed')

    return _collection_signin_image_preparing_handler


if sign_in_config.signin_plugin_enable_pixiv_preparing_scheduler:
    """下载签到图片的定时任务"""
    scheduler.add_job(
        _generate_collection_signin_image_preparing_handler(collection=PixivArtworkCollection),
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
