"""
@Author         : Ailitonia
@Date           : 2024/8/6 17:28:37
@FileName       : pixiv.py
@Project        : omega-miya
@Description    : Pixiv 适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.service.artwork_proxy import PixivArtworkProxy
from ..internal import BaseArtworkCollection


class PixivArtworkCollection(BaseArtworkCollection):
    """Pixiv 收藏作品合集"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> type[PixivArtworkProxy]:
        return PixivArtworkProxy


__all__ = [
    'PixivArtworkCollection'
]
