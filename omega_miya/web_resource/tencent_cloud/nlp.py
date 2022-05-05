from typing import Optional

from .cloud_api import TencentCloudApi
from .exception import TencentCloudNetworkError
from .model import (TencentCloudChatBotResponse, TencentCloudSentimentAnalysisResponse,
                    TencentCloudLexicalAnalysisResponse, TencentCloudTextCorrectionResponse)


class TencentNLP(object):
    """腾讯云自然语言处理"""
    def __init__(
            self,
            *,
            host: str = 'nlp.tencentcloudapi.com',
            secret_id: str | None = None,
            secret_key: str | None = None):
        self._api = TencentCloudApi(host=host, secret_id=secret_id, secret_key=secret_key)

    async def chat_bot(
            self,
            query: str,
            *,
            flag: int = 0) -> TencentCloudChatBotResponse:
        """闲聊

        :param query: 用户请求的query
        :param flag: 0: 通用闲聊, 1:儿童闲聊, 默认是通用闲聊
        """
        payload = {'Query': query, 'Flag': flag}
        result = await self._api.post_request(
            action='ChatBot', version='2019-04-08', region='ap-guangzhou', payload=payload)
        if result.status != 200:
            raise TencentCloudNetworkError(f'TencentCloudNetworkError, status code {result.status}')
        return TencentCloudChatBotResponse.parse_obj(result.result)

    async def sentiment_analysis(
            self,
            text: str,
            *,
            flag: int = 4,
            mode: str = '2class') -> TencentCloudSentimentAnalysisResponse:
        """情感分析

        :param text: 待分析的文本（仅支持UTF-8格式, 不超过200字）
        :param flag: 待分析文本所属的类型, 仅当输入参数Mode取值为2class时有效（默认取4值）
            1: 商品评论类
            2: 社交类
            3: 美食酒店类
            4: 通用领域类
        :param mode: 情感分类模式选项, 可取2class或3class（默认值为2class）
            2class: 返回正负面二分类情感结果
            3class: 返回正负面及中性三分类情感结果
        """
        payload = {'Text': text, 'Flag': flag, 'Mode': mode}
        result = await self._api.post_request(
            action='SentimentAnalysis', version='2019-04-08', region='ap-guangzhou', payload=payload)
        if result.status != 200:
            raise TencentCloudNetworkError(f'TencentCloudNetworkError, status code {result.status}')
        return TencentCloudSentimentAnalysisResponse.parse_obj(result.result)

    async def lexical_analysis(
            self,
            text: str,
            *,
            dict_id: Optional[str] = None,
            flag: int = 2) -> TencentCloudLexicalAnalysisResponse:
        """词法分析

        :param text: 待分析的文本（仅支持UTF-8格式, 不超过500字）
        :param dict_id: 指定要加载的自定义词库ID
        :param flag: 词法分析模式（默认取2值）
            1: 高精度（混合粒度分词能力）
            2: 高性能（单粒度分词能力）
        :return: TencentCloudLexicalAnalysisResponse
            NerTokens: Array of NerToken, 命名实体识别结果。取值范围, 注意：此字段可能返回 null, 表示取不到有效值
                PER: 表示人名, 如刘德华、贝克汉姆
                LOC: 表示地名, 如北京、华山
                ORG: 表示机构团体名, 如腾讯、最高人民法院、人大附中
                PRODUCTION: 表示产品名, 如QQ、微信、iPhone
            PosTokens: Array of PosToken, 分词&词性标注结果（词性表请参见附录）
            RequestId: String, 唯一请求 ID, 每次请求都会返回。定位问题时需要提供该次请求的 RequestId
        """
        payload = {'Text': text, 'DictId': dict_id, 'Flag': flag} if dict_id else {'Text': text, 'Flag': flag}
        result = await self._api.post_request(
            action='LexicalAnalysis', version='2019-04-08', region='ap-guangzhou', payload=payload)
        if result.status != 200:
            raise TencentCloudNetworkError(f'TencentCloudNetworkError, status code {result.status}')
        return TencentCloudLexicalAnalysisResponse.parse_obj(result.result)

    async def text_correction(self, text: str) -> TencentCloudTextCorrectionResponse:
        """文本纠错

        :param text: 待纠错的文本(仅支持UTF-8格式, 不超过2000字符)
        :return: TencentCloudTextCorrectionResponse
            CCITokens: Array of CCIToken, 纠错详情, 注意：此字段可能返回 null, 表示取不到有效值。
                Word: str, 错别字内容
                BeginOffset: int, 错别字的起始位置，从0开始
                CorrectWord: str, 错别字纠错结果
            ResultText: str, 纠错后的文本
            RequestId: str, 唯一请求 ID, 每次请求都会返回。定位问题时需要提供该次请求的 RequestId。
        """
        payload = {'Text': text}
        result = await self._api.post_request(
            action='TextCorrection', version='2019-04-08', region='ap-guangzhou', payload=payload)
        if result.status != 200:
            raise TencentCloudNetworkError(f'TencentCloudNetworkError, status code {result.status}')
        return TencentCloudTextCorrectionResponse.parse_obj(result.result)


__all__ = [
    'TencentNLP'
]
