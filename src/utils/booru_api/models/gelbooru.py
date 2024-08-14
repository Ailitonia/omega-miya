"""
@Author         : Ailitonia
@Date           : 2024/8/13 下午10:07
@FileName       : gelbooru
@Project        : nonebot2_miya
@Description    : Gelbooru models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from enum import StrEnum, unique
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BaseGelbooruModel(BaseModel):
    """Gelbooru 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class PostAttributes(BaseGelbooruModel):
    limit: int
    offset: int
    count: int


class BaseIndexData(BaseGelbooruModel):
    attributes: PostAttributes = Field(alias='@attributes')


@unique
class PostRating(StrEnum):
    general = 'general'
    sensitive = 'sensitive'
    questionable = 'questionable'
    explicit = 'explicit'


class Post(BaseGelbooruModel):
    id: int
    owner: str
    creator_id: int
    title: str
    tags: str
    rating: PostRating
    score: int
    change: int
    directory: str
    image: str
    md5: str
    source: str
    width: int
    height: int
    preview_width: int
    preview_height: int
    sample_height: int
    sample_width: int
    file_url: Optional[str] = None
    jpeg_url: Optional[str] = None
    preview_url: Optional[str] = None
    sample_url: Optional[str] = None
    parent_id: int
    sample: int
    has_children: bool
    has_comments: bool
    has_notes: bool
    status: str
    post_locked: int
    created_at: str


class PostsData(BaseIndexData):
    post: list[Post]

    @property
    def post_ids(self) -> list[int]:
        return [x.id for x in self.post]


class Tag(BaseGelbooruModel):
    id: int
    name: str
    count: int
    type: int
    ambiguous: int


class TagsData(BaseIndexData):
    tag: list[Tag]


class User(BaseGelbooruModel):
    id: int
    username: str
    active: int


class UsersData(BaseIndexData):
    user: list[User]


class Comment(BaseGelbooruModel):
    id: int
    post_id: int
    creator: str
    creator_id: int
    body: str


class CommentsData(BaseIndexData):
    comment: list[Comment]


__all__ = [
    'PostsData',
    'TagsData',
    'UsersData',
    'CommentsData',
]
