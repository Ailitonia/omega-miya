"""
@Author         : Ailitonia
@Date           : 2022/04/10 21:50
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Nhentai Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from pydantic import BaseModel, AnyHttpUrl, root_validator

from omega_miya.utils.image_utils import PreviewImageThumbs, PreviewImageModel


class BaseNhentaiModel(BaseModel):
    class Config:
        extra = 'ignore'
        allow_mutation = False


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
    images: NhentaiGalleryImages
    tags: list[NhentaiGalleryTag]
    num_pages: int

    @root_validator(pre=True)
    def verify_num_pages(cls, values):
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


__all__ = [
    'NhentaiSearchingResult',
    'NhentaiGalleryModel',
    'NhentaiPreviewRequestModel',
    'NhentaiPreviewBody',
    'NhentaiPreviewModel'
]
