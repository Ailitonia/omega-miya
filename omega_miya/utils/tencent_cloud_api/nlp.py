import re
import json
from .cloud_api import SECRET_ID, SECRET_KEY, TencentCloudApi


class TencentNLP(object):
    def __init__(self):
        self.__secret_id = SECRET_ID
        self.__secret_key = SECRET_KEY

    async def chat_bot(self, text: str, flag: int = 0) -> TencentCloudApi.ApiRes:
        payload = {
            'Query': text,
            'Flag': flag}
        api = TencentCloudApi(
            secret_id=self.__secret_id,
            secret_key=self.__secret_key,
            host='nlp.tencentcloudapi.com')
        result = await api.post_request(
            action='ChatBot', version='2019-04-08', region='ap-guangzhou', payload=payload)

        if not result.error:
            if result.result['Response'].get('Error'):
                result.error = True
                result.info = result.result['Response'].get('Error')
            else:
                result.info = f"Confidence: {result.result['Response']['Confidence']}"
                result.result = result.result['Response']['Reply']
        return result

    async def describe_entity(self, entity_name: str, attr: str = None) -> TencentCloudApi.ApiRes:
        payload = {'EntityName': entity_name}
        api = TencentCloudApi(
            secret_id=self.__secret_id,
            secret_key=self.__secret_key,
            host='nlp.tencentcloudapi.com')
        result = await api.post_request(
            action='DescribeEntity', version='2019-04-08', region='ap-guangzhou', payload=payload)

        if not result.error:
            result.result = result.result
            if result.result['Response'].get('Error'):
                result.error = True
                result.info = result.result['Response'].get('Error')
            else:
                if attr:
                    content = json.loads(result.result['Response']['Content'])
                    attr_content = content.get(attr)
                    if attr_content:
                        attr_text = '\n'.join([re.sub(r'\s{2,}', '', x.get('Name')) for x in attr_content])
                        result.result = attr_text
                    else:
                        result.error = True
                        result.info = 'Attributes not found'
                else:
                    text = json.loads(result.result['Response']['Content'])['简介'][0]['Name']
                    text = re.sub(r'\s{2,}', '', str(text)).split('|@|')[0]
                    result.result = text
        return result

    async def describe_relation(self, left_entity_name: str, right_entity_name: str) -> TencentCloudApi.ApiRes:
        payload = {'LeftEntityName': left_entity_name, 'RightEntityName': right_entity_name}
        api = TencentCloudApi(
            secret_id=self.__secret_id,
            secret_key=self.__secret_key,
            host='nlp.tencentcloudapi.com')
        result = await api.post_request(
            action='DescribeRelation', version='2019-04-08', region='ap-guangzhou', payload=payload)
        if not result.error:
            if result.result['Response'].get('Error'):
                result.error = True
                result.info = result.result['Response'].get('Error')
            else:
                content = result.result = result.result['Response']['Content']
                res_list = \
                    [(x['Object'][0]['Name'][0], x['Subject'][0]['Name'][0], x['Relation']) for x in content[:-1]]
                msg = ';\n'.join([f'{x[0]}是{x[1]}的{x[2]}' for x in res_list])
                result.info = f'get relation: {len(res_list)}'
                result.result = msg
        return result


__all__ = [
    'TencentNLP'
]
