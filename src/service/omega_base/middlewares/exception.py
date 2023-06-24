"""
@Author         : Ailitonia
@Date           : 2023/6/9 19:11
@FileName       : exception
@Project        : nonebot2_miya
@Description    : Omega 平台中间件异常
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import PlatformException


class AdapterNotSupported(PlatformException):
    def __init__(self, adapter_name: str) -> None:
        message = f'adapter "{adapter_name}" not supported'
        super().__init__(self, message)


class TargetNotSupported(PlatformException):
    def __init__(self, target_name: str) -> None:
        message = f'target "{target_name}" not supported'
        super().__init__(self, message)


class BotNoFound(PlatformException):
    pass


__all__ = [
    'AdapterNotSupported',
    'TargetNotSupported',
    'BotNoFound'
]
