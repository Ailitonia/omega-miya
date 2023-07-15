"""
@Author         : Ailitonia
@Date           : 2023/7/14 0:24
@FileName       : exception
@Project        : nonebot2_miya
@Description    : 签到插件异常
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import PluginException


class SignInException(PluginException):
    """签到异常基类"""


class DuplicateException(SignInException):
    """重复签到"""


class FailedException(SignInException):
    """签到失败"""


__all__ = [
    'DuplicateException',
    'FailedException',
    'SignInException'
]
