"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:53
@FileName       : searching.py
@Project        : nonebot2_miya 
@Description    : Pixiv Searching Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import AnyHttpUrl
from typing import Optional
from .base_model import BasePixivModel


class PixivSearchingData(BasePixivModel):
    id: int
    title: str
    userId: int
    userName: str
    xRestrict: int
    pageCount: int
    width: int
    height: int
    url: AnyHttpUrl
    tags: list[str]


class PixivSearchingContent(BasePixivModel):
    """Pixiv 搜索结果汇总"""
    data: list[PixivSearchingData]
    total: int


class PixivSearchingResultBody(BasePixivModel):
    """Pixiv 搜索结果 body"""
    illustManga: Optional[PixivSearchingContent]
    illust: Optional[PixivSearchingContent]
    manga: Optional[PixivSearchingContent]
    popular: dict
    extraData: dict


class PixivSearchingResultModel(BasePixivModel):
    """Pixiv 搜索结果 Model"""
    body: PixivSearchingResultBody | list[None]
    error: bool

    @property
    def searching_result(self) -> list[PixivSearchingData]:
        if self.error:
            raise ValueError('Search result status is error')
        for content in (self.body.illustManga, self.body.illust, self.body.manga):
            if content is not None:
                return content.data
        raise ValueError('Search result all contents is null')


__all__ = [
    'PixivSearchingData',
    'PixivSearchingResultModel'
]
