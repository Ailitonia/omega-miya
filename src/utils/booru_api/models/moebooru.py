"""
@Author         : Ailitonia
@Date           : 2024/8/14 10:50:01
@FileName       : moebooru.py
@Project        : omega-miya
@Description    : moebooru models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, RootModel, field_validator


class BaseMoebooruModel(BaseModel):
    """Moebooru 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class Post(BaseMoebooruModel):
    id: int
    author: str
    creator_id: int | None = None
    approver_id: int | None = None
    tags: str
    rating: Literal['s', 'q', 'e']
    change: int
    source: str
    score: int
    md5: str
    width: int
    height: int
    preview_width: int
    preview_height: int
    actual_preview_width: int | None = None
    actual_preview_height: int | None = None
    sample_height: int
    sample_width: int
    sample_file_size: int | None = None
    jpeg_width: int | None = None
    jpeg_height: int | None = None
    jpeg_file_size: int | None = None
    file_ext: str | None = None
    file_size: int
    file_url: str | None = None
    jpeg_url: str | None = None
    preview_url: str | None = None
    sample_url: str | None = None
    frames_pending_string: str | None = None
    frames_pending: list[Any] | None = None
    frames_string: str | None = None
    frames: list[Any] | None = None
    parent_id: int | None = None
    has_children: bool
    status: str
    is_rating_locked: bool = False
    is_shown_in_index: bool = True
    is_pending: bool = False
    is_held: bool = False
    is_note_locked: bool = False
    last_noted_at: int | None = None
    last_commented_at: int | None = None
    created_at: Any = None
    updated_at: Any = None


class SimilarPosts(BaseMoebooruModel):
    posts: list[Post]
    search_id: int | None = None
    success: bool


class Tag(BaseMoebooruModel):
    id: int
    name: str
    count: int
    type: int
    ambiguous: bool


class TagsRelated(RootModel[dict[str, list[tuple[str, int]]]]):
    """tag/related 响应

    形状: {查询标签: [[相关标签名, 相关计数], ...]}; 上游计数为字符串, 解析时归一为 int;
    首个元素通常为查询标签自身
    """


class Artist(BaseMoebooruModel):
    id: int
    name: str
    alias_id: int | None = None
    group_id: int | None = None
    urls: list[str]

    @field_validator('urls', mode='before')
    @classmethod
    def _split_urls(cls, v: str | list[str]) -> list[str]:
        # 响应中该字段可能为空格分隔字符串 (Danbooru 1.x 兼容形态) 或数组, 统一为列表
        if isinstance(v, str):
            return v.split()
        return v


class Comment(BaseMoebooruModel):
    id: int
    post_id: int
    creator: str
    creator_id: int | None = None  # Anonymous creator
    body: str
    created_at: Any = None


class Wiki(BaseMoebooruModel):
    id: int
    title: str
    body: str
    updater_id: int
    locked: bool
    version: int
    created_at: Any = None
    updated_at: Any = None


class Note(BaseMoebooruModel):
    id: int
    x: int
    y: int
    width: int
    height: int
    is_active: bool
    creator_id: int | None = None  # Anonymous creator
    post_id: int
    body: str
    version: int
    created_at: Any = None
    updated_at: Any = None


class NoteHistory(BaseMoebooruModel):
    """note/history 响应项"""
    x: int
    y: int
    width: int
    height: int
    is_active: bool
    creator_id: int | None = None  # Anonymous creator
    post_id: int
    body: str
    version: int
    created_at: Any = None
    updated_at: Any = None


class User(BaseMoebooruModel):
    id: int
    name: str


class Forum(BaseMoebooruModel):
    id: int
    parent_id: int | None = None
    creator: str
    creator_id: int | None = None  # Anonymous creator
    title: str
    body: str
    pages: int
    updated_at: Any = None


class Pool(BaseMoebooruModel):
    id: int
    name: str
    user_id: int
    is_public: bool
    post_count: int
    description: str | None = None
    posts: list[Post] | None = None
    created_at: Any = None
    updated_at: Any = None


class FavoritedUsers(BaseMoebooruModel):
    """favorite/list_users 响应: 上游为逗号分隔用户名字符串, 经校验器拆分为列表"""

    favorited_users: list[str]

    @field_validator('favorited_users', mode='before')
    @classmethod
    def _split_favorited_users(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [name for name in v.split(',') if name]  # 无人收藏时为空串, 拆为空列表
        return v


__all__ = [
    'Post',
    'SimilarPosts',
    'Tag',
    'Artist',
    'Comment',
    'Wiki',
    'Note',
    'User',
    'Forum',
    'Pool',
    'FavoritedUsers',
    'NoteHistory',
    'TagsRelated',
]
