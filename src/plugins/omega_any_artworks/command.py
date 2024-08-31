"""
@Author         : Ailitonia
@Date           : 2024/8/31 上午3:23
@FileName       : command
@Project        : omega-miya
@Description    : 注册图站相关命令
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from src.service.artwork_proxy import (
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanSafeArtworkProxy,
    YandereArtworkProxy,
    PixivArtworkProxy,
)
from .handlers import ArtworkHandlerManager

__ARTWORK_PROXY_LIST = [
    DanbooruArtworkProxy,
    GelbooruArtworkProxy,
    KonachanSafeArtworkProxy,
    YandereArtworkProxy,
    PixivArtworkProxy,
]

for artwork_proxy_type in __ARTWORK_PROXY_LIST:
    ArtworkHandlerManager(artwork_class=artwork_proxy_type).register_handler()

__all__ = []
