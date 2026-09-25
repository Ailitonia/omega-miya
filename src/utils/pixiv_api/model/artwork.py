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
from pydantic import Field, model_validator

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseArtworkData, BasePixivModel


class _IllustTagItem(BasePixivModel):
    tag: str
    locked: bool
    deletable: bool
    userId: str | None = Field(default=None)
    translation: dict[str, str] = Field(default_factory=dict)
    userName: str | None = Field(default=None)


class _IllustTags(BasePixivModel):
    tags: list[_IllustTagItem] = Field(default_factory=list)
    authorId: str | None = Field(default=None)
    isLocked: bool | None = Field(default=None)
    writable: bool | None = Field(default=None)

    @property
    def all_tags(self) -> list[str]:
        _tags = [x.tag for x in self.tags]
        _tags.extend([tag_t for tag in self.tags for tag_t in tag.translation.values()])
        return list(dict.fromkeys(_tags))


class _IllustUrls(BasePixivModel):
    mini: AnyHttpUrl
    thumb: AnyHttpUrl
    small: AnyHttpUrl
    regular: AnyHttpUrl
    original: AnyHttpUrl


class _IllustuserIllusts(BaseArtworkData):
    url: AnyHttpUrl
    createDate: str
    updateDate: str


class _IllustDataBody(BaseArtworkData):
    illustId: str
    illustTitle: str
    illustComment: str
    tag_info: _IllustTags = Field(default_factory=_IllustTags)
    urls: _IllustUrls
    userAccount: str
    userIllusts: dict[str, _IllustuserIllusts | None] = Field(default_factory=dict)

    @model_validator(mode='before')
    @classmethod
    def _migrate_tags_field(cls, values):
        """详情接口返回的 tags 为对象结构(与列表接口的 list[str] 不同), 迁移至 tag_info 字段避免与父类字段冲突"""
        if isinstance(values, dict) and isinstance(values.get('tags'), dict):
            values = {k: v for k, v in values.items() if k != 'tags'} | {'tag_info': values['tags']}
        return values

    # 作品相关统计信息
    bookmarkCount: int
    likeCount: int
    commentCount: int
    responseCount: int
    viewCount: int

    # 属性标识
    isOriginal: bool
    isUnlisted: bool
    isLoginOnly: bool

    @property
    def parsed_description(self) -> str:
        if not self.description:
            return ''

        description_html = etree.HTML(self.description)
        for br in description_html.iter('br'):
            br.tail = f'\n{br.tail or ""}'
        return ''.join(text for text in description_html.itertext())


class PixivIllustData(BasePixivModel):
    """Pixiv 作品数据"""
    body: _IllustDataBody
    error: bool
    message: str


class _IllustPageUrl(BasePixivModel):
    thumb_mini: AnyHttpUrl
    small: AnyHttpUrl
    regular: AnyHttpUrl
    original: AnyHttpUrl


class _IllustPageTypesUrl(BasePixivModel):
    thumb_mini: list[AnyHttpUrl]
    small: list[AnyHttpUrl]
    regular: list[AnyHttpUrl]
    original: list[AnyHttpUrl]


class _IllustPageItem(BasePixivModel):
    urls: _IllustPageUrl
    width: int
    height: int


class PixivIllustPages(BasePixivModel):
    """Pixiv 作品多页数据"""
    body: list[_IllustPageItem]
    error: bool
    message: str

    @property
    def index_pages(self) -> dict[int, _IllustPageUrl]:
        if self.error:
            raise ValueError('Artwork pages data status is error')
        return {index: x.urls for index, x in enumerate(self.body)}

    @property
    def type_pages(self) -> _IllustPageTypesUrl:
        if self.error:
            raise ValueError('Artwork pages data status is error')
        _pages_data = {
            'original': [x.urls.original for x in self.body],
            'regular': [x.urls.regular for x in self.body],
            'small': [x.urls.small for x in self.body],
            'thumb_mini': [x.urls.thumb_mini for x in self.body]
        }
        return _IllustPageTypesUrl.model_validate(_pages_data)


class _IllustUgoiraFrames(BasePixivModel):
    file: str
    delay: int


class _IllustUgoiraMetaBody(BasePixivModel):
    src: AnyHttpUrl
    originalSrc: AnyHttpUrl
    mime_type: str
    frames: list[_IllustUgoiraFrames]


class PixivIllustUgoiraMeta(BasePixivModel):
    """Pixiv 作品动图数据"""
    body: _IllustUgoiraMetaBody
    error: bool
    message: str


class PixivIllustFull(BasePixivModel):
    """汇总 Pixiv 作品全量数据"""
    pid: str
    illust_type: int
    is_ai: bool
    ai_level: int
    is_r18: bool
    sanity_level: int
    title: str
    description: str
    tags: list[str]
    uid: str
    uname: str
    width: int
    height: int
    bookmark_count: int
    like_count: int
    comment_count: int
    response_count: int
    view_count: int
    page_count: int
    url: AnyHttpUrl
    orig_url: AnyHttpUrl
    regular_url: AnyHttpUrl
    type_pages: _IllustPageTypesUrl
    index_pages: dict[int, _IllustPageUrl]
    ugoira_meta: _IllustUgoiraMetaBody | None = Field(default=None)


class _IllustRecommendBody(BasePixivModel):
    illusts: list[BaseArtworkData] = Field(default_factory=list)
    nextIds: list[str] = Field(default_factory=list)


class PixivIllustRecommend(BasePixivModel):
    """Pixiv 作品的相关推荐作品数据"""
    body: _IllustRecommendBody
    error: bool
    message: str


__all__ = [
    'PixivIllustData',
    'PixivIllustPages',
    'PixivIllustUgoiraMeta',
    'PixivIllustFull',
    'PixivIllustRecommend',
]
