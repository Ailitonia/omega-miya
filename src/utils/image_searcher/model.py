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
from typing import Optional
from pydantic import BaseModel, ConfigDict

from src.compat import AnyUrlStr as AnyUrl


class ImageSearchingResult(BaseModel):
    """识图结果"""
    source: str  # 来源说明
    source_urls: Optional[list[AnyUrl]] = None  # 来源地址
    similarity: Optional[str] = None  # 相似度
    thumbnail: Optional[AnyUrl] = None  # 缩略图地址

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class ImageSearcher(abc.ABC):
    """识图引擎基类"""
    _searcher_name: str = 'abc_searcher'

    def __init__(self, image_url: str):
        """仅支持传入图片 url

        :param image_url: 待识别的图片 url
        """
        self.image_url = image_url

    def __repr__(self) -> str:
        return f'ImageSearcher(name={self._searcher_name.upper()}, image_url={self.image_url})'

    @abc.abstractmethod
    async def search(self) -> list[ImageSearchingResult]:
        """获取搜索结果"""
        raise NotImplementedError


__all__ = [
    'ImageSearchingResult',
    'ImageSearcher'
]
