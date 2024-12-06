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

from pydantic import Field, model_validator

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BasePixivModel


class _GlobalUserData(BasePixivModel):
    """全局用户数据"""
    id: int
    pixivId: str
    name: str
    profileImg: AnyHttpUrl | None = None
    profileImgBig: AnyHttpUrl | None = None
    premium: bool
    xRestrict: int
    adult: bool
    safeMode: bool | None = None  # maybe deactivated
    illustCreator: bool
    novelCreator: bool
    hideAiWorks: bool
    readingStatusEnabled: bool


class PixivGlobalData(BasePixivModel):
    """Pixiv 主页全局数据"""
    token: str
    services: dict
    oneSignalAppId: str
    publicPath: AnyHttpUrl | None = None
    commonResourcePath: AnyHttpUrl | None = None
    development: bool
    userData: _GlobalUserData
    adsData: dict | None = None
    miscData: dict | None = None
    premium: dict | None = None
    mute: list

    @property
    def uid(self) -> int:
        return self.userData.id

    @property
    def username(self) -> str:
        return self.userData.name


class PixivUserDataBody(BasePixivModel):
    """Pixiv 用户信息 Body"""
    userId: int
    name: str
    image: AnyHttpUrl | None = None
    imageBig: AnyHttpUrl | None = None


class PixivUserDataModel(BasePixivModel):
    """Pixiv 用户信息 Model"""
    body: PixivUserDataBody
    error: bool
    message: str


class PixivUserArtworkDataBody(BasePixivModel):
    """Pixiv 用户作品信息 Body"""
    illusts: dict[int, Any]
    manga: dict[int, Any]
    novels: dict[int, Any]

    @model_validator(mode='before')
    @classmethod
    def _validate_content_is_none(cls, values):
        """校验 illusts/manga/novels 值为空列表时转为空字典"""
        if isinstance(values, dict):
            for k, v in values.items():
                if isinstance(v, list) and not v:
                    values[k] = {}
        return values

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
    body: PixivUserArtworkDataBody
    error: bool
    message: str


class PixivUserModel(BasePixivModel):
    """Pixiv 用户 Model"""
    user_id: int
    name: str
    image: AnyHttpUrl | None = None
    image_big: AnyHttpUrl | None = None
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
    user_head_url: str | None = None
    user_illust_count: int | None = None
    user_desc: str | None = None
    illusts_thumb_urls: list[AnyHttpUrl] = Field(default_factory=list)


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
    body: PixivFollowLatestIllustBody
    error: bool
    message: str

    @property
    def illust_ids(self) -> list[int]:
        return self.body.page.ids


class _WorkBookmarkData(BasePixivModel):
    """收藏作品属性"""
    id: str
    private: bool


class BookmarkWork(BasePixivModel):
    """收藏作品详情"""
    id: int
    title: str
    illustType: int
    xRestrict: int
    restrict: int
    sl: int
    url: AnyHttpUrl
    description: str
    tags: list[str]
    userId: str
    userName: str
    width: int
    height: int
    pageCount: int
    isBookmarkable: bool
    bookmarkData: _WorkBookmarkData | None = None
    alt: str
    titleCaptionTranslation: dict
    createDate: str
    updateDate:str
    isUnlisted: bool
    isMasked: bool
    aiType: int
    profileImageUrl: AnyHttpUrl | None = None


class BookmarkBody(BasePixivModel):
    """收藏页内容"""
    bookmarkTags: list | dict | None = None
    extraData: dict
    total: int
    works: list[BookmarkWork]
    zoneConfig: dict


class PixivBookmark(BasePixivModel):
    """Pixiv 收藏作品"""
    body: BookmarkBody
    error: bool
    message: str

    @property
    def total(self) -> int:
        return self.body.total

    @property
    def illust_ids(self) -> list[int]:
        return [x.id for x in self.body.works]


class FollowUserIllust(BasePixivModel):
    id: str
    title: str
    illustType: int
    xRestrict: int
    restrict: int
    sl: int
    url: str
    description: str
    tags: list[str]
    userId: str
    userName: str
    width: int
    height: int
    pageCount: int
    isBookmarkable: bool
    alt: str
    createDate: str
    updateDate: str
    isUnlisted: bool
    isMasked: bool
    aiType: int
    profileImageUrl: str


class FollowUserNovel(BasePixivModel):
    id: str
    title: str
    genre: str
    xRestrict: int
    restrict: int
    url: str
    tags: list[str]
    userId: str
    userName: str
    profileImageUrl: str
    textCount: int
    wordCount: int
    readingTime: int
    useWordCount: bool
    description: str
    isBookmarkable: bool
    bookmarkCount: int
    isOriginal: bool
    createDate: str
    updateDate: str
    isMasked: bool
    aiType: int
    isUnlisted: bool


class FollowUserData(BasePixivModel):
    """关注的用户信息"""
    userId: str
    userName: str
    profileImageUrl: str
    userComment: str
    following: bool
    followed: bool
    isBlocking: bool
    isMypixiv: bool
    illusts: list[FollowUserIllust]
    novels: list[FollowUserNovel]


class FollowUserBody(BasePixivModel):
    users: list[FollowUserData]
    total: int
    followUserTags: list[Any]


class PixivFollowUser(BasePixivModel):
    """关注用户"""
    error: bool
    message: str
    body: FollowUserBody


__all__ = [
    'PixivGlobalData',
    'PixivUserDataModel',
    'PixivUserArtworkDataModel',
    'PixivUserModel',
    'PixivUserSearchingBody',
    'PixivUserSearchingModel',
    'PixivFollowLatestIllust',
    'PixivBookmark',
    'PixivFollowUser',
]
