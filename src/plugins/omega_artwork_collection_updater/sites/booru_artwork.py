"""
@Author         : Ailitonia
@Date           : 2024/8/24 上午12:55
@FileName       : booru_artwork
@Project        : nonebot2_miya
@Description    : booru 系图站自动更新工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from collections.abc import Sequence
from typing import TYPE_CHECKING

from src.service.artwork_collection import (
    DanbooruArtworkCollection,
    KonachanSafeArtworkCollection,
    YandereArtworkCollection,
)
from src.service.artwork_proxy import (
    DanbooruArtworkProxy,
    KonachanSafeArtworkProxy,
    YandereArtworkProxy,
)
from src.utils import semaphore_gather

if TYPE_CHECKING:
    from src.service.artwork_collection.typing import ArtworkCollectionType
    from src.service.artwork_proxy.typing import ProxiedArtwork


class BooruArtworksUpdater:
    """自动更新较高评价的 booru 系图站作品

    Tips:
        danbooru 图比较杂, 使用 score:>600 筛选还算可以的作品
        gelbooru 平均水平惨不忍睹, 没有通用的搜索条件, 略
        konachan 和 yandere 的图整体较好, 但请求限制相对较严
    """

    @staticmethod
    async def _add_artwork_into_database(
            ac_t: 'ArtworkCollectionType',
            artworks: Sequence['ProxiedArtwork'],
            semaphore_num: int = 4,
    ) -> None:
        tasks = [ac_t(x.s_aid).add_artwork_into_database_ignore_exists() for x in artworks]
        await semaphore_gather(tasks=tasks, semaphore_num=semaphore_num, return_exceptions=False)

    @classmethod
    async def update_danbooru_high_score_sfw_artworks(cls) -> None:
        random_result = await DanbooruArtworkProxy.search('status:active is:sfw score:>600 order:random limit:20')
        top_result = await DanbooruArtworkProxy.search('status:active is:sfw score:>500 limit:20',
                                                       page=random.randint(1, 10))
        await cls._add_artwork_into_database(DanbooruArtworkCollection, random_result + top_result)

    @classmethod
    async def update_konachan_high_score_artworks(cls) -> None:
        random_result = await KonachanSafeArtworkProxy.search('score:>150 order:random')
        top_result = await KonachanSafeArtworkProxy.search('score:>100', page=random.randint(1, 100))
        await cls._add_artwork_into_database(KonachanSafeArtworkCollection, random_result + top_result, semaphore_num=2)

    @classmethod
    async def update_yandere_high_score_artworks(cls) -> None:
        random_result = await YandereArtworkProxy.search('score:>50 id:>50000 order:random')
        top_result = await YandereArtworkProxy.search('score:>25', page=random.randint(1, 100))
        await cls._add_artwork_into_database(YandereArtworkCollection, random_result + top_result)


__all__ = [
    'BooruArtworksUpdater',
]
