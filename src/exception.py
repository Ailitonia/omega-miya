"""
@Author         : Ailitonia
@Date           : 2022/12/01 19:55
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


class PlatformException(OmegaException):
    """平台中间件异常"""


class PluginException(OmegaException):
    """由插件自定义的异常"""


__all__ = [
    'OmegaException',
    'DatabaseException',
    'LocalSourceException',
    'WebSourceException',
    'PlatformException',
    'PluginException',
]
