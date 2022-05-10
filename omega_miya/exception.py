"""
@Author         : Ailitonia
@Date           : 2022/05/06 22:05
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : Omega exceptions
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


class OmegaException(Exception):
    """所有 Omega 异常的基类"""


class DatabaseException(OmegaException):
    """数据库异常"""


class LocalSourceException(OmegaException):
    """本地资源异常"""


class WebSourceException(OmegaException):
    """网络资源异常"""


class OnebotApiException(OmegaException):
    """Onebot API 异常"""


class PluginException(OmegaException):
    """由插件自定义的异常"""


__all__ = [
    'OmegaException',
    'DatabaseException',
    'LocalSourceException',
    'WebSourceException',
    'OnebotApiException',
    'PluginException'
]
