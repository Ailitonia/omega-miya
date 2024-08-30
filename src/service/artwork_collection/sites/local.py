"""
@Author         : Ailitonia
@Date           : 2024/8/12 下午11:21
@FileName       : local
@Project        : nonebot2_miya
@Description    : 本地图片适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from src.service.artwork_proxy import LocalCollectedArtworkProxy
from ..internal import BaseArtworkCollection

if TYPE_CHECKING:
    from src.service.artwork_proxy.typing import ArtworkProxyType


class LocalCollectedArtworkCollection(BaseArtworkCollection):
    """本地图片收藏作品合集"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> "ArtworkProxyType":
        return LocalCollectedArtworkProxy


__all__ = [
    'LocalCollectedArtworkCollection',
]
