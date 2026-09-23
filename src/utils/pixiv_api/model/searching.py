"""
@Author         : Ailitonia
@Date           : 2022/04/05 22:53
@FileName       : searching.py
@Project        : nonebot2_miya
@Description    : Pixiv Searching Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pydantic import Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseArtworkData, BaseNovelData, BasePixivModel


class _NovelData(BaseNovelData):
    useWordCount: bool
    isOriginal: bool
    isMasked: bool
    createDate: str
    updateDate: str


class _Novel(BasePixivModel):
    """搜索结果小说内容"""
    data: list[_NovelData] = Field(default_factory=list)
    total: int = Field(default=0)


class _ArtworkData(BaseArtworkData):
    isUnlisted: bool
    isMasked: bool
    isOriginal: bool
    url: AnyHttpUrl
    createDate: str
    updateDate: str


class _Popular(BasePixivModel):
    """搜索结果热门作品内容"""
    recent: list[_ArtworkData] = Field(default_factory=list)
    permanent: list[_ArtworkData] = Field(default_factory=list)


class _IllustManga(BasePixivModel):
    """搜索结果插画漫画内容"""
    data: list[_ArtworkData] = Field(default_factory=list)
    total: int = Field(default=0)


class _CollectionData(BasePixivModel):
    id: str
    title: str
    tags: list[str] = Field(default_factory=list)
    userId: str
    userName: str
    profileImageUrl: AnyHttpUrl | None = Field(default=None)
    thumbnailImageUrl: AnyHttpUrl | None = Field(default=None)
    caption: str
    language: str
    xRestrict: int
    commentOff: bool
    isSpoiler: bool
    isBookmarkable: bool
    bookmarkCount: int
    viewCount: int
    status: str
    publishedDateTime: str


class _Collection(BasePixivModel):
    """搜索结果珍藏册内容"""
    data: list[_CollectionData] = Field(default_factory=list)
    total: int = Field(default=0)


class _SearchingResultBody(BasePixivModel):
    """搜索结果内容"""
    illustManga: _IllustManga = Field(default_factory=_IllustManga)
    illust: _IllustManga = Field(default_factory=_IllustManga)
    manga: _IllustManga = Field(default_factory=_IllustManga)
    novel: _Novel = Field(default_factory=_Novel)
    collection: _Collection = Field(default_factory=_Collection)
    popular: _Popular = Field(default_factory=_Popular)
    relatedTags: list[str] = Field(default_factory=list)
    tagTranslation: dict[str, dict[str, str]] = Field(default_factory=dict)


class PixivSearchingResult(BasePixivModel):
    """Pixiv 搜索结果数据"""
    body: _SearchingResultBody
    error: bool
    message: str = Field(default_factory=str)

    @property
    def artworks(self) -> list[_ArtworkData]:
        if self.error:
            raise ValueError('Search result status is error')
        return [
            data
            for content in (self.body.illustManga, self.body.illust, self.body.manga)
            for data in content.data
        ]


__all__ = [
    'PixivSearchingResult',
]
