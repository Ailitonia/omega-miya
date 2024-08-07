"""
@Author         : Ailitonia
@Date           : 2022/04/11 20:31
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : Bilibili Exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import WebSourceException


class BaseBilibiliError(WebSourceException):
    """Bilibili 异常基类"""


class BilibiliApiError(BaseBilibiliError):
    """Bilibili API 异常"""


__all__ = [
    'BilibiliApiError',
]
