"""
@Author         : Ailitonia
@Date           : 2022/04/10 13:14
@FileName       : pixivision.py
@Project        : nonebot2_miya
@Description    : Pixivision Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import re

from pydantic import Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BasePixivModel


class _IllustrationTagItem(BasePixivModel):
    tag_id: str
    tag_name: str
    tag_url: AnyHttpUrl


class PixivisionIllustrationItem(BasePixivModel):
    """Pixivision Illustration 特辑作品数据"""
    aid: str
    title: str
    thumbnail: AnyHttpUrl
    url: AnyHttpUrl
    tags: list[_IllustrationTagItem] = Field(default_factory=list)

    @property
    def all_tags_id(self) -> list[str]:
        return [x.tag_id for x in self.tags]

    @property
    def all_tags_name(self) -> list[str]:
        return [x.tag_name for x in self.tags]

    @property
    def split_title(self) -> str:
        return '\n'.join([x.strip() for x in self.title.split('-')])

    @property
    def split_title_without_mark(self) -> str:
        return re.sub(r'【.+?】', '', self.split_title)


class PixivisionIllustrations(BasePixivModel):
    """Pixivision Illustration 特辑作品导览数据"""
    illustrations: list[PixivisionIllustrationItem] = Field(default_factory=list)


class _ArticleArtworkItem(BasePixivModel):
    artwork_id: str
    artwork_title: str
    artwork_user: str
    artwork_url: AnyHttpUrl
    image_url: AnyHttpUrl | None = None


class PixivisionArticle(BasePixivModel):
    """Pixivision Article 特辑文章数据"""
    title: str
    description: str
    eyecatch_image: AnyHttpUrl | None = None
    artwork_list: list[_ArticleArtworkItem] = Field(default_factory=list)
    illustration_list: list[PixivisionIllustrationItem] = Field(default_factory=list)
    tags_list: list[_IllustrationTagItem] = Field(default_factory=list)

    @property
    def title_without_mark(self) -> str:
        return re.sub(r'【.+?】', '', self.title)


__all__ = [
    'PixivisionIllustrations',
    'PixivisionIllustrationItem',
    'PixivisionArticle',
]
