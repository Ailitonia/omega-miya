"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午6:55
@FileName       : exception
@Project        : nonebot2_miya
@Description    : Nhentai Exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import PluginException


class BaseNhentaiException(PluginException):
    """Nhentai 异常基类"""


class NhentaiParseError(BaseNhentaiException):
    """Nhentai 页面解析异常"""


__all__ = [
    'NhentaiParseError',
]
