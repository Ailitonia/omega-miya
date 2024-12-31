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

from pydantic import BaseModel, ConfigDict


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
    is_held: bool = True
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


class Artist(BaseMoebooruModel):
    id: int
    name: str
    alias_id: int | None = None
    group_id: int | None = None
    urls: list[str]


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
]
