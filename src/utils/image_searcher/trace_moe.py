"""
@Author         : Ailitonia
@Date           : 2022/05/08 20:30
@FileName       : trace_moe.py
@Project        : nonebot2_miya 
@Description    : trace.moe 识番引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


from typing import Optional
from pydantic import BaseModel, Field, AnyUrl, parse_obj_as
from nonebot.log import logger

from src.exception import WebSourceException
from src.service import OmegaRequests
from src.utils.process_utils import semaphore_gather

from .model import ImageSearcher, ImageSearchingResult


_SIMILARITY_THRESHOLD: float = 0.8
"""搜索结果相似度阈值"""


class TraceMoeApiError(WebSourceException):
    """TraceMoe Api 异常"""


class AnilistApiError(WebSourceException):
    """Anilist Api 异常"""


class TraceMoeResults(BaseModel):
    anilist: int
    filename: str
    episode: int | None
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
                romaji: Optional[str]
                english: Optional[str]
                chinese: Optional[str]

            id: int
            title: _Title
            isAdult: bool
            synonyms: list[str]

        Media: _Media

    data: _Data

    @property
    def media(self):
        return self.data.Media


class TraceMoe(ImageSearcher):
    """trace.moe 识图引擎"""
    _searcher_name: str = 'trace.moe'
    _api = 'https://api.trace.moe/search'
    """trace.moe API"""
    _anilist_api = 'https://graphql.anilist.co'
    """Anilist API"""
    _anilist_api_cn = 'https://trace.moe/anilist/'
    """中文 Anilist API"""
    _anilist_api_query = r'''
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
    """Anilist API 请求内容"""

    async def _handel_anilist_result(self, data: TraceMoeResults) -> ImageSearchingResult:
        headers = OmegaRequests.get_default_headers()
        headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3;q=0.9'
        })
        params = {'query': self._anilist_api_query, 'variables': {'id': data.anilist}}
        anilist_response = await OmegaRequests(headers=headers, timeout=15).post(url=self._anilist_api_cn, json=params)
        if anilist_response.status_code != 200:
            logger.error(f'TraceMoe | AnilistApiError, {anilist_response}')
            raise AnilistApiError(f'{anilist_response.request}, status code {anilist_response.status_code}')

        anilist_data = AnilistResult.parse_obj(OmegaRequests.parse_content_json(anilist_response))
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
        headers = OmegaRequests.get_default_headers()
        headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3;q=0.9'
        })
        params = {'url': self.image_url}
        tracemoe_response = await OmegaRequests(headers=headers, timeout=15).get(url=self._api, params=params)
        if tracemoe_response.status_code != 200:
            logger.error(f'TraceMoe | TraceMoeApiError, {tracemoe_response}')
            raise TraceMoeApiError(f'{tracemoe_response.request}, status code {tracemoe_response.status_code}')

        tracemoe_result = TraceMoeResult.parse_obj(OmegaRequests.parse_content_json(tracemoe_response))

        anilist_tasks = [
            self._handel_anilist_result(data=x)
            for x in tracemoe_result.result
            if x.similarity >= _SIMILARITY_THRESHOLD
        ]
        anilist_result = await semaphore_gather(tasks=anilist_tasks, semaphore_num=5, return_exceptions=False)

        return parse_obj_as(list[ImageSearchingResult], anilist_result)


__all__ = [
    'TraceMoe'
]
