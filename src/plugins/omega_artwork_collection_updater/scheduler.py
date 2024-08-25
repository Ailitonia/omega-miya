"""
@Author         : Ailitonia
@Date           : 2024/8/17 下午7:02
@FileName       : scheduler
@Project        : nonebot2_miya
@Description    : 更新任务管理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger

from src.service import scheduler
from .sites import (
    BooruArtworksUpdater,
    LocalCollectedArtworkUpdater,
    LoliconAPI,
    PixivArtworkUpdater,
)


@get_driver().on_startup
async def artwork_collection_updater_startup_task() -> None:
    logger.debug('OmegaArtworkCollectionUpdater | Starting update from LocalCollectedArtwork')
    try:
        await LocalCollectedArtworkUpdater.update_local_collected_artwork()
        logger.success('OmegaArtworkCollectionUpdater | Updated from LocalCollectedArtwork succeed')
    except Exception as e:
        logger.error(f'OmegaArtworkCollectionUpdater | Updating from LocalCollectedArtwork failed, {e!r}')


async def artwork_collection_updater_main() -> None:
    logger.debug('OmegaArtworkCollectionUpdater | Starting update from LoliconAPI')
    try:
        await LoliconAPI.update_lolicon_setu()
        logger.success('OmegaArtworkCollectionUpdater | Updated from LoliconAPI succeed')
    except Exception as e:
        logger.error(f'OmegaArtworkCollectionUpdater | Updating from LoliconAPI failed, {e!r}')

    logger.debug('OmegaArtworkCollectionUpdater | Starting update from Danbooru')
    try:
        await BooruArtworksUpdater.update_danbooru_high_score_sfw_artworks()
        logger.success('OmegaArtworkCollectionUpdater | Updated from Danbooru succeed')
    except Exception as e:
        logger.error(f'OmegaArtworkCollectionUpdater | Updating from Danbooru failed, {e!r}')

    logger.debug('OmegaArtworkCollectionUpdater | Starting update from Konachan')
    try:
        await BooruArtworksUpdater.update_konachan_high_score_artworks()
        logger.success('OmegaArtworkCollectionUpdater | Updated from Konachan succeed')
    except Exception as e:
        logger.error(f'OmegaArtworkCollectionUpdater | Updating from Konachan failed, {e!r}')

    logger.debug('OmegaArtworkCollectionUpdater | Starting update from Yandere')
    try:
        await BooruArtworksUpdater.update_yandere_high_score_artworks()
        logger.success('OmegaArtworkCollectionUpdater | Updated from Yandere succeed')
    except Exception as e:
        logger.error(f'OmegaArtworkCollectionUpdater | Updating from Yandere failed, {e!r}')

    logger.debug('OmegaArtworkCollectionUpdater | Starting update from PixivRecommend')
    try:
        await PixivArtworkUpdater.update_recommend_artworks()
        logger.success('OmegaArtworkCollectionUpdater | Updated from PixivRecommend succeed')
    except Exception as e:
        logger.error(f'OmegaArtworkCollectionUpdater | Updating from PixivRecommend failed, {e!r}')


scheduler.add_job(
    artwork_collection_updater_main,
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    hour='1-7',  # 只在夜间执行自动更新
    minute='*/6',
    second='17',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='artwork_collection_updater',
    coalesce=True,
    misfire_grace_time=120
)

__all__ = [
    'scheduler',
]
