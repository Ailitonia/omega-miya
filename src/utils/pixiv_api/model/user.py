"""
@Author         : Ailitonia
@Date           : 2022/04/08 19:00
@FileName       : user.py
@Project        : nonebot2_miya 
@Description    : Pixiv User Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any
from pydantic import AnyHttpUrl
from .base_model import BasePixivModel


class PixivUserDataBody(BasePixivModel):
    """Pixiv 用户信息 Body"""
    userId: int
    name: str
    image: AnyHttpUrl
    imageBig: AnyHttpUrl


class PixivUserDataModel(BasePixivModel):
    """Pixiv 用户信息 Model"""
    body: PixivUserDataBody | list[None]
    error: bool
    message: str


class PixivUserArtworkDataBody(BasePixivModel):
    """Pixiv 用户作品信息 Body"""
    illusts: dict[int, Any]
    manga: dict[int, Any]
    novels: dict[int, Any]

    @property
    def illust_list(self) -> list[int]:
        return [x for x in self.illusts.keys()]

    @property
    def manga_list(self) -> list[int]:
        return [x for x in self.manga.keys()]

    @property
    def novel_list(self) -> list[int]:
        return [x for x in self.novels.keys()]


class PixivUserArtworkDataModel(BasePixivModel):
    """Pixiv 用户作品信息 Model"""
    body: PixivUserArtworkDataBody | list[None]
    error: bool
    message: str


class PixivUserModel(BasePixivModel):
    """Pixiv 用户 Model"""
    user_id: int
    name: str
    image: AnyHttpUrl
    image_big: AnyHttpUrl
    illusts: list[int]
    manga: list[int]
    novels: list[int]

    @property
    def manga_illusts(self) -> list[int]:
        artwork_list = self.manga + self.illusts
        artwork_list.sort(reverse=True)
        return artwork_list


class PixivUserSearchingBody(BasePixivModel):
    """Pixiv 用户搜索结果 body"""
    user_id: int
    user_name: str
    user_head_url: str
    user_illust_count: int
    user_desc: str
    illusts_thumb_urls: list[AnyHttpUrl]


class PixivUserSearchingModel(BasePixivModel):
    """Pixiv 用户搜索结果 Model"""
    search_name: str
    count: str
    users: list[PixivUserSearchingBody]


class PixivFollowLatestIllustPage(BasePixivModel):
    """关注用户的最新作品页面"""
    ids: list[int]
    isLastPage: bool
    tags: list


class PixivFollowLatestIllustBody(BasePixivModel):
    """关注用户的最新作品内容"""
    illustSeries: list
    page: PixivFollowLatestIllustPage
    requests: list
    tagTranslation: dict
    thumbnails: dict
    users: list
    zoneConfig: dict


class PixivFollowLatestIllust(BasePixivModel):
    """关注用户的最新作品"""
    body: PixivFollowLatestIllustBody | list[None]
    error: bool
    message: str

    @property
    def illust_ids(self) -> list[int]:
        return self.body.page.ids


__all__ = [
    'PixivUserDataModel',
    'PixivUserArtworkDataModel',
    'PixivUserModel',
    'PixivUserSearchingBody',
    'PixivUserSearchingModel',
    'PixivFollowLatestIllust'
]
