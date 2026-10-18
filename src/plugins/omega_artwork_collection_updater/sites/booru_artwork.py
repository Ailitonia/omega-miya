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

from nonebot.log import logger

from src.service.artwork_proxy import (
    DanbooruArtworkProxy,
    KonachanSafeArtworkProxy,
    YandereArtworkProxy,
)

if TYPE_CHECKING:
    from src.service.artwork_proxy.internal import BaseArtworkProxy


class BooruArtworksUpdater:
    """自动更新较高评价的 booru 系图站作品

    Tips:
        danbooru 图比较杂, 使用 score:>600 筛选还算可以的作品
        gelbooru 平均水平惨不忍睹, 没有通用的搜索条件, 略
        konachan 和 yandere 的图整体较好, 但请求限制相对较严
    """

    @staticmethod
    async def _add_artwork_into_database(
            ap_cls: type['BaseArtworkProxy'],
            artwork_ids: Sequence[str],
    ) -> None:
        for artwork_id in artwork_ids:
            try:
                artwork = ap_cls(artwork_id)
                await artwork.add_artwork_into_database_ignore_exists()
            except Exception as e:
                logger.error(
                    f'ArtworkCollectionUpdater | Add {ap_cls.__name__}({artwork_id}) into database failed, {e}'
                )

    @classmethod
    async def update_danbooru_high_score_sfw_artworks(cls) -> None:
        random_result = await DanbooruArtworkProxy.search('status:active is:sfw score:>600 order:random limit:20')
        top_result = await DanbooruArtworkProxy.search('status:active is:sfw score:>500 limit:20',
                                                       page=random.randint(1, 10))
        await cls._add_artwork_into_database(
            DanbooruArtworkProxy,
            list(dict.fromkeys(x.s_aid for x in (random_result + top_result))),
        )

    @classmethod
    async def update_konachan_high_score_artworks(cls) -> None:
        random_result = await KonachanSafeArtworkProxy.search('score:>150 order:random')
        top_result = await KonachanSafeArtworkProxy.search('score:>100', page=random.randint(1, 100))
        await cls._add_artwork_into_database(
            KonachanSafeArtworkProxy,
            list(dict.fromkeys(x.s_aid for x in (random_result + top_result))),
        )

    @classmethod
    async def update_yandere_high_score_artworks(cls) -> None:
        random_result = await YandereArtworkProxy.search('score:>50 id:>50000 order:random')
        top_result = await YandereArtworkProxy.search('score:>25', page=random.randint(1, 100))
        await cls._add_artwork_into_database(
            YandereArtworkProxy,
            list(dict.fromkeys(x.s_aid for x in (random_result + top_result))),
        )


__all__ = [
    'BooruArtworksUpdater',
]
