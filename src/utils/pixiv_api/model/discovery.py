"""
@Author         : Ailitonia
@Date           : 2022/04/06 1:14
@FileName       : discovery.py
@Project        : nonebot2_miya
@Description    : Pixiv Discovery Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pydantic import Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseArtworkData, BaseNovelData, BasePixivModel, BaseUserData


class _IllustUrls(BasePixivModel):
    type_250x250: AnyHttpUrl = Field(alias='250x250')
    type_360x360: AnyHttpUrl = Field(alias='360x360')
    type_540x540: AnyHttpUrl = Field(alias='540x540')
    type_1200x1200: AnyHttpUrl = Field(alias='1200x1200')


class _IllustItem(BaseArtworkData):
    isUnlisted: bool
    isMasked: bool
    visibilityScope: int
    url: AnyHttpUrl
    urls: _IllustUrls
    createDate: str
    updateDate: str


class _NovelItem(BaseNovelData):
    isOriginal: bool
    isMasked: bool
    isUnlisted: bool
    visibilityScope: int
    createDate: str
    updateDate: str


class _ThumbnailsItem(BasePixivModel):
    illust: list[_IllustItem] = Field(default_factory=list)
    novel: list[_NovelItem] = Field(default_factory=list)


class _DiscoveryRecommendedIllust(BasePixivModel):
    illustId: str
    recommendMethods: list[str]
    recommendScore: float
    recommendSeedIllustIds: list[str]


class _DiscoveryBody(BasePixivModel):
    recommendedIllusts: list[_DiscoveryRecommendedIllust]
    thumbnails: _ThumbnailsItem
    tagTranslation: dict[str, dict[str, str]] = Field(default_factory=dict)


class PixivDiscovery(BasePixivModel):
    """Pixiv 发现内容数据"""
    body: _DiscoveryBody
    error: bool
    message: str

    @property
    def recommend_pids(self) -> list[str]:
        if self.error:
            raise ValueError('Discovery result status is error')
        return [x.illustId for x in self.body.recommendedIllusts]

    @property
    def recommend_illusts(self) -> list[_IllustItem]:
        if self.error:
            raise ValueError('Discovery result status is error')
        return self.body.thumbnails.illust


class _TopPageTags(BasePixivModel):
    """Pixiv 首页推送 Tag"""
    tag: str
    ids: list[str]


class _TopPageDetailItem(BasePixivModel):
    methods: list[str] = Field(default_factory=list)
    score: float
    seedIllustIds: list[str] = Field(default_factory=list)


class _TopPageRecommend(BasePixivModel):
    ids: list[str] = Field(default_factory=list)
    details: dict[str, _TopPageDetailItem] = Field(default_factory=dict)


class _TopPageRecommendByTag(BasePixivModel):
    tag: str
    ids: list[str]
    details: dict[str, _TopPageDetailItem] = Field(default_factory=dict)


class _TopPageRecommendUser(BasePixivModel):
    id: str
    illustIds: list[str]
    novelIds: list[str]


class _TopPagePixivision(BasePixivModel):
    id: str
    title: str
    url: AnyHttpUrl
    thumbnailUrl: AnyHttpUrl | None = Field(default=None)


class _TopPage(BasePixivModel):
    tags: list[_TopPageTags] = Field(default_factory=list, description='你的 XP')
    follow: list[str] = Field(default_factory=list, description='已关注用户的最新作品')
    recommend: _TopPageRecommend = Field(default_factory=_TopPageRecommend, description='首页推荐作品')
    recommendByTag: list[_TopPageRecommendByTag] = Field(default_factory=list, description='首页 Tag 及作品推荐')
    recommendUser: list[_TopPageRecommendUser] = Field(default_factory=list, description='首页用户推荐')
    myFavoriteTags: list[str] = Field(default_factory=list, description='收藏的 Tag')
    newPost: list[str] = Field(default_factory=list, description='全站最新作品')
    pixivision: list[_TopPagePixivision] = Field(default_factory=list, description='最新的 Pixivision 特辑')


class _TopBoothItem(BasePixivModel):
    id: str
    userId: str
    title: str
    url: AnyHttpUrl
    imageUrl: AnyHttpUrl
    adult: bool


class _TopBody(BasePixivModel):
    thumbnails: _ThumbnailsItem = Field(default_factory=_ThumbnailsItem)
    users: list[BaseUserData] = Field(default_factory=list)
    page: _TopPage = Field(default_factory=_TopPage)
    boothItems: list[_TopBoothItem] = Field(default_factory=list)
    tagTranslation: dict[str, dict[str, str]] = Field(default_factory=dict)


class PixivTop(BasePixivModel):
    """Pixiv 首页推荐内容数据"""
    body: _TopBody
    error: bool
    message: str

    @property
    def recommend_pids(self) -> list[str]:
        if self.error:
            raise ValueError('Recommend result status is error')
        return self.body.page.recommend.ids


__all__ = [
    'PixivDiscovery',
    'PixivTop',
]
