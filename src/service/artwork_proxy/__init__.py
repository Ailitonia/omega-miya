"""
@Author         : Ailitonia
@Date           : 2024/8/4 下午5:32
@FileName       : artwork_proxy
@Project        : nonebot2_miya
@Description    : 图站 API 及本地图片缓存统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Literal, Optional

from .sites import (
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    LocalCollectedArtworkProxy,
    BehoimiArtworkProxy,
    KonachanArtworkProxy,
    KonachanSafeArtworkProxy,
    YandereArtworkProxy,
    NoneArtworkProxy,
    PixivArtworkProxy,
)

if TYPE_CHECKING:
    from .typing import ArtworkProxyType

type ALLOW_ARTWORK_ORIGIN = Literal[
    "pixiv",
    "danbooru",
    "gelbooru",
    "behoimi",
    "konachan",
    "konachan_safe",
    "yandere",
    "local",
    "none",
]


def get_artwork_proxy(origin: Optional[ALLOW_ARTWORK_ORIGIN] = None) -> "ArtworkProxyType":
    match origin:
        case 'pixiv':
            return PixivArtworkProxy
        case 'danbooru':
            return DanbooruArtworkProxy
        case 'gelbooru':
            return GelbooruArtworkProxy
        case 'behoimi':
            return BehoimiArtworkProxy
        case 'konachan':
            return KonachanArtworkProxy
        case 'konachan_safe':
            return KonachanSafeArtworkProxy
        case 'yandere':
            return YandereArtworkProxy
        case 'local':
            return LocalCollectedArtworkProxy
        case 'none' | _:
            return NoneArtworkProxy


__all__ = [
    'ALLOW_ARTWORK_ORIGIN',
    'DanbooruArtworkProxy',
    'GelbooruArtworkProxy',
    'LocalCollectedArtworkProxy',
    'BehoimiArtworkProxy',
    'KonachanArtworkProxy',
    'KonachanSafeArtworkProxy',
    'YandereArtworkProxy',
    'NoneArtworkProxy',
    'PixivArtworkProxy',
    'get_artwork_proxy',
]
