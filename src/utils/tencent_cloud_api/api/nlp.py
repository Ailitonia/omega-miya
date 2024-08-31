"""
@Author         : Ailitonia
@Date           : 2021/12/24 22:43
@FileName       : nlp.py
@Project        : nonebot2_miya
@Description    : nlp api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal, Sequence

from .base import BaseTencentCloudAPI
from ..model.nlp import (
    TencentCloudComposeCoupletResponse,
    TencentCloudComposePoetryResponse,
    TencentCloudTextEmbellishResponse,
    TencentCloudTextWritingResponse,
    TencentCloudGenerateKeywordSentenceResponse,
    TencentCloudSentenceCorrectionResponse,
    TencentCloudClassifyContentResponse,
    TencentCloudAnalyzeSentimentResponse,
    TencentCloudEvaluateSentenceSimilarityResponse,
    TencentCloudEvaluateWordSimilarityResponse,
    TencentCloudParseWordsResponse,
    TencentCloudRetrieveSimilarWordsResponse,
)


class TencentNLP(BaseTencentCloudAPI):
    """腾讯云自然语言处理"""
    def __init__(
            self,
            *,
            host: str = 'nlp.tencentcloudapi.com',
            secret_id: str | None = None,
            secret_key: str | None = None
    ):
        super().__init__(host=host, secret_id=secret_id, secret_key=secret_key)

    async def compose_couplet(
            self,
            text: str,
            *,
            target_type: int = 0
    ) -> TencentCloudComposeCoupletResponse:
        """对联生成

        :param text: 生成对联的关键词, 长度需>=2，当长度>2时，自动截取前两个字作为关键字, 内容需为常用汉字
        :param target_type: 返回的文本结果为繁体还是简体, 0: 简体, 1: 繁体
        """
        payload = {'Text': text, 'TargetType': target_type}

        return TencentCloudComposeCoupletResponse.model_validate(
            await self._post_request(action='ComposeCouplet', version='2019-04-08', region='', payload=payload)
        )

    async def compose_poetry(
            self,
            text: str,
            *,
            poetry_type: int = 0,
            genre: int = 0
    ) -> TencentCloudComposePoetryResponse:
        """诗词生成

        :param text: 生成诗词的关键词
        :param poetry_type: 生成诗词的类型, 0: 藏头或藏身, 1: 藏头, 2: 藏身
        :param genre: 诗的体裁, 0: 五言律诗或七言律诗, 5: 五言律诗, 7: 七言律诗
        """
        payload = {'Text': text, 'PoetryType': poetry_type, 'Genre': genre}

        return TencentCloudComposePoetryResponse.model_validate(
            await self._post_request(action='ComposePoetry', version='2019-04-08', region='', payload=payload)
        )

    async def text_embellish(
            self,
            text: str,
            *,
            source_lang: Literal['zh', 'en'] = 'zh',
            number: Literal[1, 2, 3, 4, 5] = 1,
            style: Literal['both', 'expansion', 'rewriting', 'm2a', 'a2m'] = 'both',
    ) -> TencentCloudTextEmbellishResponse:
        """文本润色

        :param text: 待润色的文本, 中文文本长度需 <=50 字符, 英文文本长度需 <=30 个单词
        :param source_lang: 待润色文本的语言类型
        :param number: 返回润色结果的个数, 数量需 >=1 且 <=5 (注意实际结果可能小于指定个数)
        :param style: 控制润色类型, both: 同时返回改写和扩写, expansion: 扩写, rewriting: 改写, m2a: 从现代文改写为古文, a2m: 从古文改写为现代文
        """
        payload = {'Text': text, 'SourceLang': source_lang, 'Number': number, 'Style': style}

        return TencentCloudTextEmbellishResponse.model_validate(
            await self._post_request(action='TextEmbellish', version='2019-04-08', region='', payload=payload)
        )

    async def text_writing(
            self,
            text: str,
            *,
            source_lang: Literal['zh', 'en'] = 'zh',
            number: Literal[1, 2, 3, 4, 5] = 1,
            domain: Literal['general', 'academic'] = 'general',
            style: Literal['science_fiction', 'military_history', 'xuanhuan_wuxia', 'urban_officialdom'] = 'xuanhuan_wuxia',
    ) -> TencentCloudTextWritingResponse:
        """文本补全

        :param text: 待续写的句子, 文本统一使用 utf-8 格式编码, 长度不超过200字符
        :param source_lang: 待续写文本的语言类型
        :param number: 返回续写结果的个数, 数量需>=1且<=5(注意实际结果可能小于指定个数)
        :param domain: 指定续写领域, 支持领域如下: general: 通用领域, 支持中英文补全, academic: 学术领域, 仅支持英文补全
        :param style: 指定续写风格, 支持风格如下: science_fiction: 科幻, military_history: 军事, xuanhuan_wuxia: 武侠, urban_officialdom: 职场
        """
        payload = {'Text': text, 'SourceLang': source_lang, 'Number': number, 'Domain': domain, 'Style': style}

        return TencentCloudTextWritingResponse.model_validate(
            await self._post_request(action='TextWriting', version='2019-04-08', region='', payload=payload)
        )

    async def generate_keyword_sentence(
            self,
            word_list: Sequence[str],
            *,
            number: Literal[1, 2, 3, 4, 5] = 1,
            domain: Literal['general', 'academic'] = 'general',
    ) -> TencentCloudGenerateKeywordSentenceResponse:
        """句子生成

        :param word_list: 生成句子的关键词, 关键词个数需不超过4个, 中文关键词长度应不超过 10 字符, 英文关键词长度不超过3个单词, 关键词中不可包含标点符号
        :param number: 返回生成句子的个数, 数量需>=1且<=5
        :param domain: 指定生成句子的领域, 支持领域如下: general: 通用领域, 支持中英文, academic: 学术领域, 仅支持英文
        """
        payload = {'WordList': word_list, 'Number': number, 'Domain': domain}

        return TencentCloudGenerateKeywordSentenceResponse.model_validate(
            await self._post_request(action='GenerateKeywordSentence', version='2019-04-08', region='', payload=payload)
        )

    async def sentence_correction(self, text_list: list[str]) -> TencentCloudSentenceCorrectionResponse:
        """句子纠错

        :param text_list: 待纠错的句子列表, 可以以数组方式在一次请求中填写多个待纠错的句子, 文本统一使用 utf-8 格式编码, 每个中文句子的长度不超过 150 字符, 每个英文句子的长度不超过100个单词, 且数组长度需小于30
        """
        payload = {'TextList': text_list}

        return TencentCloudSentenceCorrectionResponse.model_validate(
            await self._post_request(action='SentenceCorrection', version='2019-04-08', region='', payload=payload)
        )

    async def classify_content(self, title: str, content: list[str]) -> TencentCloudClassifyContentResponse:
        """文本分类V2

        :param title: 待分类的文章的标题(仅支持 UTF-8 格式, 不超过 100 字符)
        :param content: 待分类文章的内容, 每个元素对应一个段落(支持 UTF-8 格式, 文章内容长度总和不超过 2000 字符)
        """
        payload = {'Title': title, 'Content': content}

        return TencentCloudClassifyContentResponse.model_validate(
            await self._post_request(action='ClassifyContent', version='2019-04-08', region='', payload=payload)
        )

    async def analyze_sentiment(self, text: str) -> TencentCloudAnalyzeSentimentResponse:
        """情感分析V2

        :param text: 待分析的文本（仅支持 UTF-8 格式, 不超过 200 字）
        """
        payload = {'Text': text}

        return TencentCloudAnalyzeSentimentResponse.model_validate(
            await self._post_request(action='AnalyzeSentiment', version='2019-04-08', region='', payload=payload)
        )

    async def evaluate_sentence_similarity(
            self,
            source_text: str,
            target_text: str
    ) -> TencentCloudEvaluateSentenceSimilarityResponse:
        """句子相似度V2

        :param source_text: 需要与目标句子计算相似度的源句子(仅支持 UTF-8 格式, 不超过 500 字符)
        :param target_text: 目标句子(仅支持 UTF-8 格式, 不超过 500 字符)
        """
        payload = {'SentencePairList': [{'SourceText': source_text, 'TargetText': target_text}]}

        return TencentCloudEvaluateSentenceSimilarityResponse.model_validate(
            await self._post_request(
                action='EvaluateSentenceSimilarity', version='2019-04-08', region='', payload=payload
            )
        )

    async def evaluate_word_similarity(
            self,
            source_word: str,
            target_word: str
    ) -> TencentCloudEvaluateWordSimilarityResponse:
        """词相似度V2

        :param source_word: 计算相似度的源词(仅支持 UTF-8 格式, 不超过 10 字符)
        :param target_word: 计算相似度的目标词(仅支持 UTF-8 格式, 不超过 10 字符)
        """
        payload = {'SourceWord': source_word, 'TargetWord': target_word}

        return TencentCloudEvaluateWordSimilarityResponse.model_validate(
            await self._post_request(action='EvaluateWordSimilarity', version='2019-04-08', region='', payload=payload)
        )

    async def parse_words(self, text: str) -> TencentCloudParseWordsResponse:
        """词法分析V2

        :param text: 待分析的文本(支持中英文文本, 不超过 500 字符)
        """
        payload = {'Text': text}

        return TencentCloudParseWordsResponse.model_validate(
            await self._post_request(action='ParseWords', version='2019-04-08', region='', payload=payload)
        )

    async def retrieve_similar_words(self, text: str, *, number: int = 10) -> TencentCloudRetrieveSimilarWordsResponse:
        """相似词召回

        :param text: 输入的词语(仅支持 UTF-8 格式, 不超过 10 字符)
        :param number: 召回的相似词个数, 取值范围为 1-20
        """
        payload = {'Text': text, 'Number': number}

        return TencentCloudRetrieveSimilarWordsResponse.model_validate(
            await self._post_request(action='RetrieveSimilarWords', version='2019-04-08', region='', payload=payload)
        )


__all__ = [
    'TencentNLP',
]
