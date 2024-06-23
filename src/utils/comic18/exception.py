"""
@Author         : Ailitonia
@Date           : 2024/5/26 下午7:46
@FileName       : exception
@Project        : nonebot2_miya
@Description    : 18Comic Exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import WebSourceException


class BaseComic18Error(WebSourceException):
    """18Comic 异常基类"""


class Comic18NetworkError(BaseComic18Error):
    """18Comic 网络异常"""


__all__ = [
    'Comic18NetworkError'
]
