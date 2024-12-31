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

from pydantic import BaseModel, ConfigDict

from src.compat import AnyUrlStr as AnyUrl
from src.utils import BaseCommonAPI

if TYPE_CHECKING:
    from nonebot.internal.driver import QueryTypes


class ImageSearchingResult(BaseModel):
    """识图结果"""
    source: str  # 来源说明
    source_urls: list[AnyUrl] | None = None  # 来源地址
    similarity: str | None = None  # 相似度
    thumbnail: AnyUrl | None = None  # 缩略图地址

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class BaseImageSearcher(abc.ABC):
    """识图引擎基类"""

    def __init__(self, image_url: str):
        """仅支持传入图片 url

        :param image_url: 待识别的图片 url
        """
        self.image_url = image_url

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(image_url={self.image_url})'

    @abc.abstractmethod
    async def search(self) -> list[ImageSearchingResult]:
        """获取搜索结果"""
        raise NotImplementedError


class BaseImageSearcherAPI(BaseImageSearcher, BaseCommonAPI, abc.ABC):
    """识图引擎 API 基类"""

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

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
]
