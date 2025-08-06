"""
@Author         : Ailitonia
@Date           : 2022/05/08 20:30
@FileName       : trace_moe.py
@Project        : nonebot2_miya
@Description    : trace.moe 识番引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Iterable
from typing import TYPE_CHECKING, ClassVar

from pydantic import BaseModel, Field

from src.compat import AnyUrlStr as AnyUrl
from ..model import BaseImageSearcherAPI, ImageSearchingResult

if TYPE_CHECKING:
    from src.resource import BaseResource
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes


class TraceMoeResults(BaseModel):
    anilist: int
    filename: str
    episode: int | list[int] | None = Field(default=None)
    from_: float = Field(alias='from')
    to: float
    similarity: float
    video: AnyUrl
    image: AnyUrl


class TraceMoeResult(BaseModel):
    """trace.moe 识别结果"""
    frameCount: int
    error: str
    result: list[TraceMoeResults]


class AnilistTitle(BaseModel):
    native: str
    romaji: str | None = None
    english: str | None = None
    chinese: str | None = None


class AnilistCoverImage(BaseModel):
    large: AnyUrl | None = None
    medium: AnyUrl | None = None


class AnilistMedia(BaseModel):
    id: int
    title: AnilistTitle
    type: str
    format: str
    status: str
    season: str | None = Field(default=None)
    episodes: int | list[int] | None = Field(default=None)
    duration: int | list[int] | None = Field(default=None)
    source: str
    bannerImage: AnyUrl | None = None
    coverImage: AnilistCoverImage
    synonyms: list[str] = Field(default_factory=list)
    isAdult: bool
    siteUrl: AnyUrl


class AnilistPage(BaseModel):
    media: list[AnilistMedia]


class AnilistMultiData(BaseModel):
    Page: AnilistPage


class AnilistSingleData(BaseModel):
    Media: AnilistMedia


class AnilistMultiResult(BaseModel):
    """Anilist 多页结果内容"""
    data: AnilistMultiData

    @property
    def media(self) -> list[AnilistMedia]:
        return self.data.Page.media


class AnilistSingleResult(BaseModel):
    """Anilist 单作品查询结果内容"""
    data: AnilistSingleData

    @property
    def media(self) -> AnilistMedia:
        return self.data.Media


class TraceMoe(BaseImageSearcherAPI):
    """trace.moe 识图引擎"""

    _similarity_threshold: ClassVar[float] = 0.8
    """搜索结果相似度阈值"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://api.trace.moe'

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3;q=0.9'
        })
        return headers

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    @classmethod
    def get_api_url(cls) -> str:
        """trace.moe API"""
        return f'{cls._get_root_url()}/search'

    @classmethod
    def _get_anilist_api(cls) -> str:
        """Anilist API"""
        return 'https://graphql.anilist.co'

    @classmethod
    def _get_anilist_api_cn(cls) -> str:
        """中文 Anilist API"""
        return 'https://trace.moe/anilist'

    @classmethod
    def _get_anilist_api_single_query(cls) -> str:
        """Anilist API 单个作品请求内容"""

        return r"""
        query ($id: Int) { # Define which variables will be used in the query (id)
          Media (id: $id, type: ANIME) { # Insert our variables into the query arguments (id) (type: ANIME is hard-coded in the query)
            id # you must query the id field for it to search the translated database
            title {
              native # do not query chinese here, the official Anilist API doesn't recognize
              romaji
              english
            }
            type
            format
            status
            season
            episodes
            duration
            source
            coverImage {
              large
              medium
            }
            synonyms # chinese titles will always be merged into this array
            isAdult
            siteUrl
          }
        }
        """

    @classmethod
    def _get_anilist_api_multi_query(cls) -> str:
        """Anilist API 多个作品请求内容"""

        return r"""
        query ($ids: [Int]) { # Define which variables will be used in the query (ids)
          Page(page: 1, perPage: 50) {
            media(id_in: $ids, type: ANIME) {
              id
              title {
                native # do not query chinese here, the official Anilist API doesn't recognize
                romaji
                english
              }
              type
              format
              status
              season
              episodes
              duration
              source
              coverImage {
                large
                medium
              }
              synonyms # chinese titles will always be merged into this array
              isAdult
              siteUrl
            }
          }
        }
        """

    @classmethod
    async def _query_anilist_result(cls, anilist_id: int | str) -> AnilistSingleResult:
        """查询单个作品的 anilist 数据"""
        params = {'query': cls._get_anilist_api_single_query(), 'variables': {'id': str(anilist_id)}}
        return AnilistSingleResult.model_validate(await cls._post_json(url=cls._get_anilist_api_cn(), json=params))

    @classmethod
    async def _query_anilist_multi_result(cls, anilist_ids: Iterable[int | str]) -> AnilistMultiResult:
        """查询多个作品的 anilist 数据"""
        params = {'query': cls._get_anilist_api_multi_query(), 'variables': {'ids': [str(x) for x in anilist_ids]}}
        return AnilistMultiResult.model_validate(await cls._post_json(url=cls._get_anilist_api_cn(), json=params))

    @classmethod
    async def _handel_anilist_result(cls, data: Iterable[TraceMoeResults]) -> list[ImageSearchingResult]:
        """获取 anilist 数据"""
        anilist_data = await cls._query_anilist_multi_result(anilist_ids=[x.anilist for x in data])

        return [
            ImageSearchingResult(
                source=(f'trace.moe & Anilist 数据库\n'
                        f'名称: {media.title.native}\n'
                        f'{f"中文名称: {media.title.chinese}\n" if media.title.chinese else ""}'
                        f'类型: {media.type}-{media.format}-{media.source}\n'
                        f'集/季/Episode: {x.episode}({x.from_}-{x.to})\n'
                        f'NSFW: {media.isAdult}'),
                source_urls=[media.siteUrl],
                thumbnail=x.image,
                similarity=str(int(x.similarity * 100))
            )
            for x in data if x.similarity >= cls._similarity_threshold
            for media in anilist_data.media if x.anilist == media.id
        ]

    @classmethod
    async def _search_local_image(cls, image: 'BaseResource') -> list[ImageSearchingResult]:
        with image.open('rb') as f:
            files = {
                'file': (image.name, f, 'application/octet-stream'),
            }
            result = await cls._post_json(url=cls.get_api_url(), files=files)  # type: ignore

        return await cls._handel_anilist_result(data=TraceMoeResult.model_validate(result).result)

    @classmethod
    async def _search_bytes_image(cls, image: bytes) -> list[ImageSearchingResult]:
        files = {
            'file': ('blob', image, 'application/octet-stream'),
        }
        result = await cls._post_json(url=cls.get_api_url(), files=files)  # type: ignore

        return await cls._handel_anilist_result(data=TraceMoeResult.model_validate(result).result)

    @classmethod
    async def _search_url_image(cls, image: str) -> list[ImageSearchingResult]:
        params = {'url': image}
        tracemoe_result = TraceMoeResult.model_validate(await cls._get_json(url=cls.get_api_url(), params=params))
        return await cls._handel_anilist_result(data=tracemoe_result.result)


__all__ = [
    'TraceMoe',
]
