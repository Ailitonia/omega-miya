"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:51
@FileName       : artwork.py
@Project        : nonebot2_miya 
@Description    : Pixiv Artwork Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from lxml import etree
from typing import Optional

from src.compat import AnyHttpUrlStr as AnyHttpUrl

from .base_model import BasePixivModel
from .searching import PixivSearchingData


class PixivTagTranslation(BasePixivModel):
    """Pixiv tag 翻译"""
    en: str


class PixivTag(BasePixivModel):
    """Pixiv tag 模型"""
    tag: str
    translation: Optional[PixivTagTranslation] = None


class PixivArtworkTags(BasePixivModel):
    """Pixiv 作品 tag 属性"""
    tags: list[PixivTag]
    authorId: Optional[int] = None
    isLocked: Optional[bool] = None
    writable: Optional[bool] = None

    @property
    def all_tags(self) -> list[str]:
        _tags = [x.tag for x in self.tags]
        _tags.extend([x.translation.en for x in self.tags if x.translation is not None])
        return _tags


class PixivArtworkMainUrl(BasePixivModel):
    """Pixiv 作品主图链接"""
    mini: AnyHttpUrl
    original: AnyHttpUrl
    regular: AnyHttpUrl
    small: AnyHttpUrl
    thumb: AnyHttpUrl


class PixivArtworkBody(BasePixivModel):
    """Pixiv 作品信息 Body"""
    id: int
    illustId: int
    illustTitle: str
    illustType: int
    illustComment: str
    userAccount: str
    userId: int
    userName: str
    title: str
    description: str
    width: int
    height: int
    xRestrict: int
    aiType: int
    tags: PixivArtworkTags
    urls: PixivArtworkMainUrl
    pageCount: int

    # 作品相关统计信息
    likeCount: int
    bookmarkCount: int
    viewCount: int
    commentCount: int

    @property
    def parsed_description(self) -> str:
        if not self.description:
            return ''

        description_html = etree.HTML(self.description)
        for br in description_html.xpath("*//br"):
            br.tail = '\n' + br.tail if br.tail else '\n'  # replace br tag

        return ''.join(text for x in description_html.xpath('/html/body/*') for text in x.itertext())


class PixivArtworkDataModel(BasePixivModel):
    """Pixiv 作品信息 Model"""
    body: PixivArtworkBody
    error: bool
    message: str


class PixivArtworkPageUrl(BasePixivModel):
    """Pixiv 作品多页链接"""
    original: AnyHttpUrl
    regular: AnyHttpUrl
    small: AnyHttpUrl
    thumb_mini: AnyHttpUrl


class PixivArtworkAllPages(BasePixivModel):
    """Pixiv 作品多页分类汇总"""
    original: list[AnyHttpUrl]
    regular: list[AnyHttpUrl]
    small: list[AnyHttpUrl]
    thumb_mini: list[AnyHttpUrl]


class PixivArtworkPageUrlContent(BasePixivModel):
    """Pixiv 作品多页链接内容"""
    urls: PixivArtworkPageUrl
    width: int
    height: int


class PixivArtworkPageModel(BasePixivModel):
    """Pixiv 作品多页信息"""
    body: list[PixivArtworkPageUrlContent]
    error: bool
    message: str

    @property
    def index_page(self) -> dict[int, PixivArtworkPageUrl]:
        if self.error:
            raise ValueError('Artwork pages data status is error')
        return {index: x.urls for index, x in enumerate(self.body)}

    @property
    def type_page(self) -> PixivArtworkAllPages:
        if self.error:
            raise ValueError('Artwork pages data status is error')
        _pages_data = {
            'original': [x.urls.original for x in self.body],
            'regular': [x.urls.regular for x in self.body],
            'small': [x.urls.small for x in self.body],
            'thumb_mini': [x.urls.thumb_mini for x in self.body]
        }
        return PixivArtworkAllPages.model_validate(_pages_data)


class PixivArtworkUgoiraFrames(BasePixivModel):
    """Pixiv 作品动图帧信息"""
    delay: int
    file: str


class PixivArtworkUgoiraMetaBody(BasePixivModel):
    """Pixiv 作品动图信息 Body"""
    frames: list[PixivArtworkUgoiraFrames]
    mime_type: str
    originalSrc: AnyHttpUrl
    src: AnyHttpUrl


class PixivArtworkUgoiraMeta(BasePixivModel):
    """Pixiv 作品动图信息"""
    body: PixivArtworkUgoiraMetaBody
    error: bool
    message: str


class PixivArtworkCompleteDataModel(BasePixivModel):
    """完整版 Pixiv 作品信息(用于模块数据处理)"""
    illust_type: int
    pid: int
    title: str
    sanity_level: int
    is_r18: bool
    ai_level: int
    is_ai: bool
    uid: int
    uname: str
    description: str
    tags: list[str]
    url: AnyHttpUrl
    width: int
    height: int
    like_count: int
    bookmark_count: int
    view_count: int
    comment_count: int
    page_count: int
    orig_url: AnyHttpUrl
    regular_url: AnyHttpUrl
    all_url: PixivArtworkAllPages
    all_page: dict[int, PixivArtworkPageUrl]
    ugoira_meta: Optional[PixivArtworkUgoiraMetaBody] = None


class PixivArtworkRecommendModel(BasePixivModel):
    """Pixiv 作品的相关推荐作品信息"""
    illusts: list[PixivSearchingData]
    nextIds: list[int]


class PixivArtworkPreviewRequestModel(BasePixivModel):
    """请求 PixivArtworkPreview 的入参"""
    desc_text: str
    request_url: AnyHttpUrl


__all__ = [
    'PixivArtworkDataModel',
    'PixivArtworkPageModel',
    'PixivArtworkUgoiraMeta',
    'PixivArtworkCompleteDataModel',
    'PixivArtworkRecommendModel',
    'PixivArtworkPreviewRequestModel'
]
