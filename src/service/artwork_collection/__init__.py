"""
@Author         : Ailitonia
@Date           : 2024/6/11 上午1:52
@FileName       : artwork_collection
@Project        : nonebot2_miya
@Description    : 收藏的图片、漫画等作品合集, 数据库统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Literal, overload

from src.service.artwork_proxy import ALLOW_ARTWORK_ORIGIN
from .sites import (
    BehoimiArtworkCollection,
    DanbooruArtworkCollection,
    GelbooruArtworkCollection,
    KonachanArtworkCollection,
    KonachanSafeArtworkCollection,
    LocalCollectedArtworkCollection,
    NoneArtworkCollection,
    PixivArtworkCollection,
    YandereArtworkCollection,
)

if TYPE_CHECKING:
    from src.database.internal.artwork_collection import ArtworkCollection as DBArtworkCollection

    from .typing import ArtworkCollectionType, CollectedArtwork


@overload
def get_artwork_collection_type(origin: Literal['pixiv']) -> type[PixivArtworkCollection]:
    ...


@overload
def get_artwork_collection_type(origin: Literal['danbooru']) -> type[DanbooruArtworkCollection]:
    ...


@overload
def get_artwork_collection_type(origin: Literal['gelbooru']) -> type[GelbooruArtworkCollection]:
    ...


@overload
def get_artwork_collection_type(origin: Literal['behoimi']) -> type[BehoimiArtworkCollection]:
    ...


@overload
def get_artwork_collection_type(origin: Literal['konachan']) -> type[KonachanArtworkCollection]:
    ...


@overload
def get_artwork_collection_type(origin: Literal['yandere']) -> type[YandereArtworkCollection]:
    ...


@overload
def get_artwork_collection_type(origin: Literal['local_collected_artwork']) -> type[LocalCollectedArtworkCollection]:
    ...


@overload
def get_artwork_collection_type(origin: Literal['none', None] = None) -> type[NoneArtworkCollection]:
    ...


def get_artwork_collection_type(origin: ALLOW_ARTWORK_ORIGIN | None = None) -> 'ArtworkCollectionType':
    """根据 origin 名称获取 ArtworkCollection 类"""
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
            return KonachanSafeArtworkCollection
        case 'yandere':
            return YandereArtworkCollection
        case 'local_collected_artwork':
            return LocalCollectedArtworkCollection
        case 'none' | _:
            return NoneArtworkCollection


def get_artwork_collection(artwork: 'DBArtworkCollection') -> 'CollectedArtwork':
    """根据数据库查询 ArtworkCollection 结果获取对应的 ArtworkCollection 实例"""
    artwork_collection_type = get_artwork_collection_type(origin=artwork.origin)  # type: ignore
    return artwork_collection_type(artwork_id=artwork.aid)


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
    'get_artwork_collection_type',
]
