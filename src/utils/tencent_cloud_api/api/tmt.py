"""
@Author         : Ailitonia
@Date           : 2021/06/05 19:43
@FileName       : tmt.py
@Project        : nonebot2_miya 
@Description    : 腾讯云机器翻译模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional, Sequence

from .base import BaseTencentCloudAPI
from ..model.tmt import TencentCloudTextTranslateResponse, TencentCloudTextTranslateBatchResponse


class TencentTMT(BaseTencentCloudAPI):
    """腾讯云翻译"""
    def __init__(
            self,
            *,
            host: str = 'tmt.tencentcloudapi.com',
            secret_id: str | None = None,
            secret_key: str | None = None
    ):
        super().__init__(host=host, secret_id=secret_id, secret_key=secret_key)

    async def text_translate(
            self,
            source_text: str,
            *,
            source: str = 'auto',
            target: str = 'zh',
            project_id: int = 0,
            untranslated_text: Optional[str] = None
    ) -> TencentCloudTextTranslateResponse:
        """文本翻译

        :param source_text: 待翻译的文本, 文本统一使用utf-8格式编码
        :param source: 源语言
        :param target: 目标语言
        :param project_id: 项目ID, 如无配置请填写默认项目ID: 0
        :param untranslated_text: 用来标记不希望被翻译的文本内容, 如句子中的特殊符号、人名、地名等, 每次请求只支持配置一个不被翻译的单词, 不要配置动词或短语, 否则会影响翻译结果
        """
        payload = {'SourceText': source_text, 'Source': source, 'Target': target, 'ProjectId': project_id}
        if untranslated_text is not None:
            payload.update({'UntranslatedText': untranslated_text})

        return TencentCloudTextTranslateResponse.model_validate(
            await self._post_request(action='TextTranslate', version='2018-03-21', region='ap-chengdu', payload=payload)
        )

    async def text_translate_batch(
            self,
            source_text_list: Sequence[str],
            *,
            source: str = 'auto',
            target: str = 'zh',
            project_id: int = 0
    ) -> TencentCloudTextTranslateBatchResponse:
        """批量文本翻译

        :param source_text_list: 待翻译的文本列表, 文本统一使用 utf-8 格式编码, 请传入有效文本, html标记等非常规翻译文本可能会翻译失败, 单次请求的文本长度总和需要低于 6000 字符
        :param source: 源语言
        :param target: 目标语言
        :param project_id: 项目ID, 如无配置请填写默认项目ID: 0
        """
        payload = {'Source': source, 'Target': target, 'ProjectId': project_id, 'SourceTextList': source_text_list}

        return TencentCloudTextTranslateBatchResponse.model_validate(
            await self._post_request(
                action='TextTranslateBatch', version='2018-03-21', region='ap-chengdu', payload=payload
            )
        )


__all__ = [
    'TencentTMT',
]
