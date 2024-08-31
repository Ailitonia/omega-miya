"""
@Author         : Ailitonia
@Date           : 2023/2/3 23:48
@FileName       : exception
@Project        : nonebot2_miya
@Description    : Weibo exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import WebSourceException


class BaseWeiboError(WebSourceException):
    """Weibo 异常基类"""


class WeiboApiError(BaseWeiboError):
    """Api 返回错误"""


__all__ = [
    'WeiboApiError',
]
