"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午6:55
@FileName       : exception
@Project        : nonebot2_miya
@Description    : Nhentai Exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import WebSourceException


class BaseNhentaiException(WebSourceException):
    """Nhentai 异常基类"""


class NhentaiParseError(BaseNhentaiException):
    """Nhentai 页面解析异常"""


class NhentaiNetworkError(BaseNhentaiException):
    """Nhentai 网络连接异常"""


__all__ = [
    'NhentaiParseError',
    'NhentaiNetworkError'
]
