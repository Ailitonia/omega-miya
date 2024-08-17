"""
@Author         : Ailitonia
@Date           : 2024/6/11 上午1:52
@FileName       : artwork_collection
@Project        : nonebot2_miya
@Description    : 收藏的图片、漫画等作品合集, 数据库统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Literal, Optional, overload

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


@overload
def get_artwork_collection(origin: Literal['pixiv']) -> type[PixivArtworkCollection]:
    ...


@overload
def get_artwork_collection(origin: Literal['danbooru']) -> type[DanbooruArtworkCollection]:
    ...


@overload
def get_artwork_collection(origin: Literal['gelbooru']) -> type[GelbooruArtworkCollection]:
    ...


@overload
def get_artwork_collection(origin: Literal['behoimi']) -> type[BehoimiArtworkCollection]:
    ...


@overload
def get_artwork_collection(origin: Literal['konachan']) -> type[KonachanArtworkCollection]:
    ...


@overload
def get_artwork_collection(origin: Literal['konachan_safe']) -> type[KonachanSafeArtworkCollection]:
    ...


@overload
def get_artwork_collection(origin: Literal['yandere']) -> type[YandereArtworkCollection]:
    ...


@overload
def get_artwork_collection(origin: Literal['local', 'local_collected_artwork']) -> type[LocalCollectedArtworkCollection]:
    ...


@overload
def get_artwork_collection(origin: Literal['none', None] = None) -> type[NoneArtworkCollection]:
    ...


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
        case 'local' | 'local_collected_artwork':
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
