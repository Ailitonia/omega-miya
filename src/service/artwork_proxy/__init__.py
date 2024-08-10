"""
@Author         : Ailitonia
@Date           : 2024/8/4 下午5:32
@FileName       : artwork_proxy
@Project        : nonebot2_miya
@Description    : 图站 API 及本地图片缓存统一接口
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .sites import DanbooruArtworkProxy, PixivArtworkProxy


__all__ = [
    'DanbooruArtworkProxy',
    'PixivArtworkProxy',
]
