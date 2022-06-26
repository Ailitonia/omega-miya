"""
@Author         : Ailitonia
@Date           : 2021/06/28 21:42
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : shindanmaker data source
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
import ujson as json
from typing import Literal
from bs4 import BeautifulSoup
from pydantic import BaseModel, AnyUrl, parse_obj_as
from nonebot.log import logger

from omega_miya.web_resource import HttpFetcher
from omega_miya.local_resource import TmpResource
from omega_miya.exception import WebSourceException
from omega_miya.utils.process_utils import run_async_catching_exception


_TMP_PATH = TmpResource('shindan_maker')
"""缓存文件路径"""
_SHINDANMAKER_CACHE: dict[str, int] = {}
"""缓存占卜名称与对应id"""


class ShindanMakerSearchResult(BaseModel):
    """ShindanMaker 搜索结果"""
    id: int
    name: str
    url: AnyUrl


class ShindanMakerResult(BaseModel):
    """ShindanMaker 占卜结果"""
    text: str
    image_url: list[AnyUrl]


class ShindanMaker(object):
    _root_url = 'https://shindanmaker.com'
    _root_url_cn = 'https://cn.shindanmaker.com'

    def __init__(self, shindan_id: int):
        self.shindan_id = shindan_id

    @classmethod
    def _get_version_url(cls, version: Literal['original', 'cn'] = 'cn') -> str:
        """获取对应版本网站 url"""
        match version:
            case 'cn':
                url = cls._root_url_cn
            case _:
                url = cls._root_url
        return url

    @classmethod
    @run_async_catching_exception
    async def search(cls, keyword: str, *, version: Literal['original', 'cn'] = 'cn') -> list[ShindanMakerSearchResult]:
        """搜索占卜

        :param keyword: 搜索关键词
        :param version: 使用的网站版本
        """
        url = cls._get_version_url(version=version)
        search_url = f'{url}/list/search'
        params = {'q': keyword}
        search_result = await HttpFetcher(timeout=10).get_text(url=search_url, params=params)
        if search_result.status != 200:
            logger.error(f'ShindanMaker | ShindanMakerNetError, searching: {keyword} failed, {search_result}')
            raise WebSourceException('ShindanMakerNetError')

        page_bs = BeautifulSoup(search_result.result, 'lxml')
        result_index = page_bs.find(name='div', attrs={'id': 'shindan-index', 'class': 'index'})
        result_links = result_index.find_all(name='a', attrs={'class': 'shindanLink'})

        result = []
        for link in result_links:
            try:
                link_url = link.attrs.get('href')
                link_id = re.search(r'/(\d+?)$', link_url).group(1)
                link_name = link.get_text(strip=True, separator='').replace(' ', '')
                result.append({'id': link_id, 'name': link_name, 'url': link_url})
            except (KeyError, AttributeError):
                continue
        return parse_obj_as(list[ShindanMakerSearchResult], result)

    @run_async_catching_exception
    async def query_result(
            self,
            input_name: str,
            *,
            version: Literal['original', 'cn'] = 'cn'
    ) -> ShindanMakerResult:
        """获取占卜结果

        :param input_name: 占卜对象名称
        :param version: 使用的网站版本
        """
        url = self._get_version_url(version=version)
        query_url = f'{url}/{self.shindan_id}'
        query_result = await HttpFetcher(timeout=10).get_text(url=query_url)
        if query_result.status != 200:
            logger.error(f'ShindanMaker | ShindanMakerNetError, query: {self.shindan_id} failed, {query_result}')
            raise WebSourceException('ShindanMakerNetError')

        # 获取请求页面 token
        query_page_bs = BeautifulSoup(query_result.result, 'lxml')
        input_form_bs = query_page_bs.find(name='form', attrs={'id': 'shindanForm', 'method': 'POST'})
        token_bs = input_form_bs.find(name='input', attrs={'type': 'hidden', 'name': '_token'})
        token = token_bs.attrs.get('value')

        headers = HttpFetcher.get_default_headers()
        headers.update({
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': url,
            'referer': query_url,
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1'
        })

        data = HttpFetcher.FormData()
        data.add_field(name='_token', value=token)
        data.add_field(name='shindanName', value=input_name)
        data.add_field(name='hiddenName', value='无名的X')
        maker_result = await HttpFetcher(cookies=query_result.cookies, headers=headers).post_text(url=query_url,
                                                                                                  data=data)
        if maker_result.status != 200:
            logger.error(f'ShindanMaker | ShindanMakerNetError, make: {self.shindan_id} failed, {maker_result}')
            raise WebSourceException('ShindanMakerNetError')

        maker_page_bs = BeautifulSoup(maker_result.result, 'lxml')
        result_bs = maker_page_bs.find(name='span', attrs={'id': 'shindanResult'})
        result_image = [x.attrs.get('src') for x in result_bs.findAll(name='img', attrs={'title': None, 'style': None})]
        result_image = [x for x in result_image if x is not None]

        # 预处理结果里面的文本
        [line_break.replaceWith('\n') for line_break in result_bs.findAll(name='br')]
        result_text = result_bs.get_text()
        return ShindanMakerResult(text=result_text, image_url=result_image)

    @staticmethod
    @run_async_catching_exception
    async def download_image(url: str) -> TmpResource:
        """下载图片到本地, 保持原始文件名, 直接覆盖同名文件"""
        file_name = HttpFetcher.hash_url_file_name(url=url)
        file = _TMP_PATH('image', file_name)
        download_result = await HttpFetcher().download_file(url=url, file=file)
        if download_result.status != 200:
            raise RuntimeError(f'download failed, status {download_result.status}')
        return file

    @staticmethod
    async def read_shindan_cache() -> dict[str, int]:
        """从文件中读取占卜名缓存"""
        global _SHINDANMAKER_CACHE
        cache_file = _TMP_PATH('shindan_maker_cache.json')
        if not cache_file.path.exists():
            result = {}
            async with cache_file.async_open('w', encoding='utf8') as af:
                await af.write(json.dumps(result, ensure_ascii=False))
        else:
            async with cache_file.async_open('r', encoding='utf8') as af:
                data = await af.read()
                if not data:
                    result = {}
                else:
                    result = json.loads(data)

        _SHINDANMAKER_CACHE.update(result)
        return _SHINDANMAKER_CACHE

    @staticmethod
    @run_async_catching_exception
    async def upgrade_shindan_cache(data: dict[str, int]) -> None:
        """更新并写入占卜名缓存到文件"""
        cache_file = _TMP_PATH('shindan_maker_cache.json')
        if not cache_file.path.exists():
            async with cache_file.async_open('w+', encoding='utf8') as af:
                await af.write(json.dumps(data, ensure_ascii=False))
        else:
            async with cache_file.async_open('w+', encoding='utf8') as af:
                file_data = await af.read()
                if file_data:
                    exist_data: dict = json.loads(file_data)
                else:
                    exist_data = {}
                exist_data.update(_SHINDANMAKER_CACHE)
                exist_data.update(data)
                _SHINDANMAKER_CACHE.update(exist_data)
                await af.write(json.dumps(exist_data, ensure_ascii=False))


__all__ = [
    'ShindanMaker'
]
