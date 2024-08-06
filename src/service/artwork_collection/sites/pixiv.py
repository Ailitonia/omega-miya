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

    @classmethod
    def _init_self_artwork_proxy(cls, artwork_id: str | int) -> PixivArtworkProxy:
        return PixivArtworkProxy(artwork_id=artwork_id)

    @classmethod
    def _get_base_origin_name(cls) -> str:
        return 'pixiv'


__all__ = [
    'PixivArtworkCollection'
]
