"""
@Author         : Ailitonia
@Date           : 2024/8/10 下午2:05
@FileName       : danbooru
@Project        : nonebot2_miya
@Description    : booru 系列适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from src.service.artwork_proxy import (
    BehoimiArtworkProxy,
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanArtworkProxy,
    KonachanSafeArtworkProxy,
    YandereArtworkProxy,
)
from ..internal import BaseArtworkCollection

if TYPE_CHECKING:
    from src.service.artwork_proxy.typing import ArtworkProxyType


class DanbooruArtworkCollection(BaseArtworkCollection):
    """Danbooru 收藏作品合集"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> 'ArtworkProxyType':
        return DanbooruArtworkProxy


class GelbooruArtworkCollection(BaseArtworkCollection):
    """Gelbooru 收藏作品合集"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> 'ArtworkProxyType':
        return GelbooruArtworkProxy


class BehoimiArtworkCollection(BaseArtworkCollection):
    """Behoimi 收藏作品合集"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> 'ArtworkProxyType':
        return BehoimiArtworkProxy


class KonachanArtworkCollection(BaseArtworkCollection):
    """Konachan 收藏作品合集"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> 'ArtworkProxyType':
        return KonachanArtworkProxy


class KonachanSafeArtworkCollection(BaseArtworkCollection):
    """KonachanSafe 收藏作品合集"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> 'ArtworkProxyType':
        return KonachanSafeArtworkProxy


class YandereArtworkCollection(BaseArtworkCollection):
    """Yandere 收藏作品合集"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> 'ArtworkProxyType':
        return YandereArtworkProxy


__all__ = [
    'DanbooruArtworkCollection',
    'GelbooruArtworkCollection',
    'BehoimiArtworkCollection',
    'KonachanArtworkCollection',
    'KonachanSafeArtworkCollection',
    'YandereArtworkCollection',
]
