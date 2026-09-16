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

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class BaseGelbooruModel(BaseModel):
    """Gelbooru 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class IndexAttributes(BaseGelbooruModel):
    limit: int
    offset: int
    count: int


class BaseIndexData(BaseGelbooruModel):
    attributes: IndexAttributes = Field(alias='@attributes')


@unique
class PostRating(StrEnum):
    general = 'general'
    sensitive = 'sensitive'
    questionable = 'questionable'
    explicit = 'explicit'


class Post(BaseGelbooruModel):
    id: int
    owner: str
    # dapi 部分实现对无可值字段返回空串, 归一为 None; 0 为上游真实的"无"标记, 保留为 0
    creator_id: int | None = None
    title: str
    tags: str
    rating: PostRating
    score: int
    change: int
    directory: str
    image: str
    # dapi 文档未记载响应字段, 不同实现中该字段存在 md5/hash 两种命名, 兼容解析
    md5: str | None = Field(default=None, validation_alias=AliasChoices('md5', 'hash'))
    source: str
    width: int
    height: int
    preview_width: int
    preview_height: int
    sample_height: int
    sample_width: int
    file_url: str | None = None
    jpeg_url: str | None = None
    preview_url: str | None = None
    sample_url: str | None = None
    parent_id: int | None = None
    sample: int
    has_children: bool
    has_comments: bool
    has_notes: bool
    status: str
    post_locked: int
    created_at: str

    @field_validator('creator_id', 'parent_id', mode='before')
    @classmethod
    def _normalize_empty_to_none(cls, value: object) -> object:
        # 空串归一为 None, 避免单条坏记录导致整页解析失败
        return None if value == '' else value


class PostsData(BaseIndexData):
    # 空结果时 dapi 可能省略数组键, 默认空列表
    post: list[Post] = Field(default_factory=list)

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
    tag: list[Tag] = Field(default_factory=list)


class User(BaseGelbooruModel):
    id: int
    # dapi 文档未记载响应字段, 不同实现中该字段存在 username/name 两种命名, 兼容解析
    username: str = Field(validation_alias=AliasChoices('username', 'name'))
    active: int


class UsersData(BaseIndexData):
    user: list[User] = Field(default_factory=list)


class Comment(BaseGelbooruModel):
    id: int
    post_id: int
    creator: str
    creator_id: int
    body: str


class CommentsData(BaseIndexData):
    comment: list[Comment] = Field(default_factory=list)


__all__ = [
    'Comment',
    'Post',
    'PostsData',
    'PostRating',
    'Tag',
    'TagsData',
    'User',
    'UsersData',
    'CommentsData',
]
