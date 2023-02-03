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

from src.service.omega_requests import OmegaRequests
from src.exception import WebSourceException

from .model import ImageSearcher, ImageSearchingResult
from .config import image_searcher_config


_SIMILARITY_THRESHOLD: int = 60
"""搜索结果相似度阈值"""


class SaucenaoApiError(WebSourceException):
    """Saucenao Api 异常"""


class SaucenaoResult(BaseModel):
    """识图结果"""

    class _Result(BaseModel):

        class _Header(BaseModel):
            similarity: float
            thumbnail: Optional[AnyUrl]
            index_id: int
            index_name: str

        class _BaseData(BaseModel):
            ext_urls: Optional[list[AnyUrl]]

            @property
            def data_text(self) -> str:
                """输出可读的来源结果信息"""
                raise NotImplementedError

        class _NullData(_BaseData):
            """默认无解析的结果类"""
            @property
            def data_text(self) -> str:
                return ''

        class _DefaultData(_BaseData):
            author_name: Optional[str]
            author_url: Optional[str]
            creator: str
            creator_name: str

            @property
            def data_text(self) -> str:
                return f'Creator: {self.creator}/{self.creator_name}\n' \
                       f'Author: {self.author_name}\nAuthor Url: {self.author_url}'

        class _TitleAuthorData(_BaseData):
            author_name: str
            author_url: str
            title: str

            @property
            def data_text(self) -> str:
                return f'Title: {self.title}\nAuthor: {self.author_name}\nAuthor Url: {self.author_url}'

        class _PixivData(_BaseData):
            pixiv_id: int
            title: str
            member_id: int
            member_name: str

            @property
            def data_text(self) -> str:
                return f'【Pixiv Artwork】\nTitle: {self.title}\nPid: {self.pixiv_id}\nAuthor: {self.member_name}'

        class _PawooData(_BaseData):
            pawoo_id: int
            pawoo_user_acct: str
            pawoo_user_display_name: str
            pawoo_user_username: str
            created_at: str

            @property
            def data_text(self) -> str:
                return f'【Pawoo】\nUser: {self.pawoo_user_username}/{self.pawoo_user_display_name}\n' \
                       f'Pawoo id: {self.pawoo_id}'

        class _NicoData(_BaseData):
            seiga_id: int
            title: str
            member_id: int
            member_name: str

            @property
            def data_text(self) -> str:
                return f'【Nico Nico Seiga】\nTitle: {self.title}\nSeiga id: {self.seiga_id}\nAuthor: {self.member_name}'

        class _TwitterData(_BaseData):
            tweet_id: int
            twitter_user_handle: str
            twitter_user_id: int
            created_at: str

            @property
            def data_text(self) -> str:
                return f'【Twitter】\nUser: {self.twitter_user_handle}\nTweet id: {self.tweet_id}'

        class _AnimeData(_BaseData):
            anidb_aid: int
            anilist_id: int
            est_time: str
            source: str
            part: str
            year: str

            @property
            def data_text(self) -> str:
                return f'【Anime】\nSource: [{self.year}]{self.source}(part: {self.part})\nEst time: {self.est_time}'

        class _EHData(_BaseData):
            source: str
            jp_name: str
            eng_name: str

            @property
            def data_text(self) -> str:
                text = f'【EH】\nSource: {self.source}'
                text += f'\nJP name: {self.jp_name}'
                text += f'\nENG name: {self.eng_name}'
                return text

        header: _Header
        data: (_AnimeData |
               _TwitterData |
               _NicoData |
               _PawooData |
               _PixivData |
               _EHData |
               _TitleAuthorData |
               _DefaultData |
               _NullData)

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

        saucenao_response = await OmegaRequests(timeout=15).get(url=self._api, params=params)
        if saucenao_response.status_code != 200:
            logger.error(f'Saucenao | SaucenaoApiError, {saucenao_response}')
            raise SaucenaoApiError(f'{saucenao_response.request}, status code {saucenao_response.status_code}')

        saucenao_result = SaucenaoResult.parse_obj(OmegaRequests.parse_content_json(saucenao_response))
        data = (
            {
                'source': f'{x.header.index_name}\n{x.data.data_text}',
                'source_urls': x.data.ext_urls,
                'similarity': x.header.similarity,
                'thumbnail': x.header.thumbnail
            }
            for x in saucenao_result.results if x.header.similarity >= _SIMILARITY_THRESHOLD
        )

        return parse_obj_as(list[ImageSearchingResult], data)


__all__ = [
    'Saucenao'
]
