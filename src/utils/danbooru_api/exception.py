"""
@Author         : Ailitonia
@Date           : 2024/8/1 14:51:20
@FileName       : exception.py
@Project        : omega-miya
@Description    : Danbooru 异常
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import WebSourceException


class BaseDanbooruError(WebSourceException):
    """Danbooru 异常基类"""


class DanbooruNetworkError(BaseDanbooruError):
    """Danbooru 网络异常"""


__all__ = [
    'DanbooruNetworkError'
]
