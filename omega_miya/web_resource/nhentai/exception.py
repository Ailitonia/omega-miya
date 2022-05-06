"""
@Author         : Ailitonia
@Date           : 2022/04/10 21:51
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : Nhentai Exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from omega_miya.exception import WebSourceException


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
