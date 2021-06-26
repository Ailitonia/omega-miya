"""
@Author         : Ailitonia
@Date           : 2021/06/05 19:43
@FileName       : tmt.py
@Project        : nonebot2_miya 
@Description    : 腾讯云机器翻译模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from omega_miya.utils.Omega_Base import Result
from .cloud_api import SECRET_ID, SECRET_KEY, TencentCloudApi


class TencentTMT(object):
    def __init__(self):
        self.__secret_id = SECRET_ID
        self.__secret_key = SECRET_KEY

    async def translate(
            self,
            source_text: str,
            *,
            source: str = 'auto',
            target: str = 'zh',
            project_id: int = 0) -> Result.DictResult:
        payload = {'SourceText': source_text, 'Source': source, 'Target': target, 'ProjectId': project_id}
        api = TencentCloudApi(
            secret_id=self.__secret_id,
            secret_key=self.__secret_key,
            host='tmt.tencentcloudapi.com')
        result = await api.post_request(
            action='TextTranslate', version='2018-03-21', region='ap-chengdu', payload=payload)

        if result.error:
            return result
        response = dict(result.result.get('Response'))
        if response.get('Error'):
            return Result.DictResult(error=True, info=response.get('Error'), result={})

        trans_result = {
            'source': response.get('Source'),
            'target': response.get('Target'),
            'targettext': response.get('TargetText')
        }
        return Result.DictResult(error=False, info='Success', result=trans_result)


__all__ = [
    'TencentTMT'
]
