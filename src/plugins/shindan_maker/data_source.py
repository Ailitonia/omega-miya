"""
@Author         : Ailitonia
@Date           : 2021/06/28 21:42
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : shindan maker data source
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import itertools
import re
from copy import deepcopy
from typing import TYPE_CHECKING, Literal, Optional

from nonebot.log import logger
from pydantic import ValidationError
from rapidfuzz import process, fuzz
from zhconv import convert as zh_convert

from src.compat import parse_json_as, dump_json_as
from src.resource import TemporaryResource
from src.utils.common_api import BaseCommonAPI
from src.utils.process_utils import semaphore_gather
from .config import shindan_maker_plugin_config
from .helper import (
    parse_searching_result_page,
    parse_shindan_page_title,
    parse_shindan_page_token,
    parse_shindan_result_page
)

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes
    from .model import ShindanMakerResult, ShindanMakerSearchResult

_SHINDAN_CACHE: dict[str, int] = {}
"""实时缓存占卜名称与对应id"""
_TMP_FOLDER: TemporaryResource = TemporaryResource('shindan_maker')
"""缓存路径"""
_SHINDAN_CACHE_FILE: TemporaryResource = _TMP_FOLDER('shindan_maker_cache.json')
"""占卜名称与对应id的缓存文件"""


class ShindanMaker(BaseCommonAPI):
    """ShindanMaker 占卜生成"""

    def __init__(self, shindan_id: int):
        self.shindan_id = shindan_id

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(shindan_id={self.shindan_id})'

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        match shindan_maker_plugin_config.shindan_maker_plugin_domain_version:
            case 'cn':
                return 'https://cn.shindanmaker.com'
            case 'default' | _:
                return 'https://shindanmaker.com'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> dict[str, str]:
        return {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'}

    @classmethod
    def _get_default_cookies(cls) -> "CookieTypes":
        return None

    @classmethod
    async def download_resource(
            cls,
            url: str,
            *,
            custom_file_name: Optional[str] = None,
            subdir: str | None = None,
    ) -> TemporaryResource:
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=_TMP_FOLDER,
            url=url,
            subdir=subdir,
            custom_file_name=custom_file_name,
        )

    @classmethod
    async def _load_shindan_cache(cls) -> None:
        """从文件中读取并更新占卜名缓存"""
        global _SHINDAN_CACHE
        if _SHINDAN_CACHE_FILE.is_file:
            try:
                async with _SHINDAN_CACHE_FILE.async_open('r', encoding='utf8') as af:
                    cache_data = parse_json_as(dict[str, int], await af.read())
                    _SHINDAN_CACHE.update(cache_data)
                logger.debug(f'ShindanMaker | loaded shindan cache from {_SHINDAN_CACHE_FILE!r}')
            except ValidationError as e:
                logger.warning(f'ShindanMaker | Parsing shindan cache file failed, {e!r}')

    @classmethod
    async def _read_shindan_cache(cls) -> dict[str, int]:
        """读取占卜名缓存"""
        if not _SHINDAN_CACHE:
            await cls._load_shindan_cache()
        return deepcopy(_SHINDAN_CACHE)

    @classmethod
    async def _upgrade_shindan_cache(cls, data: dict[str, int]) -> None:
        """更新并写入占卜名缓存到文件"""
        global _SHINDAN_CACHE
        await cls._load_shindan_cache()

        _SHINDAN_CACHE.update(data)
        output_data = {k: v for k, v in sorted(_SHINDAN_CACHE.items(), key=lambda x: x[1])}

        async with _SHINDAN_CACHE_FILE.async_open('w', encoding='utf8') as af:
            await af.write(dump_json_as(dict[str, int], output_data))
        logger.debug(f'ShindanMaker | Upgraded shindan cache with {data}')

    @classmethod
    async def ranking_list(
            cls,
            mode: Optional[Literal['pickup', 'latest', 'daily', 'monthly', 'favorite', 'favhot', 'overall']] = None
    ) -> list["ShindanMakerSearchResult"]:
        """列出占卜排行榜

        :param mode: 排序方式, 默认: 按热度, pickup: 最新热度, latest: 最新添加, daily: 每日排名, monthly: 每月排名, favorite: 收藏数, favhot: 最新收藏, overall: 综合
        """
        url = f'{cls._get_root_url()}/list'
        if mode is not None:
            url += f'/{mode}'

        return await parse_searching_result_page(content=await cls._get_resource_as_text(url=url))

    @classmethod
    async def search(
            cls,
            keyword: str,
            *,
            mode: Literal['search', 'themes'] = 'search',
            last_number: Optional[int] = None,
            page: Optional[int] = None,
            order: Optional[Literal['popular', 'favorites']] = None

    ) -> list["ShindanMakerSearchResult"]:
        """搜索占卜

        :param keyword: 搜索关键词
        :param mode: 搜索模式, search: 关键词搜索, themes: 主题或 tag 搜索
        :param last_number: 用途未知
        :param page: 搜索页码
        :param order: 排序方式, 默认: 按时间, popular: 按人气, favorites: 按收藏数
        """
        search_url = f'{cls._get_root_url()}/list/{mode}'
        params = {'q': keyword}
        if last_number is not None:
            params.update({'lastnumber': str(last_number)})
        if page is not None:
            params.update({'page': str(page)})
        if order is not None:
            params.update({'order': order})

        return await parse_searching_result_page(content=await cls._get_resource_as_text(url=search_url, params=params))

    @classmethod
    async def complex_ranking(cls) -> list["ShindanMakerSearchResult"]:
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

        result = [x for x in itertools.chain(*searching_results_group)]

        await cls._upgrade_shindan_cache(data={item.name: item.id for item in result})
        return result

    @classmethod
    async def complex_search(cls, keyword: str) -> list["ShindanMakerSearchResult"]:
        """搜索更多的占卜"""
        keyword_ht = zh_convert(keyword, 'zh-hant')

        search_coro_list = [
            (
                cls.search(keyword=kw, page=page),
                cls.search(keyword=kw, page=page, order='popular'),
                cls.search(keyword=kw, page=page, order='favorites')
            )
            for page in range(1, 3) for kw in [keyword, keyword_ht]
        ]
        searching_tasks = [x for x in itertools.chain(*search_coro_list)]
        searching_results_group = await semaphore_gather(tasks=searching_tasks, semaphore_num=6, filter_exception=True)

        result = [x for x in itertools.chain(*searching_results_group)]

        await cls._upgrade_shindan_cache(data={item.name: item.id for item in result})
        return result

    async def query_shindan_result(self, input_name: str) -> "ShindanMakerResult":
        """获取占卜结果

        :param input_name: 占卜对象名称
        """
        query_url = f'{self._get_root_url()}/{self.shindan_id}'

        page_response = await self._request_get(url=query_url)
        page_content = self._parse_content_as_text(response=page_response)

        headers = self._get_default_headers()
        headers.update({
            'cache-control': 'max-age=0',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': self._get_root_url(),
            'referer': query_url,
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1'
        })

        # 更新缓存
        if self.shindan_id not in _SHINDAN_CACHE.values():
            shindan_title = await parse_shindan_page_title(content=page_content)
            await self._upgrade_shindan_cache({shindan_title: self.shindan_id})

        # 解析请求参数
        params = await parse_shindan_page_token(content=page_content)
        params.update({'shindanName': input_name})

        cookies = {}
        for k, v in page_response.headers.items():
            if re.match(re.compile('set-cookie', re.IGNORECASE), k):
                item = v.split(';', maxsplit=1)[0].strip().split('=', maxsplit=1)
                if len(item) == 2:
                    cookies.update({item[0]: item[1]})

        response = await self._request_post(url=query_url, headers=headers, cookies=cookies, data=params)
        return await parse_shindan_result_page(content=self._parse_content_as_text(response=response))

    @classmethod
    async def fuzzy_shindan(cls, shindan: str, input_name: str) -> Optional["ShindanMakerResult"]:
        """通过模糊查找进行占卜"""
        if not _SHINDAN_CACHE:
            await cls._read_shindan_cache()

        if not _SHINDAN_CACHE:
            await cls.complex_ranking()

        choice, similarity, index = process.extractOne(
            query=shindan,
            choices=_SHINDAN_CACHE.keys(),
            scorer=fuzz.WRatio
        )

        if similarity < 80:
            await cls.complex_ranking()
            await cls.complex_search(keyword=shindan)
            choice, similarity, index = process.extractOne(
                query=shindan,
                choices=_SHINDAN_CACHE.keys(),
                scorer=fuzz.WRatio
            )

        if similarity >= 75:
            shindan_id = list(_SHINDAN_CACHE.values())[index]
            logger.debug(f'ShindanMaker | Fuzzy matched shindan {choice!r} id={shindan_id}')
            return await cls(shindan_id=shindan_id).query_shindan_result(input_name=input_name)
        else:
            logger.debug(f'ShindanMaker | None of shindan {shindan!r} fuzzy matched')
            return None


__all__ = [
    'ShindanMaker',
]
