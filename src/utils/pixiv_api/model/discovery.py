"""
@Author         : Ailitonia
@Date           : 2022/04/06 1:14
@FileName       : discovery.py
@Project        : nonebot2_miya 
@Description    : Pixiv Discovery Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import random
from typing import Optional

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BasePixivModel


class ThumbnailData(BasePixivModel):
    id: int
    title: str
    alt: Optional[str] = None
    userId: int
    userName: str
    aiType: int
    illustType: int
    xRestrict: int
    pageCount: int
    width: int
    height: int
    url: AnyHttpUrl
    tags: list[str]


class PixivDiscoveryContent(BasePixivModel):
    """Pixiv 发现内容"""
    illustId: int
    recommendMethods: list[str]
    recommendScore: float
    recommendSeedIllustIds: list[int]


class PixivThumbnails(BasePixivModel):
    """Pixiv 结果内容预览"""
    illust: list[ThumbnailData]


class PixivDiscoveryBody(BasePixivModel):
    """Pixiv 发现内容 Body"""
    recommendedIllusts: list[PixivDiscoveryContent]
    thumbnails: PixivThumbnails


class PixivDiscoveryModel(BasePixivModel):
    """Pixiv 发现内容 Model"""
    body: PixivDiscoveryBody
    error: bool
    message: str

    @property
    def recommend_pids(self) -> list[int]:
        if self.error:
            raise ValueError('Discovery result status is error')
        return [x.illustId for x in self.body.recommendedIllusts]

    @property
    def recommend_data(self) -> list[ThumbnailData]:
        if self.error:
            raise ValueError('Discovery result status is error')
        return self.body.thumbnails.illust


class PixivTopDetails(BasePixivModel):
    """Pixiv 首页推荐内容 Details"""
    methods: list[str]
    score: float
    seedIllustIds: list[int]


class PixivTopRecommendContent(BasePixivModel):
    """Pixiv 首页推荐内容"""
    details: dict[int, PixivTopDetails]
    ids: list[int]


class PixivTopTagRecommendContent(BasePixivModel):
    """Pixiv 首页推荐 tag 内容"""
    tag: str
    details: dict[int, PixivTopDetails]
    ids: list[int]


class PixivTopUserRecommendContent(BasePixivModel):
    """Pixiv 首页推荐用户内容"""
    id: int
    illustIds: list[int]
    novelIds: list[int]


class PixivTopPixivision(BasePixivModel):
    """Pixiv 首页推荐 Pixivision 特辑内容"""
    id: int
    title: str
    url: AnyHttpUrl
    thumbnailUrl: str


class PixivTopTags(BasePixivModel):
    """Pixiv 首页推送 Tag"""
    tag: str
    ids: list[int]


class PixivTopPage(BasePixivModel):
    """Pixiv 首页推荐内容 Page"""
    follow: list[int]  # 已关注用户的最新作品
    myFavoriteTags: list[str]  # 收藏的 Tag
    newPost: list[int]  # 全站最新作品
    pixivision: list[PixivTopPixivision]  # 最新的 Pixivision 特辑
    recommend: PixivTopRecommendContent  # 首页推荐作品
    recommendByTag: list[PixivTopTagRecommendContent]  # 首页 Tag 及作品推荐
    recommendUser: list[PixivTopUserRecommendContent]  # 首页用户推荐
    tags: list[PixivTopTags]  # 你的 XP


class PixivTopUser(BasePixivModel):
    """Pixiv 首页推荐用户"""
    userId: int
    name: str
    isFollowed: bool
    image: str
    imageBig: str
    premium: bool
    comment: Optional[str] = None


class PixivTopBody(BasePixivModel):
    """Pixiv 首页推荐内容 Body"""
    page: PixivTopPage
    thumbnails: PixivThumbnails
    users: list[PixivTopUser]


class PixivTopModel(BasePixivModel):
    """Pixiv 首页推荐内容 Model"""
    body: PixivTopBody
    error: bool
    message: str

    @property
    def recommend_pids(self) -> list[int]:
        if self.error:
            raise ValueError('Recommend result status is error')
        return self.body.page.recommend.ids

    @property
    def random_recommend_tag_pids(self) -> tuple[str, list[int]]:
        if self.error:
            raise ValueError('Recommend result status is error')
        random_recommend_by_tag = random.choice(self.body.page.recommendByTag)
        return random_recommend_by_tag.tag, random_recommend_by_tag.ids


__all__ = [
    'PixivDiscoveryModel',
    'PixivTopModel',
]
