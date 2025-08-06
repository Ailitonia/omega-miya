"""
@Author         : Ailitonia
@Date           : 2022/05/08 16:23
@FileName       : saucenao.py
@Project        : nonebot2_miya
@Description    : Saucenao 识图引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from src.compat import AnyUrlStr as AnyUrl
from src.compat import parse_obj_as
from ..config import image_searcher_config
from ..model import BaseImageSearcherAPI, ImageSearchingResult

if TYPE_CHECKING:
    from src.resource import BaseResource
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes


class BaseSaucenaoModel(BaseModel):
    """Saucenao 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class SaucenaoResult(BaseSaucenaoModel):
    """识图结果"""

    class _GlobalStatusHeader(BaseSaucenaoModel):
        user_id: str
        account_type: str
        short_limit: int
        short_remaining: int
        long_limit: int
        long_remaining: int
        status: int
        results_requested: int
        message: str | None = None

    class _Result(BaseSaucenaoModel):

        class _Header(BaseSaucenaoModel):
            similarity: float
            thumbnail: AnyUrl | None = None
            index_id: int
            index_name: str

        class _BaseData(BaseSaucenaoModel):
            ext_urls: list[AnyUrl] = Field(default_factory=list)

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
            author_name: str | None = None
            author_url: str | None = None
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
        data: (
                _AnimeData
                | _TwitterData
                | _NicoData
                | _PawooData
                | _PixivData
                | _EHData
                | _TitleAuthorData
                | _DefaultData
                | _NullData
        )

    header: _GlobalStatusHeader
    results: list[_Result] = Field(default_factory=list)


class Saucenao(BaseImageSearcherAPI):
    """Saucenao 识图引擎"""

    _similarity_threshold: ClassVar[int] = 60
    """搜索结果相似度阈值"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://saucenao.com'

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'PostmanRuntime/7.29.0'}

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    @classmethod
    def get_api_url(cls) -> str:
        return f'{cls._get_root_url()}/search.php'

    @classmethod
    def _parse_saucenao_result(cls, saucenao_result: SaucenaoResult) -> list[ImageSearchingResult]:
        """解析 SaucenaoResult 到 ImageSearchingResult"""
        data = (
            {
                'source': f'{x.header.index_name}\n{x.data.data_text}',
                'source_urls': x.data.ext_urls,
                'similarity': x.header.similarity,
                'thumbnail': x.header.thumbnail
            }
            for x in saucenao_result.results if x.header.similarity >= cls._similarity_threshold
        )

        return parse_obj_as(list[ImageSearchingResult], data)

    @classmethod
    async def _search_local_image(cls, image: 'BaseResource') -> list[ImageSearchingResult]:
        with image.open('rb') as f:
            files = {
                'file': (image.name, f, 'application/octet-stream'),
            }
            params = {
                'output_type': '2',
                'numres': '6',
                'db': '999',
            }
            if image_searcher_config.image_searcher_saucenao_api_key:
                params.update({'api_key': image_searcher_config.image_searcher_saucenao_api_key})

            result = await cls._post_json(cls.get_api_url(), params=params, files=files)  # type: ignore

        return cls._parse_saucenao_result(saucenao_result=SaucenaoResult.model_validate(result))

    @classmethod
    async def _search_bytes_image(cls, image: bytes) -> list[ImageSearchingResult]:
        files = {
            'file': ('blob', image, 'application/octet-stream'),
        }
        params = {
            'output_type': '2',
            'numres': '6',
            'db': '999',
        }
        if image_searcher_config.image_searcher_saucenao_api_key:
            params.update({'api_key': image_searcher_config.image_searcher_saucenao_api_key})

        result = await cls._post_json(cls.get_api_url(), params=params, files=files)  # type: ignore
        return cls._parse_saucenao_result(saucenao_result=SaucenaoResult.model_validate(result))

    @classmethod
    async def _search_url_image(cls, image: str) -> list[ImageSearchingResult]:
        params = {
            'output_type': '2',
            'numres': '6',
            'db': '999',
            'url': image,
        }
        if image_searcher_config.image_searcher_saucenao_api_key:
            params.update({'api_key': image_searcher_config.image_searcher_saucenao_api_key})

        result = await cls._get_json(cls.get_api_url(), params=params)
        return cls._parse_saucenao_result(saucenao_result=SaucenaoResult.model_validate(result))


__all__ = [
    'Saucenao',
]
