"""
@Author         : Ailitonia
@Date           : 2022/05/08 15:50
@FileName       : model.py
@Project        : nonebot2_miya
@Description    : Image Searcher Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from src.compat import AnyUrlStr as AnyUrl
from src.resource import BaseResource
from src.utils import BaseCommonAPI

if TYPE_CHECKING:
    from src.utils.omega_common_api.types import QueryTypes

type SearchableImage = BaseResource | bytes | str


class ImageSearchingResult(BaseModel):
    """识图结果"""
    source: str  # 来源说明
    source_urls: list[AnyUrl] = Field(default_factory=list)  # 来源地址
    similarity: str | None = Field(default=None)  # 相似度
    thumbnail: AnyUrl | None = Field(default=None)  # 缩略图地址

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class BaseImageSearcher(abc.ABC):
    """识图引擎基类"""

    def __init__(self, image: SearchableImage):
        """仅支持传入图片 url

        :param image: 待识别的图片
        """
        self.image = image

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(image={self.image})'

    @classmethod
    @abc.abstractmethod
    async def _search_local_image(cls, image: BaseResource) -> list[ImageSearchingResult]:
        """识别本地图片"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _search_bytes_image(cls, image: bytes) -> list[ImageSearchingResult]:
        """识别 bytes 图片"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def _search_url_image(cls, image: str) -> list[ImageSearchingResult]:
        """识别 url 图片"""
        raise NotImplementedError

    async def search(self) -> list[ImageSearchingResult]:
        """根据提供的图片类型获取搜索结果"""
        if isinstance(self.image, BaseResource):
            return await self._search_local_image(image=self.image)
        elif isinstance(self.image, bytes):
            return await self._search_bytes_image(image=self.image)
        else:
            return await self._search_url_image(image=self.image)  # type: ignore


class BaseImageSearcherAPI(BaseImageSearcher, BaseCommonAPI, abc.ABC):
    """识图引擎 API 基类"""

    @classmethod
    def get_searcher_name(cls) -> str:
        """获取识图引擎名称"""
        return cls.__name__.lower()

    @classmethod
    async def get_resource_as_bytes(cls, url: str, *, params: 'QueryTypes' = None, timeout: int = 30) -> bytes:
        """请求原始资源内容"""
        return await cls._get_resource_as_bytes(url, params, timeout=timeout)

    @classmethod
    async def get_resource_as_text(cls, url: str, *, params: 'QueryTypes' = None, timeout: int = 10) -> str:
        """请求原始资源内容"""
        return await cls._get_resource_as_text(url, params, timeout=timeout)


__all__ = [
    'BaseImageSearcher',
    'BaseImageSearcherAPI',
    'ImageSearchingResult',
    'SearchableImage',
]
