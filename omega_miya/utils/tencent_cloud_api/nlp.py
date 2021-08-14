import re
import json
from typing import Optional
from omega_miya.database import Result
from .cloud_api import SECRET_ID, SECRET_KEY, TencentCloudApi


class TencentNLP(object):
    def __init__(self):
        self.__secret_id = SECRET_ID
        self.__secret_key = SECRET_KEY

    async def chat_bot(self, text: str, flag: int = 0) -> Result.TextResult:
        payload = {
            'Query': text,
            'Flag': flag}
        api = TencentCloudApi(
            secret_id=self.__secret_id,
            secret_key=self.__secret_key,
            host='nlp.tencentcloudapi.com')
        result = await api.post_request(
            action='ChatBot', version='2019-04-08', region='ap-guangzhou', payload=payload)

        if result.success():
            if result.result['Response'].get('Error'):
                return Result.TextResult(
                    error=True, info=f"API error: {result.result['Response'].get('Error')}", result='')
            else:
                return Result.TextResult(
                    error=False,
                    info=f"Success with confidence: {result.result['Response']['Confidence']}",
                    result=result.result['Response']['Reply']
                )
        else:
            return Result.TextResult(error=True, info=result.info, result='')

    async def describe_entity(self, entity_name: str, attr: str = '简介') -> Result.TextResult:
        payload = {'EntityName': entity_name}
        api = TencentCloudApi(
            secret_id=self.__secret_id,
            secret_key=self.__secret_key,
            host='nlp.tencentcloudapi.com')
        result = await api.post_request(
            action='DescribeEntity', version='2019-04-08', region='ap-guangzhou', payload=payload)

        if result.success():
            if result.result['Response'].get('Error'):
                return Result.TextResult(
                    error=True, info=f"API error: {result.result['Response'].get('Error')}", result='')
            else:
                content = json.loads(result.result['Response']['Content'])
                attr_content = content.get(attr)
                if isinstance(attr_content, list):
                    attr_text = ';\n'.join([
                        re.sub(r'\s{2,}', '', str(x.get('Name'))).replace('|@|', '\n') for x in attr_content
                    ])
                    return Result.TextResult(error=False, info='Success', result=attr_text)
                else:
                    return Result.TextResult(error=True, info='Attributes not found', result='')
        else:
            return Result.TextResult(error=True, info=result.info, result='')

    async def describe_relation(self, left_entity_name: str, right_entity_name: str) -> Result.TextResult:
        payload = {'LeftEntityName': left_entity_name, 'RightEntityName': right_entity_name}
        api = TencentCloudApi(
            secret_id=self.__secret_id,
            secret_key=self.__secret_key,
            host='nlp.tencentcloudapi.com')
        result = await api.post_request(
            action='DescribeRelation', version='2019-04-08', region='ap-guangzhou', payload=payload)

        if result.success():
            if result.result['Response'].get('Error'):
                return Result.TextResult(
                    error=True, info=f"API error: {result.result['Response'].get('Error')}", result='')
            else:
                content = result.result['Response']['Content']
                res_list = [
                    (x['Object'][0]['Name'][0], x['Subject'][0]['Name'][0], x['Relation']) for x in content[:-1]
                ]
                msg = ';\n'.join([f'{x[0]}是{x[1]}的{x[2]}' for x in res_list])
                return Result.TextResult(error=False, info=f'Get relation: {len(res_list)}', result=msg)
        else:
            return Result.TextResult(error=True, info=result.info, result='')

    async def sentiment_analysis(self, text: str, *, flag: int = 4, mode: str = '2class') -> Result.DictResult:
        """
        情感分析
        :param text: 待分析的文本（仅支持UTF-8格式, 不超过200字）
        :param flag: 待分析文本所属的类型, 仅当输入参数Mode取值为2class时有效（默认取4值）
            1: 商品评论类
            2: 社交类
            3: 美食酒店类
            4: 通用领域类
        :param mode: 情感分类模式选项, 可取2class或3class（默认值为2class）
            2class: 返回正负面二分类情感结果
            3class: 返回正负面及中性三分类情感结果
        :return: DictResult
            Positive: Float, 正面情感概率
            Neutral: Float, 中性情感概率, 当输入参数Mode取值为3class时有效, 否则值为空。注意: 此字段可能返回 null, 表示取不到有效值。
            Negative: Float, 负面情感概率
            Sentiment: String, 情感分类结果
                positive: 表示正面情感
                negative: 表示负面情感
                neutral: 表示中性、无情感
            RequestId: String, 唯一请求 ID, 每次请求都会返回。定位问题时需要提供该次请求的 RequestId。
        """
        payload = {'Text': text, 'Flag': flag, 'Mode': mode}
        api = TencentCloudApi(
            secret_id=self.__secret_id,
            secret_key=self.__secret_key,
            host='nlp.tencentcloudapi.com')
        result = await api.post_request(
            action='SentimentAnalysis', version='2019-04-08', region='ap-guangzhou', payload=payload)

        if result.success():
            if result.result['Response'].get('Error'):
                return Result.DictResult(
                    error=True, info=f"API error: {result.result['Response'].get('Error')}", result={})
            else:
                response = dict(result.result['Response'])
                return Result.DictResult(error=False, info='Success', result=response)
        else:
            return Result.DictResult(error=True, info=result.info, result={})

    async def sentiment_tendency(self, text: str, *, flag: int = 4, mode: str = '3class') -> Result.IntResult:
        """
        使用sentiment_analysis情感分析后直接返回情感倾向标签
        :param text: 待分析的文本（仅支持UTF-8格式, 不超过200字）
        :param flag: 待分析文本所属的类型, 同sentiment_analysis, 默认为4
        :param mode: 情感分类模式选项, 同sentiment_analysis, 默认为3class
        :return: IntResult
            1: positive, 表示正面情感
            0: neutral, 表示中性、无情感
            -1: negative, 表示负面情感
        """
        result = await self.sentiment_analysis(text=text, flag=flag, mode=mode)
        if result.success():
            sentiment = result.result.get('Sentiment')
            if sentiment == 'positive':
                return Result.IntResult(error=False, info='Success', result=1)
            elif sentiment == 'neutral':
                return Result.IntResult(error=False, info='Success', result=0)
            elif sentiment == 'negative':
                return Result.IntResult(error=False, info='Success', result=-1)
            else:
                return Result.IntResult(error=True, info=f'Sentiment result not found', result=-100)
        else:
            return Result.IntResult(error=True, info=result.info, result=-101)

    async def lexical_analysis(self, text: str, *, dict_id: Optional[str] = None, flag: int = 2) -> Result.DictResult:
        """
        词法分析
        :param text: 待分析的文本（仅支持UTF-8格式, 不超过500字）
        :param dict_id: 指定要加载的自定义词库ID
        :param flag: 词法分析模式（默认取2值）
            1: 高精度（混合粒度分词能力）
            2: 高性能（单粒度分词能力）
        :return: DictResult
            NerTokens: Array of NerToken, 命名实体识别结果。取值范围, 注意：此字段可能返回 null, 表示取不到有效值
                PER: 表示人名, 如刘德华、贝克汉姆
                LOC: 表示地名, 如北京、华山
                ORG: 表示机构团体名, 如腾讯、最高人民法院、人大附中
                PRODUCTION: 表示产品名, 如QQ、微信、iPhone
            PosTokens: Array of PosToken, 分词&词性标注结果（词性表请参见附录）
            RequestId: String, 唯一请求 ID, 每次请求都会返回。定位问题时需要提供该次请求的 RequestId
        """
        payload = {'Text': text, 'DictId': dict_id, 'Flag': flag} if dict_id else {'Text': text, 'Flag': flag}
        api = TencentCloudApi(
            secret_id=self.__secret_id,
            secret_key=self.__secret_key,
            host='nlp.tencentcloudapi.com')
        result = await api.post_request(
            action='LexicalAnalysis', version='2019-04-08', region='ap-guangzhou', payload=payload)

        if result.success():
            if result.result['Response'].get('Error'):
                return Result.DictResult(
                    error=True, info=f"API error: {result.result['Response'].get('Error')}", result={})
            else:
                response = dict(result.result['Response'])
                return Result.DictResult(error=False, info='Success', result=response)
        else:
            return Result.DictResult(error=True, info=result.info, result={})

    async def participle_and_tagging(
            self, text: str, *, dict_id: Optional[str] = None, flag: int = 2) -> Result.TupleListResult:
        """
        使用lexical_analysis进行分词和词性标注
        :param text: 待分析的文本（仅支持UTF-8格式, 不超过500字）
        :param dict_id: 指定要加载的自定义词库ID
        :param flag: 词法分析模式（默认取2值）
        :return: TupleListResult[Word: str, Pos: str]
            Word: 基础词
            Pos: 词性
        """
        result = await self.lexical_analysis(text=text, dict_id=dict_id, flag=flag)
        if result.success():
            participle_result = [(x.get('Word'), x.get('Pos')) for x in result.result.get('PosTokens')]
            return Result.TupleListResult(error=False, info='Success', result=participle_result)
        else:
            return Result.TupleListResult(error=True, info=result.info, result=[])


__all__ = [
    'TencentNLP'
]
