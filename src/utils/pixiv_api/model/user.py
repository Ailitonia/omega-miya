"""
@Author         : Ailitonia
@Date           : 2022/04/08 19:00
@FileName       : user.py
@Project        : nonebot2_miya
@Description    : Pixiv User Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pydantic import Field, model_validator

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseArtworkData, BaseNovelData, BasePixivModel, BaseUserData


class PixivUserData(BasePixivModel):
    """Pixiv 用户信息数据"""
    body: BaseUserData
    error: bool
    message: str


class _UserProfileBody(BasePixivModel):
    """Pixiv 用户作品信息"""
    illusts: dict[str, BaseArtworkData | None] = Field(default_factory=dict)
    manga: dict[str, BaseArtworkData | None] = Field(default_factory=dict)
    novels: dict[str, BaseNovelData | None] = Field(default_factory=dict)

    @model_validator(mode='before')
    @classmethod
    def _validate_content_is_none(cls, values):
        """校验 illusts/manga/novels 值为空列表时转为空字典"""
        if isinstance(values, dict):
            values = {k: ({} if isinstance(v, list) and not v else v) for k, v in values.items()}
        return values

    @property
    def illust_list(self) -> list[str]:
        return list(self.illusts.keys())

    @property
    def manga_list(self) -> list[str]:
        return list(self.manga.keys())

    @property
    def novel_list(self) -> list[str]:
        return list(self.novels.keys())


class PixivUserProfile(BasePixivModel):
    """Pixiv 用户作品档案数据"""
    body: _UserProfileBody
    error: bool
    message: str


class PixivUserFull(BasePixivModel):
    """汇总 Pixiv 用户全量数据"""
    user_id: str
    name: str
    image: AnyHttpUrl
    image_big: AnyHttpUrl
    illusts: list[str]
    manga: list[str]
    novels: list[str]

    @property
    def manga_illusts(self) -> list[str]:
        artwork_list = self.manga + self.illusts
        artwork_list.sort(key=int, reverse=True)
        return artwork_list


class _SearchedUserItem(BasePixivModel):
    user_id: str
    user_name: str
    user_head_url: str | None = Field(default=None)
    user_illust_count: int | None = Field(default=None)
    user_desc: str | None = Field(default=None)
    illusts_thumb_urls: list[AnyHttpUrl] = Field(default_factory=list)


class PixivUserSearchingResult(BasePixivModel):
    """Pixiv 用户搜索结果数据"""
    search_name: str
    count: str
    users: list[_SearchedUserItem]


class _FollowLatestIllustPage(BasePixivModel):
    ids: list[str] = Field(default_factory=list)
    isLastPage: bool


class _FollowLatestIllustThumbnails(BasePixivModel):
    illust: list[BaseArtworkData] = Field(default_factory=list)
    novel: list[BaseNovelData] = Field(default_factory=list)


class _FollowLatestIllustBody(BasePixivModel):
    """关注用户的最新作品内容"""
    page: _FollowLatestIllustPage
    thumbnails: _FollowLatestIllustThumbnails
    users: list[BaseUserData] = Field(default_factory=list)
    tagTranslation: dict[str, dict[str, str]] = Field(default_factory=dict)


class PixivFollowLatestIllust(BasePixivModel):
    """已关注用户的最新作品"""
    body: _FollowLatestIllustBody
    error: bool
    message: str

    @property
    def illust_ids(self) -> list[str]:
        return self.body.page.ids


class _BookmarkWorkItem(BaseArtworkData):
    """收藏作品详情"""
    isUnlisted: bool
    isMasked: bool
    url: AnyHttpUrl
    createDate: str
    updateDate: str


class _BookmarkBody(BasePixivModel):
    """收藏页内容"""
    works: list[_BookmarkWorkItem] = Field(default_factory=list)
    bookmarkTags: dict[str, list[str]] = Field(default_factory=dict)
    total: int


class PixivBookmark(BasePixivModel):
    """Pixiv 收藏作品"""
    body: _BookmarkBody
    error: bool
    message: str

    @property
    def total(self) -> int:
        return self.body.total

    @property
    def illust_ids(self) -> list[str]:
        return [x.id for x in self.body.works]


class _FollowUserIllustItem(BaseArtworkData):
    url: AnyHttpUrl
    createDate: str
    updateDate: str
    isUnlisted: bool
    isMasked: bool
    visibilityScope: int


class _FollowUserNovelItem(BaseNovelData):
    useWordCount: bool
    isOriginal: bool
    createDate: str
    updateDate: str
    isMasked: bool
    isUnlisted: bool


class _FollowUserItem(BasePixivModel):
    userId: str
    userName: str
    profileImageUrl: str
    profileImageSmallUrl: str
    userComment: str
    premium: bool
    following: bool
    followed: bool
    isBlocking: bool
    isMypixiv: bool
    illusts: list[_FollowUserIllustItem] = Field(default_factory=list)
    novels: list[_FollowUserNovelItem] = Field(default_factory=list)


class _FollowUserBody(BasePixivModel):
    users: list[_FollowUserItem]
    total: int
    followUserTags: list[str] = Field(default_factory=list)


class PixivFollowUser(BasePixivModel):
    """已关注用户"""
    body: _FollowUserBody
    error: bool
    message: str


__all__ = [
    'PixivUserData',
    'PixivUserProfile',
    'PixivUserFull',
    'PixivUserSearchingResult',
    'PixivFollowLatestIllust',
    'PixivBookmark',
    'PixivFollowUser',
]
