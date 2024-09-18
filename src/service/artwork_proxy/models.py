"""
@Author         : Ailitonia
@Date           : 2024/8/4 下午7:19
@FileName       : models
@Project        : nonebot2_miya
@Description    : Artwork Proxy Models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from enum import IntEnum, unique
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl


@unique
class ArtworkClassification(IntEnum):
    """作品分类级别(标记作品元数据/分级/来源等信息是否可靠, 是否是由人工审核过的)"""
    Ignored = -2  # 可能是由于低质/敏感话题/广告等因素, 被人工手动审核/标记为忽略该作品, 一般情况下不应当使用分类为此等级的作品
    Unknown = -1  # 无法确认分类级别, 一般为本地图片或无确切来源(各种不标明来源的页面, 推文, 动态, etc.)的图片
    Unclassified = 0  # 未分类, 一般为无分级网站(pixiv, twitter, etc.)作品默认分类级别
    AIGenerated = 1  # 确认/疑似为 AI 生成作品
    Automatic = 2  # 由图站分类/图站分级/第三方接口分类, 可能由人工进行分类但不完全可信, 一般可作为应用层插件使用的最低可信级别
    Confirmed = 3  # 由人工审核/确认为 "人类生成" 的作品, 且分级可信


@unique
class ArtworkRating(IntEnum):
    """作品分级(参考 danbooru wiki howto:rate)"""
    Unknown = -1  # 未知, 可能为下面任意一种分级的其中之一, 绝对不要直接当作 G-rated 作品使用
    General = 0  # G-rated content. 任何人随时可观看的, sfw
    Sensitive = 1  # Ecchi, sexy, suggestive, or mildly erotic. 包含内衣/泳装/部分裸露/暗示性动作等, 涩图, nsfw
    Questionable = 2  # Softcore erotica. 除了关键之外的明目张胆, 官能作品, nsfw+
    Explicit = 3  # Hardcore erotica. 限制级作品, R18, nsfw+++


class BaseArtworkProxyModel(BaseModel):
    """Artwork Proxy 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class ArtworkPageFile(BaseArtworkProxyModel):
    """作品图片详情"""
    url: AnyHttpUrl
    file_ext: str
    width: Optional[int] = None
    height: Optional[int] = None


class ArtworkPage(BaseArtworkProxyModel):
    """作品图片信息"""
    preview_file: ArtworkPageFile  # 预览图/缩略图
    regular_file: ArtworkPageFile  # 通常大图
    original_file: ArtworkPageFile  # 原图


class ArtworkData(BaseArtworkProxyModel):
    """作品信息"""
    origin: str  # 作品来源(指收录该作品的站点, 如 Pixiv, Danbooru, yande 等)
    aid: str
    title: str
    uid: str
    uname: str
    classification: ArtworkClassification
    rating: ArtworkRating  # 不同图站分级不同, 这里参考 Danbooru 的分级方式, Pixiv 的 r18 被视为 Explicit
    width: int
    height: int
    tags: list[str]
    description: Optional[str] = None
    like_count: Optional[int] = None  # 喜欢/点赞数量
    bookmark_count: Optional[int] = None  # 收藏数量
    view_count: Optional[int] = None  # 浏览次数
    comment_count: Optional[int] = None  # 评论量
    source: str  # 原始出处地址(指能直接获得该作品的来源), 一般来说为 url
    pages: list[ArtworkPage]
    extra_resource: list[AnyHttpUrl] = Field(default_factory=list)  # 其他额外资源链接

    @property
    def cover_page_url(self) -> AnyHttpUrl:
        """首页/封面原图链接"""
        return self.index_pages[0].original_file.url

    @property
    def index_pages(self) -> dict[int, ArtworkPage]:
        """所有图片"""
        return {k: v for k, v in enumerate(self.pages)}

    @property
    def preview_pages_url(self) -> dict[int, AnyHttpUrl]:
        """所有预览图"""
        return {k: v for k, v in enumerate(x.preview_file.url for x in self.pages)}

    @property
    def regular_pages_url(self) -> dict[int, AnyHttpUrl]:
        """所有通常大图"""
        return {k: v for k, v in enumerate(x.regular_file.url for x in self.pages)}

    @property
    def original_pages_url(self) -> dict[int, AnyHttpUrl]:
        """所有原图"""
        return {k: v for k, v in enumerate(x.original_file.url for x in self.pages)}


class ArtworkPool(BaseArtworkProxyModel):
    origin: str
    pool_id: str
    name: str
    description: Optional[str] = None
    artwork_ids: list[str]

    @property
    def artwork_count(self) -> int:
        return len(self.artwork_ids)


__all__ = [
    'ArtworkClassification',
    'ArtworkData',
    'ArtworkPage',
    'ArtworkPageFile',
    'ArtworkPool',
    'ArtworkRating',
]
