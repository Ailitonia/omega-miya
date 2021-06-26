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


__all__ = [
    'TencentNLP'
]
