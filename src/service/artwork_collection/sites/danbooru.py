"""
@Author         : Ailitonia
@Date           : 2024/8/10 下午2:05
@FileName       : danbooru
@Project        : nonebot2_miya
@Description    : Danbooru 适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from src.service.artwork_proxy import DanbooruArtworkProxy
from ..internal import BaseArtworkCollection

if TYPE_CHECKING:
    from src.service.artwork_proxy.typing import ArtworkProxyType


class DanbooruArtworkCollection(BaseArtworkCollection):
    """Danbooru 收藏作品合集"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> "ArtworkProxyType":
        return DanbooruArtworkProxy


__all__ = [
    'DanbooruArtworkCollection',
]