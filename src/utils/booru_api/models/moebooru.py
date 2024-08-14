"""
@Author         : Ailitonia
@Date           : 2024/8/14 10:50:01
@FileName       : moebooru.py
@Project        : omega-miya
@Description    : moebooru models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


class BaseMoebooruModel(BaseModel):
    """Moebooru 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class Post(BaseMoebooruModel):
    id: int
    author: str
    creator_id: int
    approver_id: Optional[int] = None
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
    actual_preview_width: Optional[int] = None
    actual_preview_height: Optional[int] = None
    sample_height: int
    sample_width: int
    sample_file_size: Optional[int] = None
    jpeg_width: Optional[int] = None
    jpeg_height: Optional[int] = None
    jpeg_file_size: Optional[int] = None
    file_ext: Optional[str] = None
    file_size: int
    file_url: Optional[str] = None
    jpeg_url: Optional[str] = None
    preview_url: Optional[str] = None
    sample_url: Optional[str] = None
    frames_pending_string: Optional[str] = None
    frames_pending: Optional[list[Any]] = None
    frames_string: Optional[str] = None
    frames: Optional[list[Any]] = None
    parent_id: Optional[int] = None
    has_children: bool
    status: str
    is_rating_locked: bool = False
    is_shown_in_index: bool = True
    is_pending: bool = False
    is_held: bool = True
    is_note_locked: bool = False
    last_noted_at: Optional[int] = None
    last_commented_at: Optional[int] = None
    created_at: Any = None
    updated_at: Any = None


class SimilarPosts(BaseMoebooruModel):
    posts: list[Post]
    search_id: Optional[int] = None
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
    alias_id: Optional[int] = None
    group_id: Optional[int] = None
    urls: list[str]


class Comment(BaseMoebooruModel):
    id: int
    post_id: int
    creator: str
    creator_id: Optional[int] = None  # Anonymous creator
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
    creator_id: Optional[int] = None  # Anonymous creator
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
    parent_id: Optional[int] = None
    creator: str
    creator_id: Optional[int] = None  # Anonymous creator
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
    description: Optional[str] = None
    posts: Optional[list[Post]] = None
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
