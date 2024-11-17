"""
@Author         : Ailitonia
@Date           : 2024/8/12 下午11:17
@FileName       : none
@Project        : nonebot2_miya
@Description    : none
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from src.service.artwork_proxy import NoneArtworkProxy
from ..internal import BaseArtworkCollection

if TYPE_CHECKING:
    from src.service.artwork_proxy.typing import ArtworkProxyType


class NoneArtworkCollection(BaseArtworkCollection):
    """空适配"""

    @classmethod
    def _get_base_artwork_proxy_type(cls) -> 'ArtworkProxyType':
        return NoneArtworkProxy


__all__ = [
    'NoneArtworkCollection',
]
