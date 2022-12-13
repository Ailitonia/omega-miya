"""
@Author         : Ailitonia
@Date           : 2022/04/10 19:48
@FileName       : tmt.py
@Project        : nonebot2_miya 
@Description    : Tencent Cloud TMT Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .base_model import BaseTencentCloudErrorResponse, BaseTencentCloudSuccessResponse, BaseTencentCloudResponse


class TencentCloudTextTranslateSuccessResponse(BaseTencentCloudSuccessResponse):
    """文本翻译 Api 调用成功返回内容"""
    TargetText: str
    Source: str
    Target: str


class TencentCloudTextTranslateResponse(BaseTencentCloudResponse):
    """文本翻译 Api 调用成功返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudTextTranslateSuccessResponse


__all__ = [
    'TencentCloudTextTranslateResponse'
]
