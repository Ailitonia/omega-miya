"""
@Author         : Ailitonia
@Date           : 2022/04/16 14:29
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : OneBot Api Exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import OneBotApiException


class ApiNotImplement(OneBotApiException):
    """未实现 OneBot 标准协议要求的 api"""


class ApiNotSupport(OneBotApiException):
    """不支持 OneBot 标准协议要求的 api"""


__all__ = [
    'ApiNotImplement',
    'ApiNotSupport'
]
