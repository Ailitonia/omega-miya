"""
@Author         : Ailitonia
@Date           : 2025/4/24 20:47:58
@FileName       : anime_trace.py
@Project        : omega-miya
@Description    : AnimeTrace 识别引擎
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from src.compat import parse_obj_as
from src.resource import BaseResource
from ..config import image_searcher_config
from ..model import BaseImageSearcherAPI, ImageSearchingResult

if TYPE_CHECKING:
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes


class BaseAnimeTraceModel(BaseModel):
    """AnimeTrace 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class AnimeTraceCharacterItem(BaseAnimeTraceModel):
    work: str
    character: str


class AnimeTraceDatum(BaseAnimeTraceModel):
    box: list[float]
    box_id: str
    character: list[AnimeTraceCharacterItem]


class AnimeTraceResult(BaseAnimeTraceModel):
    code: int = Field(default=-1)
    data: list[AnimeTraceDatum] = Field(default_factory=list)
    ai: bool = Field(default=False)
    trace_id: str = Field(default_factory=str)


class AnimeTrace(BaseImageSearcherAPI):
    """AnimeTrace 识图引擎"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://api.animetrace.com/v1/search'

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        return {'User-Agent': 'PostmanRuntime/7.29.0'}

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    @staticmethod
    def _parse_anime_trace_result(anime_trace_result: AnimeTraceResult) -> list[ImageSearchingResult]:
        """解析 AnimeTraceResult 到 ImageSearchingResult"""
        data = (
            {'source': f'{x.character}, 作品：{x.work!r}'}
            for character in anime_trace_result.data
            for x in character.character[:1]
        )
        return parse_obj_as(list[ImageSearchingResult], data)

    @classmethod
    async def _origin_search_local_image(cls, image: 'BaseResource') -> AnimeTraceResult:
        with image.open('rb') as f:
            files = {
                'file': (image.name, f, 'application/octet-stream'),
            }
            data = {
                'is_multi': '1' if image_searcher_config.image_searcher_anime_trace_enable_multi else '0',
                'model': image_searcher_config.image_searcher_anime_trace_default_model,
                'ai_detect': '1' if image_searcher_config.image_searcher_anime_trace_enable_ai_detect else '2',
            }
            result = await cls._post_acquire_as_json(
                url=cls._get_root_url(), data=data, files=files, timeout=20,  # type: ignore
            )

        return AnimeTraceResult.model_validate(result)

    @classmethod
    async def _origin_search_bytes_image(cls, image: bytes) -> AnimeTraceResult:
        files = {
            'file': ('blob', image, 'application/octet-stream'),
        }
        data = {
            'is_multi': '1' if image_searcher_config.image_searcher_anime_trace_enable_multi else '0',
            'model': image_searcher_config.image_searcher_anime_trace_default_model,
            'ai_detect': '1' if image_searcher_config.image_searcher_anime_trace_enable_ai_detect else '2',
        }
        result = await cls._post_acquire_as_json(
            url=cls._get_root_url(), data=data, files=files, timeout=20,  # type: ignore
        )
        return AnimeTraceResult.model_validate(result)

    @classmethod
    async def _origin_search_url_image(cls, image: str) -> AnimeTraceResult:
        image_content = await cls.get_resource_as_bytes(url=image)
        return await cls._origin_search_bytes_image(image=image_content)

    @classmethod
    async def _search_local_image(cls, image: 'BaseResource') -> list[ImageSearchingResult]:
        return cls._parse_anime_trace_result(await cls._origin_search_local_image(image=image))

    @classmethod
    async def _search_bytes_image(cls, image: bytes) -> list[ImageSearchingResult]:
        return cls._parse_anime_trace_result(await cls._origin_search_bytes_image(image=image))

    @classmethod
    async def _search_url_image(cls, image: str) -> list[ImageSearchingResult]:
        image_content = await cls.get_resource_as_bytes(url=image)
        return await cls._search_bytes_image(image=image_content)

    async def origin_search(self) -> AnimeTraceResult:
        """根据提供的图片类型获取搜索结果"""
        if isinstance(self.image, BaseResource):
            return await self._origin_search_local_image(image=self.image)
        elif isinstance(self.image, bytes):
            return await self._origin_search_bytes_image(image=self.image)
        else:
            return await self._origin_search_url_image(image=self.image)  # type: ignore


__all__ = [
    'AnimeTrace',
]
