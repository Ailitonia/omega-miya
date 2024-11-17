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

from .base_model import (
    BaseTencentCloudErrorResponse,
    BaseTencentCloudModel,
    BaseTencentCloudResponse,
    BaseTencentCloudSuccessResponse,
)


class TencentCloudChatBotSuccessResponse(BaseTencentCloudSuccessResponse):
    """闲聊 API 调用成功返回内容"""
    Reply: str
    Confidence: float


class TencentCloudChatBotResponse(BaseTencentCloudResponse):
    """闲聊 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudChatBotSuccessResponse


class TencentCloudComposeCoupletSuccessResponse(BaseTencentCloudSuccessResponse):
    """对联生成 API 调用成功返回内容

    - TopScroll: 横批
    - Content: 上联与下联
    - RandomCause: 当对联随机生成时, 展示随机生成原因
    """
    TopScroll: str
    Content: list[str]
    RandomCause: str | None = None


class TencentCloudComposeCoupletResponse(BaseTencentCloudResponse):
    """对联生成 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudComposeCoupletSuccessResponse


class TencentCloudComposePoetrySuccessResponse(BaseTencentCloudSuccessResponse):
    """诗词生成 API 调用成功返回内容

    - Title: 诗题, 即输入的生成诗词的关键词
    """
    Title: str
    Content: list[str]  # 诗的内容


class TencentCloudComposePoetryResponse(BaseTencentCloudResponse):
    """诗词生成 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudComposePoetrySuccessResponse


class TencentCloudEmbellishList(BaseTencentCloudModel):
    """文本润色结果

    - Text: 润色后的文本, 注意: 此字段可能返回 null, 表示取不到有效值
    - EmbellishType: 润色类型, expansion: 扩写, rewriting: 改写, translation_m2a: 从现代文改写为古文, translation_a2m: 从古文改写为现代文, 注意: 此字段可能返回 null, 表示取不到有效值
    """
    Text: str | None = None
    EmbellishType: str | None = None


class TencentCloudTextEmbellishSuccessResponse(BaseTencentCloudSuccessResponse):
    """文本润色 API 调用成功返回内容

    - EmbellishList: 润色结果列表
    """
    EmbellishList: list[TencentCloudEmbellishList]


class TencentCloudTextEmbellishResponse(BaseTencentCloudResponse):
    """文本润色 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudTextEmbellishSuccessResponse


class TencentCloudWritingList(BaseTencentCloudModel):
    """续写结果列表

    - TargetText: 续写的文本
    - PrefixText: 续写的前缀
    """
    TargetText: str
    PrefixText: str


class TencentCloudTextWritingSuccessResponse(BaseTencentCloudSuccessResponse):
    """文本补全 API 调用成功返回内容

    - WritingList: 续写结果列表
    """
    WritingList: list[TencentCloudWritingList]


class TencentCloudTextWritingResponse(BaseTencentCloudResponse):
    """文本补全 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudTextWritingSuccessResponse


class TencentCloudKeywordSentence(BaseTencentCloudModel):
    """通过关键词生成的句子信息

    - TargetText: 通过关键词生成的句子
    """
    TargetText: str


class TencentCloudGenerateKeywordSentenceSuccessResponse(BaseTencentCloudSuccessResponse):
    """句子生成 API 调用成功返回内容

    - KeywordSentenceList: 生成的句子列表
    """
    KeywordSentenceList: list[TencentCloudKeywordSentence]


class TencentCloudGenerateKeywordSentenceResponse(BaseTencentCloudResponse):
    """句子生成 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudGenerateKeywordSentenceSuccessResponse


class TencentCloudCorrectionItem(BaseTencentCloudModel):
    """纠错结果列表

    - Order: 纠错句子的序号
    - BeginOffset: 错误的起始位置, 从0开始
    - Len: 错误内容长度
    - Word: 错误内容
    - CorrectWord: 纠错结果, 当为删除类错误时, 结果为null, 注意: 此字段可能返回 null, 表示取不到有效值
    - CorrectionType: 纠错类型, 0: 替换, 1: 插入, 2: 删除
    - Confidence: 纠错信息置信度, 0: error, 1: warning, error 的置信度更高(仅供参考)
    - DescriptionZh: 纠错信息中文描述, 注意: 此字段可能返回 null, 表示取不到有效值
    - DescriptionEn: 纠错信息英文描述, 注意: 此字段可能返回 null, 表示取不到有效值
    """
    Order: int
    BeginOffset: int
    Len: int
    Word: str
    CorrectWord: list[str] | None = None
    CorrectionType: int
    Confidence: int
    DescriptionZh: str | None = None
    DescriptionEn: str | None = None


class TencentCloudSentenceCorrectionSuccessResponse(BaseTencentCloudSuccessResponse):
    """句子纠错 API 调用成功返回内容

    - CorrectionList: 纠错结果列表(注意仅展示错误句子的纠错结果, 若句子无错则不展示, 若全部待纠错句子都被认为无错, 则可能返回数组为空)
    """
    CorrectionList: list[TencentCloudCorrectionItem]


class TencentCloudSentenceCorrectionResponse(BaseTencentCloudResponse):
    """句子纠错 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudSentenceCorrectionSuccessResponse


class TencentCloudCategory(BaseTencentCloudModel):
    """分类详细信息

    - Id: 分类id, 注意: 此字段可能返回 null, 表示取不到有效值
    - Label: 分类英文名, 注意: 此字段可能返回 null, 表示取不到有效值
    - Name: 分类中文名, 注意: 此字段可能返回 null, 表示取不到有效值
    - Score: 分类置信度, 注意: 此字段可能返回 null, 表示取不到有效值
    """
    Id: int | None = None
    Label: str | None = None
    Name: str | None = None
    Score: float | None = None


class TencentCloudClassifyContentSuccessResponse(BaseTencentCloudSuccessResponse):
    """文本分类 V2 API 调用成功返回内容

    - FirstClassification: 一级分类
    - SecondClassification: 二级分类
    - ThirdClassification: 三级分类
    """
    FirstClassification: TencentCloudCategory
    SecondClassification: TencentCloudCategory
    ThirdClassification: TencentCloudCategory


class TencentCloudClassifyContentResponse(BaseTencentCloudResponse):
    """句子纠错 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudClassifyContentSuccessResponse


class TencentCloudAnalyzeSentimentSuccessResponse(BaseTencentCloudSuccessResponse):
    """情感分析V2 API 调用成功返回内容

    - Positive: 正面情感概率
    - Neutral: 中性情感概率
    - Negative: 负面情感概率
    - Sentiment: 情感分类结果: positive: 正面情感, negative: 负面情感, neutral: 中性、无情感
    """
    Positive: float
    Neutral: float
    Negative: float
    Sentiment: Literal['positive', 'negative', 'neutral']


class TencentCloudAnalyzeSentimentResponse(BaseTencentCloudResponse):
    """情感分析V2 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudAnalyzeSentimentSuccessResponse


class TencentCloudEvaluateSentenceSimilaritySuccessResponse(BaseTencentCloudSuccessResponse):
    """句子相似度V2 API 调用成功返回内容

    - ScoreList: 每个句子对的相似度分值
    """
    ScoreList: list[float]


class TencentCloudEvaluateSentenceSimilarityResponse(BaseTencentCloudResponse):
    """句子相似度V2 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudEvaluateSentenceSimilaritySuccessResponse


class TencentCloudEvaluateWordSimilaritySuccessResponse(BaseTencentCloudSuccessResponse):
    """词相似度V2 API 调用成功返回内容

    - Similarity: 词相似度分值
    """
    Similarity: float


class TencentCloudEvaluateWordSimilarityResponse(BaseTencentCloudResponse):
    """词相似度V2 API 调用返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudEvaluateWordSimilaritySuccessResponse


class TencentCloudBasicParticiple(BaseTencentCloudModel):
    """基础粒度分词和词性标注的结果

    - Word: 基础词
    - BeginOffset: 起始位置
    - Length: 基础词的长度
    - Pos: 词性
    """
    Word: str
    BeginOffset: int
    Length: int
    Pos: str


class TencentCloudCompoundParticiple(TencentCloudBasicParticiple):
    """复合粒度分词和词性标注的结果

    - Word: 基础词
    - BeginOffset: 基础词在 NormalText 中的起始位置
    - Length: 基础词的长度
    - Pos: 词性
    """


class TencentCloudEntity(BaseTencentCloudModel):
    """实体识别结果

    - Word: 基础词
    - BeginOffset: 基础词在 NormalText 中的起始位置
    - Length: 基础词的长度
    - Type: 实体类型的标准名字
    - Name: 类型名字的自然语言表达(中文或英文)
    """
    Word: str
    BeginOffset: int
    Length: int
    Type: str
    Name: str


class TencentCloudParseWordsSuccessResponse(BaseTencentCloudSuccessResponse):
    """词法分析V2 API 调用成功返回内容

    - NormalText: 输入文本正则化的结果(包括对英文文本中的开头和实体进行大写等)
    - BasicParticiples: 基础粒度分词和词性标注的结果
    - CompoundParticiples: 复合粒度分词和词性标注的结果
    - Entities: 实体识别结果
    """
    NormalText: str
    BasicParticiples: list[TencentCloudBasicParticiple]
    CompoundParticiples: list[TencentCloudCompoundParticiple]
    Entities: list[TencentCloudEntity]


class TencentCloudParseWordsResponse(BaseTencentCloudResponse):
    """词法分析V2 API 调用成功返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudParseWordsSuccessResponse


class TencentCloudRetrieveSimilarWordsSuccessResponse(BaseTencentCloudSuccessResponse):
    """相似词召回 API 调用成功返回内容

    - WordList: 召回的相似词数组
    """
    WordList: list[str]


class TencentCloudRetrieveSimilarWordsResponse(BaseTencentCloudResponse):
    """相似词召回 API 调用成功返回"""
    Response: BaseTencentCloudErrorResponse | TencentCloudRetrieveSimilarWordsSuccessResponse


__all__ = [
    'TencentCloudComposeCoupletResponse',
    'TencentCloudComposePoetryResponse',
    'TencentCloudTextEmbellishResponse',
    'TencentCloudTextWritingResponse',
    'TencentCloudGenerateKeywordSentenceResponse',
    'TencentCloudSentenceCorrectionResponse',
    'TencentCloudClassifyContentResponse',
    'TencentCloudAnalyzeSentimentResponse',
    'TencentCloudEvaluateSentenceSimilarityResponse',
    'TencentCloudEvaluateWordSimilarityResponse',
    'TencentCloudParseWordsResponse',
    'TencentCloudRetrieveSimilarWordsResponse',
]
