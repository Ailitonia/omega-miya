"""
@Author         : Ailitonia
@Date           : 2024/6/16 下午7:05
@FileName       : model
@Project        : nonebot2_miya
@Description    : 18Comic models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from src.resource import TemporaryResource
from src.utils.image_utils.template import PreviewImageModel, PreviewImageThumbs


class BaseComic18Model(BaseModel):
    """Comic18 数据基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, frozen=True)


class AlbumsResult(BaseComic18Model):
    """漫画搜索结果/分类/排行"""
    aid: int
    title: str
    artist: str
    categories: list[str]
    tags: list[str]
    url: AnyHttpUrl
    cover_image_url: AnyHttpUrl


class AlbumChapter(BaseComic18Model):
    """章节"""
    chapter_id: int
    chapter_title: str


class AlbumData(AlbumsResult):
    """漫画详情页面内容"""
    jm_car: str
    artwork_tag: list[str]
    characters: list[str]
    description: str
    pages: str
    chapters: list[AlbumChapter]


class AlbumPageContent(BaseComic18Model):
    """漫画页面内容"""
    page_id: str
    page_index: int
    page_type: str
    url: AnyHttpUrl
    description: str | None = None


class AlbumPage(BaseComic18Model):
    """漫画页面"""
    count: int
    data: list[AlbumPageContent]
    pagination: list[int]  # 只包含当前页面以外的其他页面


class VideosResult(BaseComic18Model):
    """动画搜索结果/分类/排行"""


class MoviesResult(BaseComic18Model):
    """电影搜索结果/分类/排行"""


class BlogsResult(BaseComic18Model):
    """文库搜索结果/分类/排行"""


@dataclass
class AlbumPackResult:
    """漫画下载/打包信息"""
    file: TemporaryResource
    password: str


class Comic18PreviewRequestModel(BaseComic18Model):
    """请求 Comic18PreviewModel 的入参"""
    desc_text: str
    request_url: AnyHttpUrl


class Comic18PreviewBody(PreviewImageThumbs):
    """Pixiv 作品预览图中的缩略图数据"""


class Comic18PreviewModel(PreviewImageModel):
    """Pixiv 作品预览图 Model"""


__all__ = [
    'AlbumChapter',
    'AlbumData',
    'AlbumPage',
    'AlbumPageContent',
    'AlbumsResult',
    'AlbumPackResult',
    'Comic18PreviewRequestModel',
    'Comic18PreviewBody',
    'Comic18PreviewModel',
]
