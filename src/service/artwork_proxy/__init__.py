"""
@Author         : Ailitonia
@Date           : 2024/8/4 下午5:32
@FileName       : artwork_proxy
@Project        : nonebot2_miya
@Description    : 图站 API 及本地图片缓存统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .internal import BaseArtworkProxy

from .sites import (
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanArtworkProxy,
    KonachanSafeArtworkProxy,
    LocalCollectedArtworkProxy,
    NoneArtworkProxy,
    PixivArtworkProxy,
    YandereArtworkProxy,
)

AVAILABLE_ARTWORK_PROXY: dict[str, type['BaseArtworkProxy']] = {
    x.get_origin_name(): x
    for x in [
        DanbooruArtworkProxy,
        GelbooruArtworkProxy,
        KonachanArtworkProxy,
        KonachanSafeArtworkProxy,
        LocalCollectedArtworkProxy,
        NoneArtworkProxy,
        PixivArtworkProxy,
        YandereArtworkProxy,
    ]
}
"""所有可用的 ArtworkProxy"""


def get_artwork_proxy(origin_name: str) -> type['BaseArtworkProxy'] | None:
    """根据 origin_name 获取对应图站的 ArtworkProxy 类"""
    return AVAILABLE_ARTWORK_PROXY.get(origin_name, None)


__all__ = [
    'AVAILABLE_ARTWORK_PROXY',
    'DanbooruArtworkProxy',
    'GelbooruArtworkProxy',
    'KonachanArtworkProxy',
    'KonachanSafeArtworkProxy',
    'LocalCollectedArtworkProxy',
    'NoneArtworkProxy',
    'PixivArtworkProxy',
    'YandereArtworkProxy',
    'get_artwork_proxy',
]
