import re
import json
from omega_miya.utils.Omega_Base import Result
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
        :param text: 待分析的文本（仅支持UTF-8格式，不超过200字）
        :param flag: 待分析文本所属的类型，仅当输入参数Mode取值为2class时有效（默认取4值）：
            1 - 商品评论类
            2 - 社交类
            3 - 美食酒店类
            4 - 通用领域类
        :param mode: 情感分类模式选项，可取2class或3class（默认值为2class）
            2class - 返回正负面二分类情感结果
            3class - 返回正负面及中性三分类情感结果
        :return: DictResult
            Positive：Float，正面情感概率
            Neutral：Float，中性情感概率，当输入参数Mode取值为3class时有效，否则值为空。注意：此字段可能返回 null，表示取不到有效值。
            Negative：Float，负面情感概率
            Sentiment：String，情感分类结果：
                1 - positive，表示正面情感
                2 - negative，表示负面情感
                3 - neutral，表示中性、无情感
            RequestId：String，唯一请求 ID，每次请求都会返回。定位问题时需要提供该次请求的 RequestId。
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


__all__ = [
    'TencentNLP'
]
