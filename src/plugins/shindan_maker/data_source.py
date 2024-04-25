"""
@Author         : Ailitonia
@Date           : 2021/06/28 21:42
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : shindan maker data source
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re
import ujson as json
from typing import Literal, Optional

from nonebot.log import logger
from nonebot.utils import run_sync
from rapidfuzz import process, fuzz
from zhconv import convert as zh_convert

from src.exception import WebSourceException
from src.resource import TemporaryResource
from src.service import OmegaRequests
from src.utils.process_utils import semaphore_gather

from .config import shindan_maker_plugin_config
from .model import ShindanMakerResult, ShindanMakerSearchResult
from .helper import (parse_searching_result_page, parse_shindan_page_title,
                     parse_shindan_page_token, parse_shindan_result_page)


_TMP_FOLDER = TemporaryResource('shindan_maker')
"""缓存路径"""
_SHINDAN_MAKER_CACHE: dict[str, int] = {}
"""缓存占卜名称与对应id"""


class ShindanMakerNetworkError(WebSourceException):
    """ShindanMaker 网络异常"""


class ShindanMaker(object):
    """ShindanMaker 占卜生成"""
    def __init__(self, shindan_id: int):
        self.shindan_id = shindan_id

    @classmethod
    def _root_url(cls) -> str:
        return shindan_maker_plugin_config.root_url

    @classmethod
    async def ranking_list(
            cls,
            mode: Optional[Literal['pickup', 'latest', 'daily', 'monthly', 'favorite', 'favhot', 'overall']] = None
    ) -> list[ShindanMakerSearchResult]:
        """列出占卜排行榜

        :param mode: 排序方式, 默认: 按热度, pickup: 最新热度, latest: 最新添加, daily: 每日排名, monthly: 每月排名, favorite: 收藏数, favhot: 最新收藏, overall: 综合
        """
        url = f'{cls._root_url()}/list'
        if mode is not None:
            url += f'/{mode}'

        response = await OmegaRequests(timeout=10).get(url=url)
        if response.status_code != 200:
            logger.error(f'ShindanMaker | Get ranking list {mode!r} failed, {response}')
            raise ShindanMakerNetworkError(response)

        return await run_sync(parse_searching_result_page)(content=OmegaRequests.parse_content_text(response=response))

    @classmethod
    async def search(
            cls,
            keyword: str,
            *,
            mode: Literal['search', 'themes'] = 'search',
            last_number: Optional[int] = None,
            page: Optional[int] = None,
            order: Optional[Literal['popular', 'favorites']] = None

    ) -> list[ShindanMakerSearchResult]:
        """搜索占卜

        :param keyword: 搜索关键词
        :param mode: 搜索模式, search: 关键词搜索, themes: 主题或 tag 搜索
        :param last_number: 用途未知
        :param page: 搜索页码
        :param order: 排序方式, 默认: 按时间, popular: 按人气, favorites: 按收藏数
        """
        search_url = f'{cls._root_url()}/list/{mode}'
        params = {'q': keyword}
        if last_number is not None:
            params.update({'lastnumber': last_number})
        if page is not None:
            params.update({'page': page})
        if order is not None:
            params.update({'order': order})

        response = await OmegaRequests(timeout=10).get(url=search_url, params=params)
        if response.status_code != 200:
            logger.error(f'ShindanMaker | Searching {keyword!r} failed, {response}')
            raise ShindanMakerNetworkError(response)

        return await run_sync(parse_searching_result_page)(content=OmegaRequests.parse_content_text(response=response))

    @classmethod
    async def complex_ranking(cls) -> list[ShindanMakerSearchResult]:
        """通过排行榜获取更多的占卜"""
        searching_tasks = [
            cls.ranking_list(),
            cls.ranking_list(mode='pickup'),
            cls.ranking_list(mode='latest'),
            cls.ranking_list(mode='daily'),
            cls.ranking_list(mode='monthly'),
            cls.ranking_list(mode='overall')
        ]
        searching_results_group = await semaphore_gather(tasks=searching_tasks, semaphore_num=6, filter_exception=True)

        result = []
        for results in searching_results_group:
            for item in results:
                if item.id not in [x.id for x in result]:
                    result.append(item)
        # 更新缓存
        await cls._upgrade_shindan_cache(data={item.name: item.id for item in result})
        return result

    @classmethod
    async def complex_search(cls, keyword: str) -> list[ShindanMakerSearchResult]:
        """搜索更多的占卜"""
        keyword_ht = zh_convert(keyword, 'zh-hant')

        searching_tasks = []
        for page in range(1, 3):
            for kw in [keyword, keyword_ht]:
                searching_tasks.append(cls.search(keyword=kw, page=page))
                searching_tasks.append(cls.search(keyword=kw, page=page, order='popular'))
                searching_tasks.append(cls.search(keyword=kw, page=page, order='favorites'))

        searching_results_group = await semaphore_gather(tasks=searching_tasks, semaphore_num=6, filter_exception=True)
        result = sorted(set(x for results in searching_results_group for x in results), key=lambda x: x.id)

        # 更新缓存
        await cls._upgrade_shindan_cache(data={item.name: item.id for item in result})
        return result

    async def query_shindan_result(self, input_name: str) -> ShindanMakerResult:
        """获取占卜结果

        :param input_name: 占卜对象名称
        """
        query_url = f'{self._root_url()}/{self.shindan_id}'

        page_response = await OmegaRequests(timeout=10).get(url=query_url)
        if page_response.status_code != 200:
            logger.error(f'ShindanMaker | Get shindan {self.shindan_id!r} page failed, {page_response}')
            raise ShindanMakerNetworkError(page_response)

        headers = OmegaRequests.get_default_headers()
        headers.update({
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': self._root_url(),
            'referer': query_url,
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1'
        })

        page_content = OmegaRequests.parse_content_text(response=page_response)

        # 更新缓存
        if self.shindan_id not in _SHINDAN_MAKER_CACHE.values():
            shindan_title = await run_sync(parse_shindan_page_title)(content=page_content)
            await self._upgrade_shindan_cache({shindan_title: self.shindan_id})

        # 解析请求参数
        params = await run_sync(parse_shindan_page_token)(content=page_content)
        params.update({'shindanName': input_name})

        cookies = {}
        for k, v in page_response.headers.items():
            if re.match(re.compile('set-cookie', re.IGNORECASE), k):
                item = v.split(';', maxsplit=1)[0].strip().split('=', maxsplit=1)
                if len(item) == 2:
                    cookies.update({item[0]: item[1]})

        response = await OmegaRequests(timeout=10).post(url=query_url, headers=headers, cookies=cookies, data=params)
        if response.status_code != 200:
            logger.error(f'ShindanMaker | Make shindan {self.shindan_id!r} failed, {response}')
            raise ShindanMakerNetworkError(response)

        return await run_sync(parse_shindan_result_page)(content=OmegaRequests.parse_content_text(response=response))

    @classmethod
    async def fuzzy_shindan(cls, shindan: str, input_name: str) -> ShindanMakerResult | None:
        """通过模糊查找进行占卜"""
        if not _SHINDAN_MAKER_CACHE:
            await cls._read_shindan_cache()

        if not _SHINDAN_MAKER_CACHE:
            await cls.complex_ranking()

        choice, similarity, index = process.extractOne(
            query=shindan,
            choices=_SHINDAN_MAKER_CACHE.keys(),
            scorer=fuzz.WRatio
        )

        if similarity < 80:
            await cls.complex_ranking()
            await cls.complex_search(keyword=shindan)
            choice, similarity, index = process.extractOne(
                query=shindan,
                choices=_SHINDAN_MAKER_CACHE.keys(),
                scorer=fuzz.WRatio
            )

        if similarity >= 75:
            shindan_id = list(_SHINDAN_MAKER_CACHE.values())[index]
            logger.debug(f'ShindanMaker | Fuzzy matched shindan {choice!r} id={shindan_id}')
            return await cls(shindan_id=shindan_id).query_shindan_result(input_name=input_name)
        else:
            logger.debug(f'ShindanMaker | None of shindan {shindan!r} fuzzy matched')
            return None

    @staticmethod
    async def download_image(url: str) -> TemporaryResource:
        """下载图片到本地, 保持原始文件名, 直接覆盖同名文件"""
        file_name = OmegaRequests.hash_url_file_name(url=url)
        file = _TMP_FOLDER('image', file_name)
        return await OmegaRequests().download(url=url, file=file)

    @staticmethod
    async def _read_shindan_cache() -> dict[str, int]:
        """从文件中读取占卜名缓存"""
        global _SHINDAN_MAKER_CACHE
        cache_file = _TMP_FOLDER('shindan_maker_cache.json')
        if cache_file.is_file:
            async with cache_file.async_open('r', encoding='utf8') as af:
                data = await af.read()
                if not data:
                    result = {}
                else:
                    result = json.loads(data)
        else:
            result = {}
            async with cache_file.async_open('w', encoding='utf8') as af:
                await af.write(json.dumps(result, ensure_ascii=False))

        _SHINDAN_MAKER_CACHE.update(result)
        return _SHINDAN_MAKER_CACHE

    @staticmethod
    async def _upgrade_shindan_cache(data: dict[str, int]) -> None:
        """更新并写入占卜名缓存到文件"""
        global _SHINDAN_MAKER_CACHE
        cache_file = _TMP_FOLDER('shindan_maker_cache.json')
        exist_data = {}
        if cache_file.is_file:
            async with cache_file.async_open('r', encoding='utf8') as af:
                file_data = await af.read()
                if file_data:
                    exist_data: dict = json.loads(file_data)

        exist_data.update(_SHINDAN_MAKER_CACHE)
        exist_data.update(data)
        exist_data = {k: v for k, v in sorted(exist_data.items(), key=lambda x: x[1])}
        _SHINDAN_MAKER_CACHE.update(exist_data)

        async with cache_file.async_open('w', encoding='utf8') as af:
            await af.write(json.dumps(exist_data, ensure_ascii=False))


__all__ = [
    'ShindanMaker'
]
