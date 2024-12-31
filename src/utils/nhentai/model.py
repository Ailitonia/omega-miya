"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午6:57
@FileName       : model
@Project        : nonebot2_miya
@Description    : Nhentai Models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from src.resource import TemporaryResource
from src.utils.image_utils.template import PreviewImageModel, PreviewImageThumbs


class BaseNhentaiModel(BaseModel):
    """Nhentai 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class NhentaiSearchingGallery(BaseNhentaiModel):
    """Gallery 的搜索结果内容"""
    gallery_id: int
    gallery_title: str
    cover_image_url: AnyHttpUrl


class NhentaiSearchingResult(BaseNhentaiModel):
    """Gallery 搜索结果"""
    results: list[NhentaiSearchingGallery]


class NhentaiGalleryTitle(BaseNhentaiModel):
    """Gallery 页面标题"""
    english: str | None
    japanese: str | None
    pretty: str | None


class NhentaiGalleryPage(BaseNhentaiModel):
    """Gallery Page 内容"""
    t: Literal['j', 'p']
    w: int
    h: int


class NhentaiGalleryImages(BaseNhentaiModel):
    """Gallery Images 内容"""
    pages: list[NhentaiGalleryPage]
    cover: NhentaiGalleryPage
    thumbnail: NhentaiGalleryPage


class NhentaiGalleryTag(BaseNhentaiModel):
    """Gallery Tag"""
    id: int
    type: str
    name: str
    url: str
    count: int


class NhentaiGalleryModel(BaseNhentaiModel):
    """Gallery 页面内容"""
    id: int
    media_id: int
    title: NhentaiGalleryTitle
    cover_image: AnyHttpUrl
    images: NhentaiGalleryImages
    thumbs_images: list[AnyHttpUrl]
    tags: list[NhentaiGalleryTag]
    num_pages: int

    @model_validator(mode='before')
    @classmethod
    def _verify_num_pages(cls, values):
        num_pages = values.get('num_pages', -1)
        images_pages = values.get('images', {}).get('pages', [])

        if num_pages != len(images_pages):
            raise ValueError('Parsed page count not match between "num_pages" and "images"')
        return values


class NhentaiPreviewRequestModel(BaseNhentaiModel):
    """请求 NhentaiPreviewModel 的入参"""
    desc_text: str
    request_url: AnyHttpUrl


class NhentaiPreviewBody(PreviewImageThumbs):
    """Pixiv 作品预览图中的缩略图数据"""


class NhentaiPreviewModel(PreviewImageModel):
    """Pixiv 作品预览图 Model"""


@dataclass
class NhentaiDownloadResult:
    """Nhentai 下载结果信息"""
    file: TemporaryResource
    password: str


__all__ = [
    'NhentaiDownloadResult',
    'NhentaiGalleryModel',
    'NhentaiPreviewRequestModel',
    'NhentaiPreviewBody',
    'NhentaiPreviewModel',
    'NhentaiSearchingResult'
]
