"""
@Author         : Ailitonia
@Date           : 2024/8/6 17:28:06
@FileName       : sites.py
@Project        : omega-miya
@Description    : 图库适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .booru import (
    BehoimiArtworkCollection,
    DanbooruArtworkCollection,
    GelbooruArtworkCollection,
    KonachanArtworkCollection,
    KonachanSafeArtworkCollection,
    YandereArtworkCollection,
)
from .local import LocalCollectedArtworkCollection
from .none import NoneArtworkCollection
from .pixiv import PixivArtworkCollection

__all__ = [
    'DanbooruArtworkCollection',
    'GelbooruArtworkCollection',
    'BehoimiArtworkCollection',
    'KonachanArtworkCollection',
    'KonachanSafeArtworkCollection',
    'YandereArtworkCollection',
    'LocalCollectedArtworkCollection',
    'NoneArtworkCollection',
    'PixivArtworkCollection',
]
