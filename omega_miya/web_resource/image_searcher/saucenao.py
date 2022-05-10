"""
@Author         : Ailitonia
@Date           : 2022/05/08 16:23
@FileName       : saucenao.py
@Project        : nonebot2_miya 
@Description    : Saucenao 识图引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional
from pydantic import BaseModel, AnyUrl, parse_obj_as
from nonebot.log import logger

from omega_miya.web_resource import HttpFetcher
from omega_miya.exception import WebSourceException

from .model import ImageSearcher, ImageSearchingResult
from .config import image_searcher_config


_SIMILARITY_THRESHOLD: int = 80
"""搜索结果相似度阈值"""


class SaucenaoApiError(WebSourceException):
    """Saucenao Api 异常"""


class SaucenaoResult(BaseModel):
    """识图结果"""

    class _Result(BaseModel):

        class _Header(BaseModel):
            similarity: float
            thumbnail: Optional[AnyUrl]
            index_name: str

        class _Data(BaseModel):
            ext_urls: Optional[list[AnyUrl]]

        header: _Header
        data: _Data

    results: list[_Result]


class Saucenao(ImageSearcher):
    """Saucenao 识图引擎"""
    _searcher_name: str = 'Saucenao'
    _api: str = 'https://saucenao.com/search.php'

    async def search(self) -> list[ImageSearchingResult]:
        params = {
            'output_type': 2,
            'testmode': 1,
            'numres': 6,
            'db': 999,
            'url': self.image_url
        }
        if image_searcher_config.saucenao_api_key:
            params.update({'api_key': image_searcher_config.saucenao_api_key})

        saucenao_result = await HttpFetcher(timeout=15).get_json_dict(url=self._api, params=params)
        if saucenao_result.status != 200:
            logger.error(f'Saucenao | SaucenaoApiError, {saucenao_result}')
            raise SaucenaoApiError(f'SaucenaoApiError, {saucenao_result}')
        saucenao_result = SaucenaoResult.parse_obj(saucenao_result.result)
        data = ({
            'source': x.header.index_name,
            'source_urls': x.data.ext_urls,
            'similarity': x.header.similarity,
            'thumbnail': x.header.thumbnail
        } for x in saucenao_result.results if x.header.similarity >= _SIMILARITY_THRESHOLD)

        return parse_obj_as(list[ImageSearchingResult], data)


__all__ = [
    'Saucenao'
]
