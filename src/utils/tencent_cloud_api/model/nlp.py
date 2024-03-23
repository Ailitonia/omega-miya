"""
@Author         : Ailitonia
@Date           : 2022/04/10 20:07
@FileName       : nlp.py
@Project        : nonebot2_miya 
@Description    : Tencent Cloud NLP Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from .base_model import (BaseTencentCloudModel, BaseTencentCloudErrorResponse,
                         BaseTencentCloudSuccessResponse, BaseTencentCloudResponse)


class TencentCloudChatBotSuccessResponse(BaseTencentCloudSuccessResponse):
    """闲聊 Api 调用成功返回内容"""
    Reply: str
    Confidence: float


class TencentCloudChatBotResponse(BaseTencentCloudResponse):
    """闲聊 Api 调用成功返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudChatBotSuccessResponse


class TencentCloudSentimentAnalysisSuccessResponse(BaseTencentCloudSuccessResponse):
    """情感分析 Api 调用成功返回内容"""
    Positive: float
    Neutral: float | None = None
    Negative: float
    Sentiment: Literal['positive', 'negative', 'neutral']


class TencentCloudSentimentAnalysisResponse(BaseTencentCloudResponse):
    """情感分析 Api 调用成功返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudSentimentAnalysisSuccessResponse


class TencentCloudNerToken(BaseTencentCloudModel):
    """命名实体识别结果, 被如下接口引用: LexicalAnalysis"""
    Word: str  # 基础词
    Length: int  # 长度
    BeginOffset: int  # 起始位置
    Type: str  # 命名实体类型


class TencentCloudPosToken(BaseTencentCloudModel):
    """分词&词性标注结果, 被如下接口引用: LexicalAnalysis"""
    Word: str  # 基础词
    Length: int  # 长度
    BeginOffset: int  # 起始位置
    Pos: str  # 词性


class TencentCloudLexicalAnalysisSuccessResponse(BaseTencentCloudSuccessResponse):
    """词法分析 Api 调用成功返回内容"""
    PosTokens: list[TencentCloudPosToken]
    NerTokens: list[TencentCloudNerToken] | None = None


class TencentCloudLexicalAnalysisResponse(BaseTencentCloudResponse):
    """词法分析 Api 调用成功返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudLexicalAnalysisSuccessResponse


class TencentCloudCCIToken(BaseTencentCloudModel):
    """文本纠错结果, 被如下接口引用: TextCorrection, TextCorrectionPro"""
    Word: str  # 错别字内容
    BeginOffset: int  # 错别字的起始位置, 从0开始
    CorrectWord: str  # 错别字纠错结果


class TencentCloudTextCorrectionSuccessResponse(BaseTencentCloudSuccessResponse):
    """文本纠错 Api 调用成功返回内容"""
    CCITokens: list[TencentCloudCCIToken] | None = None
    ResultText: str


class TencentCloudTextCorrectionResponse(BaseTencentCloudResponse):
    """文本纠错 Api 调用成功返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudTextCorrectionSuccessResponse


__all__ = [
    'TencentCloudChatBotResponse',
    'TencentCloudSentimentAnalysisResponse',
    'TencentCloudLexicalAnalysisResponse',
    'TencentCloudTextCorrectionResponse'
]
