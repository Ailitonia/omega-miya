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
from pydantic import AnyHttpUrl
from .base_model import BasePixivModel


class PixivisionIllustrationTag(BasePixivModel):
    tag_id: int
    tag_name: str
    tag_url: AnyHttpUrl


class PixivisionIllustration(BasePixivModel):
    """Pixivision Illustration Model"""
    aid: int
    title: str
    thumbnail: AnyHttpUrl
    url: AnyHttpUrl
    tags: list[PixivisionIllustrationTag]

    @property
    def all_tags_id(self) -> list[int]:
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


class PixivisionIllustrationList(BasePixivModel):
    """Pixivision Illustration 清单"""
    illustrations: list[PixivisionIllustration]


class PixivisionArticleArtwork(BasePixivModel):
    artwork_id: int
    artwork_title: str
    artwork_user: str
    artwork_url: AnyHttpUrl
    image_url: AnyHttpUrl | None = None


class PixivisionArticle(BasePixivModel):
    """Pixivision 文章 Model"""
    title: str
    description: str
    eyecatch_image: AnyHttpUrl | None = None
    artwork_list: list[PixivisionArticleArtwork]
    tags_list: list[PixivisionIllustrationTag]

    @property
    def title_without_mark(self) -> str:
        return re.sub(r'【.+?】', '', self.title)


__all__ = [
    'PixivisionIllustrationList',
    'PixivisionIllustration',
    'PixivisionArticle'
]
