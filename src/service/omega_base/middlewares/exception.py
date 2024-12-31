"""
@Author         : Ailitonia
@Date           : 2023/6/9 19:11
@FileName       : exception
@Project        : nonebot2_miya
@Description    : Omega 平台中间件异常
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import final

from src.exception import PlatformException


@final
class AdapterNotSupported(PlatformException):
    """平台适配器不支持的方法"""

    def __init__(self, adapter_name: str, reason: str | None = None) -> None:
        self.adapter_name = adapter_name
        self.reason = reason

    @property
    def message(self) -> str:
        return f'adapter {self.adapter_name!r} not supported{"" if self.reason is None else f", {self.reason}"}'

    def __repr__(self):
        return f'{self.__class__.__name__}(adapter={self.adapter_name!r}, message={self.message})'


@final
class TargetNotSupported(PlatformException):
    """平台对象不支持的方法"""

    def __init__(self, target_name: str, reason: str | None = None) -> None:
        self.target_name = target_name
        self.reason = reason

    @property
    def message(self) -> str:
        return f'target {self.target_name!r} not supported{"" if self.reason is None else f", {self.reason}"}'

    def __repr__(self):
        return f'{self.__class__.__name__}(target={self.target_name!r}, message={self.message})'


@final
class BotNoFound(PlatformException):
    """找不到 Bot 实例或 Bot 未上线"""

    def __init__(self, bot_self_id: str):
        self.bot_self_id = bot_self_id

    @property
    def message(self) -> str:
        return f'bot {self.bot_self_id!r} not found, or bot is not online'

    def __repr__(self):
        return f'{self.__class__.__name__}(self_id={self.bot_self_id!r}, message={self.message})'


__all__ = [
    'AdapterNotSupported',
    'TargetNotSupported',
    'BotNoFound'
]
