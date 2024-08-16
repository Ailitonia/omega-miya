"""
@Author         : Ailitonia
@Date           : 2024/6/11 上午1:52
@FileName       : artwork_collection
@Project        : nonebot2_miya
@Description    : 收藏的图片、漫画等作品合集, 数据库统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Optional

from src.service.artwork_proxy import ALLOW_ARTWORK_ORIGIN
from .sites import (
    DanbooruArtworkCollection,
    GelbooruArtworkCollection,
    BehoimiArtworkCollection,
    KonachanArtworkCollection,
    KonachanSafeArtworkCollection,
    YandereArtworkCollection,
    LocalCollectedArtworkCollection,
    NoneArtworkCollection,
    PixivArtworkCollection,
)

if TYPE_CHECKING:
    from .typing import ArtworkCollectionType


def get_artwork_collection(origin: Optional[ALLOW_ARTWORK_ORIGIN] = None) -> "ArtworkCollectionType":
    match origin:
        case 'pixiv':
            return PixivArtworkCollection
        case 'danbooru':
            return DanbooruArtworkCollection
        case 'gelbooru':
            return GelbooruArtworkCollection
        case 'behoimi':
            return BehoimiArtworkCollection
        case 'konachan':
            return KonachanArtworkCollection
        case 'konachan_safe':
            return KonachanSafeArtworkCollection
        case 'yandere':
            return YandereArtworkCollection
        case 'local':
            return LocalCollectedArtworkCollection
        case 'none' | _:
            return NoneArtworkCollection


__all__ = [
    'ALLOW_ARTWORK_ORIGIN',
    'DanbooruArtworkCollection',
    'GelbooruArtworkCollection',
    'BehoimiArtworkCollection',
    'KonachanArtworkCollection',
    'KonachanSafeArtworkCollection',
    'YandereArtworkCollection',
    'LocalCollectedArtworkCollection',
    'NoneArtworkCollection',
    'PixivArtworkCollection',
    'get_artwork_collection',
]
