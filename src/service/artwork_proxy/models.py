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
from typing import Literal, Optional, TypeAlias

from pydantic import BaseModel, ConfigDict

from src.compat import AnyHttpUrlStr as AnyHttpUrl

ArtworkPageType: TypeAlias = Literal['preview', 'regular', 'original']


@unique
class ArtworkClassification(IntEnum):
    """作品分类(标记作品分级分类等是否是人工识别过的)"""
    Unknown: int = -1
    Unclassified: int = 0
    Confirmed: int = 1  # 确认为 "人类生成" 作品, 已人工标记或从可信已标记来源获取
    AIGenerated: int = 2  # 确认为 AI 生成作品


@unique
class ArtworkRating(IntEnum):
    """作品分级"""
    Unknown: int = -1
    General: int = 0  # G-rated content. Completely safe for work. Nothing sexualized or inappropriate to view in front of others.
    Sensitive: int = 1  # Ecchi, sexy, suggestive, or mildly erotic. Skimpy or revealing clothes, swimsuits, underwear, images focused on the breasts or ass, and anything else potentially not safe for work.
    Questionable: int = 2  # Softcore erotica. Simple nudity or near-nudity, but no explicit sex or exposed genitals.
    Explicit: int = 3  # Hardcore erotica. Explicit sex acts, exposed genitals, and bodily fluids.


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
    aid: str
    origin: str  # 作品来源(指收录该作品的站点, 如 Pixiv, Danbooru, yande 等)
    title: str
    uid: Optional[str] = None
    uname: str
    tags: list[str]
    description: Optional[str] = None
    classification: ArtworkClassification
    rating: ArtworkRating  # 不同图站分级不同, 这里参考 Danbooru 的分级方式, Pixiv 的 r18 被视为 Explicit
    source: str  # 原始出处地址(指能直接获得该作品的来源), 一般来说为 url
    pages: list[ArtworkPage]

    @property
    def index_pages(self) -> dict[int, ArtworkPage]:
        return {k: v for k, v in enumerate(self.pages)}

    @property
    def preview_pages_url(self) -> dict[int, AnyHttpUrl]:
        return {k: v for k, v in enumerate(x.preview_file.url for x in self.pages)}

    @property
    def regular_pages_url(self) -> dict[int, AnyHttpUrl]:
        return {k: v for k, v in enumerate(x.regular_file.url for x in self.pages)}

    @property
    def original_pages_url(self) -> dict[int, AnyHttpUrl]:
        return {k: v for k, v in enumerate(x.original_file.url for x in self.pages)}


__all__ = [
    'ArtworkData',
    'ArtworkPage',
    'ArtworkPageType',
]
