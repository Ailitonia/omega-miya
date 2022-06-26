"""
@Author         : Ailitonia
@Date           : 2022/05/08 1:27
@FileName       : deepl.py
@Project        : nonebot2_miya 
@Description    : DeepL Translate
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal

from omega_miya.web_resource import HttpFetcher
from omega_miya.exception import WebSourceException

from .config import deepl_config
from .model import TranslateResult


class BaseDeepLError(WebSourceException):
    """DeepL 异常基类"""


class DeepLApiError(BaseDeepLError):
    """Api 返回错误"""


class DeepL(object):
    _free_api: str = 'https://api-free.deepl.com/v2/'
    _pro_api: str = 'https://api.deepl.com/v2/'

    _default_headers = HttpFetcher.get_default_headers()
    _default_headers.update({'Content-Type': 'application/x-www-form-urlencoded'})
    _fetcher = HttpFetcher(timeout=15, headers=_default_headers)

    def __init__(self, *, api_version: Literal['free', 'pro'] = 'free'):
        self._api_version = api_version
        match api_version:
            case 'free':
                self.api = self._free_api
            case 'pro':
                self.api = self._pro_api
            case _:
                raise ValueError('invalid api version')

    def __repr__(self):
        return f'<{self.__class__.__name__}(api_version={self._api_version})>'

    async def translate(
            self,
            text: str,
            target_lang: str = 'ZH',
            *,
            source_lang: str | None = None,
            split_sentences: Literal['0', '1', 'nonewlines'] = '1',
    ) -> TranslateResult:
        """翻译"""
        data = self._fetcher.FormData()
        data.add_field(name='auth_key', value=deepl_config.deepl_auth_key)
        data.add_field(name='text', value=text)
        data.add_field(name='target_lang', value=target_lang)
        data.add_field(name='split_sentences', value=split_sentences)
        if source_lang:
            data.add_field(name='source_lang', value=source_lang)

        url = f'{self.api}translate'
        result = await self._fetcher.post_text(url, data=data)
        if result.status != 200:
            raise DeepLApiError(f'DeepLApiError, status code {result.status}')
        return TranslateResult.parse_obj(result.result)
