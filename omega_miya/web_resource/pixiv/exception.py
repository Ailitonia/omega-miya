"""
@Author         : Ailitonia
@Date           : 2022/04/09 15:57
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : Pixiv custom Exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


class BasePixivError(Exception):
    """Pixiv 异常基类"""


class PixivApiError(BasePixivError):
    """Api 返回错误"""


class PixivNetworkError(BasePixivError):
    """Pixiv 网络异常"""


class PixivisionNetworkError(BasePixivError):
    """Pixivision 网络异常"""


__all__ = [
    'PixivApiError',
    'PixivNetworkError',
    'PixivisionNetworkError'
]
