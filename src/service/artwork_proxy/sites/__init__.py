"""
@Author         : Ailitonia
@Date           : 2024/8/5 下午10:37
@FileName       : site
@Project        : nonebot2_miya
@Description    : 图库适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .danbooru import DanbooruArtworkProxy
from .gelbooru import GelbooruArtworkProxy
from .local import LocalCollectedArtworkProxy
from .none import NoneArtworkProxy
from .pixiv import PixivArtworkProxy


__all__ = [
    'DanbooruArtworkProxy',
    'GelbooruArtworkProxy',
    'LocalCollectedArtworkProxy',
    'NoneArtworkProxy',
    'PixivArtworkProxy',
]
