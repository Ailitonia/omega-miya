"""
@Author         : Ailitonia
@Date           : 2022/04/10 19:48
@FileName       : tmt.py
@Project        : nonebot2_miya 
@Description    : Tencent Cloud TMT Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .base_model import (
    BaseTencentCloudErrorResponse,
    BaseTencentCloudSuccessResponse,
    BaseTencentCloudResponse,
)


class TencentCloudTextTranslateSuccessResponse(BaseTencentCloudSuccessResponse):
    """文本翻译 API 调用成功返回内容

    - TargetText: 翻译后的文本
    - Source: 源语言
    - Target: 目标语言
    """
    TargetText: str
    Source: str
    Target: str


class TencentCloudTextTranslateResponse(BaseTencentCloudResponse):
    """文本翻译 API 调用成功返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudTextTranslateSuccessResponse


class TencentCloudTextTranslateBatchSuccessResponse(BaseTencentCloudSuccessResponse):
    """批量文本翻译 API 调用成功返回内容

    - Source: 源语言
    - Target: 目标语言
    - TargetTextList: 翻译后的文本列表
    """
    Source: str
    Target: str
    TargetTextList: list[str]


class TencentCloudTextTranslateBatchResponse(BaseTencentCloudResponse):
    """批量文本翻译 API 调用成功返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudTextTranslateBatchSuccessResponse


__all__ = [
    'TencentCloudTextTranslateResponse',
    'TencentCloudTextTranslateBatchResponse',
]
