"""
@Author         : Ailitonia
@Date           : 2024/8/24 下午5:24
@FileName       : pixiv
@Project        : nonebot2_miya
@Description    : Pixiv 首页及推荐作品更新
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from asyncio import sleep as async_sleep
from collections.abc import Sequence

from nonebot.log import logger

from src.service.artwork_proxy import PixivArtworkProxy
from src.utils.pixiv_api import PixivArtwork


class PixivArtworkUpdater:
    """自动从 Pixiv 发现/推荐更新作品"""

    @staticmethod
    async def _add_artwork_into_database(pids: Sequence[str | int]) -> None:
        for artwork_id in pids:
            artwork = PixivArtworkProxy(artwork_id)
            try:
                await artwork.add_artwork_into_database_ignore_exists()
            except Exception as e:
                logger.error(f'ArtworkCollectionUpdater | Add {artwork} into database failed, {e}')
            finally:
                await async_sleep(2)

    @classmethod
    async def update_random_discovery_artworks(cls) -> None:
        discovery_artworks_data = await PixivArtwork.query_discovery_artworks(mode='all', limit=20)
        await cls._add_artwork_into_database(pids=discovery_artworks_data.recommend_pids)

    @classmethod
    async def update_random_top_artworks(cls) -> None:
        top_artworks_data = await PixivArtwork.query_top_illust()
        await cls._add_artwork_into_database(pids=top_artworks_data.recommend_pids)

    @classmethod
    async def update_recommend_artworks(cls) -> None:
        await cls.update_random_discovery_artworks()
        await async_sleep(30)
        await cls.update_random_top_artworks()


__all__ = [
    'PixivArtworkUpdater',
]
