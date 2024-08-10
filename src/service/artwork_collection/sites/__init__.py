"""
@Author         : Ailitonia
@Date           : 2024/8/6 17:28:06
@FileName       : sites.py
@Project        : omega-miya
@Description    : 图库适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .danbooru import DanbooruArtworkCollection
from .pixiv import PixivArtworkCollection


__all__ = [
    'DanbooruArtworkCollection',
    'PixivArtworkCollection',
]
