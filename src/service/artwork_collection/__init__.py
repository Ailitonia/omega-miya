"""
@Author         : Ailitonia
@Date           : 2024/6/11 上午1:52
@FileName       : artwork_collection
@Project        : nonebot2_miya
@Description    : 收藏的图片、漫画等作品合集, 数据库统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .sites import (
    DanbooruArtworkCollection,
    LocalCollectedArtworkCollection,
    NoneArtworkCollection,
    PixivArtworkCollection,
)


__all__ = [
    'DanbooruArtworkCollection',
    'LocalCollectedArtworkCollection',
    'NoneArtworkCollection',
    'PixivArtworkCollection',
]
