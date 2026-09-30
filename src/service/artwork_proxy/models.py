"""
@Author         : Ailitonia
@Date           : 2024/8/4 下午7:19
@FileName       : models
@Project        : nonebot2_miya
@Description    : Artwork Proxy Models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from src.database.internal.artwork_collection import ArtworkClassification, ArtworkRating


class BaseArtworkProxyModel(BaseModel):
    """Artwork Proxy 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class ArtworkPageFile(BaseArtworkProxyModel):
    """作品图片详情"""
    url: AnyHttpUrl
    file_ext: str
    width: int | None = None
    height: int | None = None


class ArtworkPage(BaseArtworkProxyModel):
    """作品图片信息"""
    page_index: int
    preview_file: ArtworkPageFile  # 预览图/缩略图
    regular_file: ArtworkPageFile  # 通常大图
    original_file: ArtworkPageFile  # 原图


class ArtworkProxyData(BaseArtworkProxyModel):
    """Artwork Proxy 统一作品信息"""
    origin: str  # 作品来源 (指收录该作品的站点, 如 Pixiv, Danbooru, yande 等)
    aid: str
    uid: str
    title: str
    uname: str
    classification: ArtworkClassification
    rating: ArtworkRating
    width: int
    height: int
    tags: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None)
    like_count: int | None = Field(default=None, description='喜欢/点赞数量')
    bookmark_count: int | None = Field(default=None, description='收藏数量')
    view_count: int | None = Field(default=None, description='浏览次数')
    comment_count: int | None = Field(default=None, description='评论量')
    source: str  # 原始出处地址, 本来就是源站的为源站作品地址
    pages: list[ArtworkPage] = Field(default_factory=list)
    extra_resource: list[AnyHttpUrl] = Field(default_factory=list, description='其他额外资源链接')
    published_at: datetime | None = Field(default=None)

    @property
    def index_pages(self) -> dict[int, ArtworkPage]:
        """索引所有图片信息"""
        index = {p.page_index: p for i, p in enumerate(self.pages) if p.page_index == i}
        if len(index) != len(self.pages):
            raise ValueError(f'{self.origin} {self.aid} has erroneous or duplicate page index')
        return index

    @property
    def cover_page_url(self) -> AnyHttpUrl:
        """首页/封面原图链接"""
        return self.index_pages[0].original_file.url


class ArtworkPoolData(BaseArtworkProxyModel):
    """Artwork Poll 统一作品合集信息"""
    origin: str
    pool_id: str
    name: str
    description: str | None = Field(default=None)
    artwork_ids: list[str] = Field(default_factory=list)

    @property
    def count_num(self) -> int:
        return len(self.artwork_ids)


class ArtistUserData(BaseArtworkProxyModel):
    """Artist 作者/用户信息"""
    origin: str
    uid: str
    name: str
    profile_image: AnyHttpUrl | None = Field(default=None)
    artwork_ids: list[str] = Field(default_factory=list)


class PreviewImageThumbsItem(BaseArtworkProxyModel):
    """生成预览图中的每个小缩略图的数据"""
    desc_text: str
    thumb_data: bytes


class PreviewImagesData(BaseArtworkProxyModel):
    """生成预览图的数据"""
    preview_name: str
    thumb_items: list[PreviewImageThumbsItem] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.thumb_items)


__all__ = [
    'ArtistUserData',
    'ArtworkClassification',
    'ArtworkProxyData',
    'ArtworkPage',
    'ArtworkPageFile',
    'ArtworkPoolData',
    'ArtworkRating',
    'PreviewImagesData',
    'PreviewImageThumbsItem',
]
