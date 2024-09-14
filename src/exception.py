"""
@Author         : Ailitonia
@Date           : 2022/12/01 19:55
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : Omega exceptions
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, final

if TYPE_CHECKING:
    from pathlib import PurePath


class OmegaException(Exception):
    """所有 Omega 异常的基类"""

    def __str__(self) -> str:
        return self.__repr__()


class LocalSourceException(OmegaException):
    """本地资源异常"""

    def __init__(self, path: "PurePath"):
        self.path = path


class PlatformException(OmegaException):
    """平台中间件异常"""


class PluginException(OmegaException):
    """由插件自定义的异常"""


@final
class WebSourceException(OmegaException):
    """网络资源异常"""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(status_code={self.status_code!r}, message={self.message})'


__all__ = [
    'OmegaException',
    'LocalSourceException',
    'PlatformException',
    'PluginException',
    'WebSourceException',
]
