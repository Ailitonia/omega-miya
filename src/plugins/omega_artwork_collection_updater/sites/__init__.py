"""
@Author         : Ailitonia
@Date           : 2024/8/17 下午7:00
@FileName       : sites
@Project        : nonebot2_miya
@Description    : 图站来源适配
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .booru_artwork import BooruArtworksUpdater
from .lolicon_api import LoliconAPI
from .pixiv import PixivArtworkUpdater

__all__ = [
    'BooruArtworksUpdater',
    'LoliconAPI',
    'PixivArtworkUpdater',
]
