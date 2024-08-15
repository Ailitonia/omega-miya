"""
@Author         : Ailitonia
@Date           : 2024/8/8 16:38:37
@FileName       : models.py
@Project        : omega-miya
@Description    : Add-ons models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc

from ..typing import mark_as_artwork_proxy_mixin


@mark_as_artwork_proxy_mixin
class ArtworkProxyAddonsMixin(abc.ABC):
    """Artwork Proxy 附加工具 Mixin 基类"""


___all__ = [
    'ArtworkProxyAddonsMixin',
]
