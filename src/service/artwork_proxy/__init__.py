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
    BilibiliDynamicPicArtworkProxy,
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanArtworkProxy,
    KonachanSafeArtworkProxy,
    LocalCollectedArtworkProxy,
    NoneArtworkProxy,
    PixivArtworkProxy,
    TweetPicArtworkProxy,
    YandereArtworkProxy,
)

_AVAILABLE_ARTWORK_PROXY: dict[str, type['BaseArtworkProxy']] = {
    x.get_origin_name(): x
    for x in [
        BilibiliDynamicPicArtworkProxy,
        DanbooruArtworkProxy,
        GelbooruArtworkProxy,
        KonachanArtworkProxy,
        KonachanSafeArtworkProxy,
        LocalCollectedArtworkProxy,
        NoneArtworkProxy,
        PixivArtworkProxy,
        TweetPicArtworkProxy,
        YandereArtworkProxy,
    ]
}
"""所有可用的 ArtworkProxy"""


def get_available_artwork_proxy_origin_name() -> list[str]:
    """获取所有可用的 ArtworkProxy origin_name 列表"""
    return list(_AVAILABLE_ARTWORK_PROXY.keys())


def get_artwork_proxy(origin_name: str) -> type['BaseArtworkProxy']:
    """根据 origin_name 获取对应图站的 ArtworkProxy 类, 不存在的话抛出 KeyError 异常"""
    return _AVAILABLE_ARTWORK_PROXY[origin_name]


__all__ = [
    'BilibiliDynamicPicArtworkProxy',
    'DanbooruArtworkProxy',
    'GelbooruArtworkProxy',
    'KonachanArtworkProxy',
    'KonachanSafeArtworkProxy',
    'LocalCollectedArtworkProxy',
    'NoneArtworkProxy',
    'PixivArtworkProxy',
    'TweetPicArtworkProxy',
    'YandereArtworkProxy',
    'get_artwork_proxy',
    'get_available_artwork_proxy_origin_name',
]
