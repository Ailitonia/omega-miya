"""
@Author         : Ailitonia
@Date           : 2022/04/10 19:02
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Tencent Cloud Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


from .base_model import BaseTencentCloudErrorResponse as TencentCloudErrorResponse
from .tmt import TencentCloudTextTranslateResponse
from .nlp import (TencentCloudChatBotResponse, TencentCloudSentimentAnalysisResponse,
                  TencentCloudLexicalAnalysisResponse, TencentCloudTextCorrectionResponse)


__all__ = [
    'TencentCloudErrorResponse',
    'TencentCloudTextTranslateResponse',
    'TencentCloudChatBotResponse',
    'TencentCloudSentimentAnalysisResponse',
    'TencentCloudLexicalAnalysisResponse',
    'TencentCloudTextCorrectionResponse'
]
