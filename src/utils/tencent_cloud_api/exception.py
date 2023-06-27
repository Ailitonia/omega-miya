"""
@Author         : Ailitonia
@Date           : 2022/04/10 19:55
@FileName       : exception.py
@Project        : nonebot2_miya 
@Description    : Tencent Cloud Exception
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import WebSourceException


class BaseTencentCloudError(WebSourceException):
    """TencentCloud 异常基类"""


class TencentCloudApiError(BaseTencentCloudError):
    """Api 返回错误"""


class TencentCloudNetworkError(BaseTencentCloudError):
    """TencentCloud 网络异常"""


__all__ = [
    'TencentCloudApiError',
    'TencentCloudNetworkError'
]
