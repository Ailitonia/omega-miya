"""
@Author         : Ailitonia
@Date           : 2024/8/24 下午5:24
@FileName       : pixiv
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from asyncio import sleep as async_sleep
from typing import Sequence

from src.service.artwork_collection import PixivArtworkCollection
from src.utils import semaphore_gather
from src.utils.pixiv_api import PixivArtwork


class PixivArtworkUpdater(object):
    """自动从 Pixiv 发现/推荐更新作品"""

    @staticmethod
    async def _add_artwork_into_database(pids: Sequence[int], semaphore_num: int = 8) -> None:
        tasks = [PixivArtworkCollection(x).add_artwork_into_database_ignore_exists() for x in pids]
        await semaphore_gather(tasks=tasks, semaphore_num=semaphore_num, return_exceptions=False)

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
