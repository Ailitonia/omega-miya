"""
@Author         : Ailitonia
@Date           : 2022/04/16 14:29
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : Onebot Api Exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import OnebotApiException


class ApiNotImplement(OnebotApiException):
    """未实现 Onebot 标准协议要求的 api"""


class ApiNotSupport(OnebotApiException):
    """不支持 Onebot 标准协议要求的 api"""


__all__ = [
    'ApiNotImplement',
    'ApiNotSupport'
]
