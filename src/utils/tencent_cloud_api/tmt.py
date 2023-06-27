"""
@Author         : Ailitonia
@Date           : 2021/06/05 19:43
@FileName       : tmt.py
@Project        : nonebot2_miya 
@Description    : 腾讯云机器翻译模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.service.omega_requests import OmegaRequests

from .cloud_api import TencentCloudApi
from .model import TencentCloudTextTranslateResponse
from .exception import TencentCloudNetworkError


class TencentTMT(object):
    """腾讯云翻译"""
    def __init__(
            self,
            *,
            host: str = 'tmt.tencentcloudapi.com',
            secret_id: str | None = None,
            secret_key: str | None = None
    ):
        self._api = TencentCloudApi(host=host, secret_id=secret_id, secret_key=secret_key)

    async def translate(
            self,
            source_text: str,
            *,
            source: str = 'auto',
            target: str = 'zh',
            project_id: int = 0
    ) -> TencentCloudTextTranslateResponse:
        """文本翻译

        :param source_text: 待翻译的文本, 文本统一使用utf-8格式编码
        :param source: 源语言
        :param target: 目标语言
        :param project_id: 项目ID, 如无配置请填写默认项目ID:0
        """
        payload = {'SourceText': source_text, 'Source': source, 'Target': target, 'ProjectId': project_id}
        result = await self._api.post_request(
            action='TextTranslate', version='2018-03-21', region='ap-chengdu', payload=payload)
        if result.status_code != 200:
            raise TencentCloudNetworkError(f'TencentCloudNetworkError, status code {result.status_code}')
        return TencentCloudTextTranslateResponse.parse_obj(OmegaRequests.parse_content_json(result))


__all__ = [
    'TencentTMT'
]
