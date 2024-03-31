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
from .base_model import BasePixivModel
from .searching import PixivSearchingData


class PixivDiscoveryContent(BasePixivModel):
    """Pixiv 发现内容"""
    illustId: int
    recommendMethods: list[str]
    recommendScore: float
    recommendSeedIllustIds: list[int]


class PixivThumbnails(BasePixivModel):
    """Pixiv 结果内容预览"""
    illust: list[PixivSearchingData]


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
    def recommend_data(self) -> list[PixivSearchingData]:
        if self.error:
            raise ValueError('Discovery result status is error')
        return self.body.thumbnails.illust


class PixivRecommendDetails(BasePixivModel):
    """Pixiv 首页推荐内容 Details"""
    methods: list[str]
    score: float
    seedIllustIds: list[int]


class PixivRecommendContent(BasePixivModel):
    """Pixiv 首页推荐内容"""
    details: dict[int, PixivRecommendDetails]
    ids: list[int]


class PixivRecommendTagContent(BasePixivModel):
    """Pixiv 首页推荐 tag 内容"""
    tag: str
    details: dict[int, PixivRecommendDetails]
    ids: list[int]


class PixivRecommendPage(BasePixivModel):
    """Pixiv 首页推荐内容 Page"""
    recommend: PixivRecommendContent
    recommendByTag: list[PixivRecommendTagContent]


class PixivRecommendBody(BasePixivModel):
    """Pixiv 首页推荐内容 Body"""
    page: PixivRecommendPage
    thumbnails: PixivThumbnails


class PixivRecommendModel(BasePixivModel):
    """Pixiv 首页推荐内容 Model"""
    body: PixivRecommendBody
    error: bool
    message: str

    @property
    def recommend_pids(self) -> list[int]:
        if self.error:
            raise ValueError('Recommend result status is error')
        return self.body.page.recommend.ids

    @property
    def random_recommend_tag_pids(self) -> (str, list[int]):
        if self.error:
            raise ValueError('Recommend result status is error')
        random_recommend_by_tag = random.choice(self.body.page.recommendByTag)
        return random_recommend_by_tag.tag, random_recommend_by_tag.ids


__all__ = [
    'PixivDiscoveryModel',
    'PixivRecommendModel'
]
