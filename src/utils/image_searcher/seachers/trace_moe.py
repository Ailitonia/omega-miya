"""
@Author         : Ailitonia
@Date           : 2022/05/08 20:30
@FileName       : trace_moe.py
@Project        : nonebot2_miya 
@Description    : trace.moe 识番引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from src.compat import AnyUrlStr as AnyUrl, parse_obj_as
from src.utils.process_utils import semaphore_gather
from ..model import BaseImageSearcherAPI, ImageSearchingResult

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes, HeaderTypes


class TraceMoeResults(BaseModel):
    anilist: int
    filename: str
    episode: int | None = None
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


class AnilistResult(BaseModel):
    """Anilist 内容"""

    class _Data(BaseModel):

        class _Media(BaseModel):

            class _Title(BaseModel):
                native: str
                romaji: Optional[str] = None
                english: Optional[str] = None
                chinese: Optional[str] = None

            id: int
            title: _Title
            isAdult: bool
            synonyms: list[str]

        Media: _Media

    data: _Data

    @property
    def media(self):
        return self.data.Media


class TraceMoe(BaseImageSearcherAPI):
    """trace.moe 识图引擎"""

    _similarity_threshold: float = 0.8
    """搜索结果相似度阈值"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://api.trace.moe'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _get_default_headers(cls) -> "HeaderTypes":
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3;q=0.9'
        })
        return headers

    @classmethod
    def _get_default_cookies(cls) -> "CookieTypes":
        return None

    @property
    def api_url(self) -> str:
        """trace.moe API"""
        return f'{self._get_root_url()}/search'

    @property
    def anilist_api(self) -> str:
        """Anilist API"""
        return 'https://graphql.anilist.co'

    @property
    def anilist_api_cn(self) -> str:
        """中文 Anilist API"""
        return 'https://trace.moe/anilist'

    @property
    def anilist_api_query(self) -> str:
        """Anilist API 请求内容"""

        return r'''
        query ($id: Int) { # Define which variables will be used in the query (id)
          Media (id: $id, type: ANIME) { # Insert our variables into the query arguments (id) (type: ANIME is hard-coded in the query)
            id # you must query the id field for it to search the translated database
            title {
              native # do not query chinese here, the official Anilist API doesn't recognize
              romaji
              english
            }
            isAdult
            synonyms # chinese titles will always be merged into this array
          }
        }
        '''

    async def _handel_anilist_result(self, data: TraceMoeResults) -> ImageSearchingResult:
        """获取 anilist 数据"""
        params = {'query': self.anilist_api_query, 'variables': {'id': data.anilist}}
        anilist_data = AnilistResult.model_validate(await self._post_json(url=self.anilist_api_cn, json=params))

        source = f'trace.moe & Anilist 数据库\n' \
                 f'原始名称: {anilist_data.media.title.native}\n' \
                 f'中文名称: {anilist_data.media.title.chinese}\n' \
                 f'来源文件: {data.filename}\n' \
                 f'集/季/Episode: {data.episode}\n' \
                 f'预览图时间位置: {data.from_} - {data.to}\n' \
                 f'绅士: {anilist_data.media.isAdult}'
        similarity = str(int(data.similarity * 100))
        return ImageSearchingResult(source=source, source_urls=None, similarity=similarity, thumbnail=data.image)

    async def search(self) -> list[ImageSearchingResult]:
        params = {'url': self.image_url}
        tracemoe_result = TraceMoeResult.model_validate(await self._get_json(url=self.api_url, params=params))

        anilist_tasks = [
            self._handel_anilist_result(data=x)
            for x in tracemoe_result.result
            if x.similarity >= self._similarity_threshold
        ]
        anilist_result = await semaphore_gather(tasks=anilist_tasks, semaphore_num=5, return_exceptions=False)

        return parse_obj_as(list[ImageSearchingResult], anilist_result)


__all__ = [
    'TraceMoe',
]
