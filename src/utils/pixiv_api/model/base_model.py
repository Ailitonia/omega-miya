"""
@Author         : Ailitonia
@Date           : 2022/04/06 2:10
@FileName       : base_model.py
@Project        : nonebot2_miya
@Description    : Pixiv Base Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pydantic import BaseModel, ConfigDict, Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl


class BasePixivModel(BaseModel):
    """Pixiv 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class _BookmarkData(BasePixivModel):
    id: str
    private: bool


class BaseArtworkData(BasePixivModel):
    """Pixiv 作品共有数据基类"""
    id: str
    title: str
    illustType: int
    aiType: int
    xRestrict: int
    restrict: int
    description: str
    tags: list[str] = Field(default_factory=list)
    userId: str
    userName: str
    profileImageUrl: AnyHttpUrl | None = Field(default=None)
    width: int
    height: int
    pageCount: int
    isBookmarkable: bool
    bookmarkData: _BookmarkData | None = Field(default=None)
    alt: str | None = Field(default=None)


class BaseNovelData(BasePixivModel):
    """Pixiv 小说共有数据基类"""
    id: str
    title: str
    genre: str
    aiType: int
    xRestrict: int
    restrict: int
    url: AnyHttpUrl
    tags: list[str] = Field(default_factory=list)
    userId: str
    userName: str
    profileImageUrl: AnyHttpUrl | None = Field(default=None)
    textCount: int
    wordCount: int
    readingTime: int
    description: str
    isBookmarkable: bool
    bookmarkData: _BookmarkData | None = Field(default=None)
    bookmarkCount: int
    language: str
    seriesId: str | None = Field(default=None)
    seriesTitle: str | None = Field(default=None)
    seriesContentOrder: int | None = Field(default=None)


class BaseUserData(BasePixivModel):
    """Pixiv 用户共有数据基类"""
    userId: str
    name: str
    isFollowed: bool
    isMypixiv: bool
    isBlocking: bool
    image: AnyHttpUrl
    imageBig: AnyHttpUrl
    premium: bool
    comment: str | None = Field(default=None)


__all__ = [
    'BaseArtworkData',
    'BaseNovelData',
    'BasePixivModel',
    'BaseUserData',
]
