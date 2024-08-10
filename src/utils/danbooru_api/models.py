"""
@Author         : Ailitonia
@Date           : 2024/8/2 13:52:14
@FileName       : models.py
@Project        : omega-miya
@Description    : Danbooru Models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from enum import IntEnum, StrEnum, unique
from typing import Any, Literal, Optional, Union, TypeVar

from pydantic import BaseModel, ConfigDict, Field, IPvAnyNetwork


class BaseDanbooruModel(BaseModel):
    """Danbooru 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


"""Versioned Types"""


class Artist(BaseDanbooruModel):
    id: int
    name: str
    group_name: str
    other_names: list[str]
    is_banned: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class ArtistCommentary(BaseDanbooruModel):
    id: int
    post_id: int
    original_title: str
    original_description: str
    translated_title: str
    translated_description: str
    created_at: datetime
    updated_at: datetime


class Note(BaseDanbooruModel):
    id: int
    post_id: int
    body: str
    x: int
    y: int
    width: int
    height: int
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class Pool(BaseDanbooruModel):
    id: int
    name: str
    description: str
    post_ids: list[int]
    category: Literal['series', 'collection']
    is_deleted: bool
    is_active: Optional[bool] = None  # unused
    created_at: datetime
    updated_at: datetime


class PostVariant(BaseDanbooruModel):
    url: str
    width: int
    height: int
    file_ext: str


class PostVariantType180(PostVariant):
    type: Literal['180x180']


class PostVariantType360(PostVariant):
    type: Literal['360x360']


class PostVariantType720(PostVariant):
    type: Literal['720x720']


class PostVariantTypeSample(PostVariant):
    type: Literal['sample']


class PostVariantTypeFull(PostVariant):
    type: Literal['full']


class PostVariantTypeOriginal(PostVariant):
    type: Literal['original']


type PostVariantsType = Union[
    PostVariantType180,
    PostVariantType360,
    PostVariantType720,
    PostVariantTypeSample,
    PostVariantTypeFull,
    PostVariantTypeOriginal
]

PostVariant_T = TypeVar('PostVariant_T', bound=PostVariant)


class PostMediaAsset(BaseDanbooruModel):
    id: int
    md5: Optional[str] = None
    file_key: Optional[str] = None
    file_ext: str
    file_size: int
    image_width: int
    image_height: int
    duration: Optional[Any] = None
    status: str
    is_public: bool
    pixel_hash: str
    variants: Optional[list[PostVariantsType]] = None
    created_at: datetime
    updated_at: datetime

    def _get_variant(self, type_: type[PostVariant_T]) -> PostVariant_T | None:
        if self.variants is None:
            return None

        for variant in self.variants:
            if isinstance(variant, type_):
                return variant
        else:
            return None

    @property
    def variant_type_180(self) -> PostVariantType180 | None:
        return self._get_variant(type_=PostVariantType180)

    @property
    def variant_type_360(self) -> PostVariantType360 | None:
        return self._get_variant(type_=PostVariantType360)

    @property
    def variant_type_720(self) -> PostVariantType720 | None:
        return self._get_variant(type_=PostVariantType720)

    @property
    def variant_type_sample(self) -> PostVariantTypeSample | None:
        return self._get_variant(type_=PostVariantTypeSample)

    @property
    def variant_type_full(self) -> PostVariantTypeFull | None:
        return self._get_variant(type_=PostVariantTypeFull)

    @property
    def variant_type_original(self) -> PostVariantTypeOriginal | None:
        return self._get_variant(type_=PostVariantTypeOriginal)


class Post(BaseDanbooruModel):
    id: int
    uploader_id: int
    approver_id: Optional[int]
    is_banned: bool
    is_deleted: bool
    is_flagged: bool
    is_pending: bool
    tag_string: str
    tag_string_general: str
    tag_string_artist: str
    tag_string_copyright: str
    tag_string_character: str
    tag_string_meta: str
    tag_count_general: int
    tag_count_artist: int
    tag_count_copyright: int
    tag_count_character: int
    tag_count_meta: int
    rating: Optional[Literal['g', 's', 'q', 'e']]  # includes [g, s, q, e]
    parent_id: Optional[int]
    has_children: bool
    has_active_children: bool
    has_visible_children: bool
    has_large: bool
    image_width: int
    image_height: int
    source: str
    md5: Optional[str] = None  # some image need Gold+ account
    file_url: Optional[str] = None  # some image need Gold+ account
    large_file_url: Optional[str] = None  # some image need Gold+ account
    preview_file_url: Optional[str] = None  # some image need Gold+ account
    file_ext: str
    file_size: int
    score: int
    up_score: int
    down_score: int
    fav_count: int
    last_comment_bumped_at: Optional[datetime]
    last_noted_at: Optional[datetime]
    media_asset: PostMediaAsset  # not in api docs but it actually exists
    created_at: datetime
    updated_at: datetime


class Wiki(BaseDanbooruModel):
    id: int
    title: str
    body: str
    other_names: list[str]
    is_deleted: bool
    locked: bool = Field(alias='is_locked')
    created_at: datetime
    updated_at: datetime


"""Type Versions"""


class ArtistVersion(BaseDanbooruModel):
    id: int
    artist_id: int
    name: str
    urls: list[str]
    other_names: list[str]
    group_name: str
    is_banned: bool
    updater_id: int
    created_at: datetime
    updated_at: datetime
    updater_addr_ip: Optional[IPvAnyNetwork] = None  # Limited to Moderator+


class ArtistCommentaryVersion(BaseDanbooruModel):
    id: int
    post_id: int
    original_title: str
    original_description: str
    translated_title: str
    translated_description: str
    updater_id: int
    created_at: datetime
    updated_at: datetime
    updater_addr_ip: Optional[IPvAnyNetwork] = None  # Limited to Moderator+


class NoteVersion(BaseDanbooruModel):
    id: int
    note_id: int
    post_id: int
    x: int
    y: int
    width: int
    height: int
    body: str
    is_active: bool
    version: int
    updater_id: int
    created_at: datetime
    updated_at: datetime
    updater_addr_ip: Optional[IPvAnyNetwork] = None  # Limited to Moderator+


class PoolVersion(BaseDanbooruModel):
    id: int
    pool_id: int
    name: str
    post_ids: list[int]
    added_post_ids: list[int]
    removed_post_ids: list[int]
    description: str
    category: Literal['collection', 'series']
    name_changed: bool
    description_changed: bool
    is_active: Optional[bool] = None  # unused
    is_deleted: bool
    boolean: Optional[bool] = None  # unused
    version: int
    updater_id: int
    created_at: datetime
    updated_at: datetime
    updater_addr_ip: Optional[IPvAnyNetwork] = None  # Limited to Moderator+


class PostVersion(BaseDanbooruModel):
    id: int
    post_id: int
    tags: str  # space delineated, tag format
    added_tags: list[str]  # tag format
    removed_tags: list[str]  # tag format
    rating: Literal['g', 's', 'q', 'e']
    parent_id: Optional[int]
    source: str
    rating_changed: bool
    parent_changed: bool
    source_changed: bool
    version: int
    updater_id: int
    created_at: Optional[datetime] = None  # Actually not exists
    updated_at: datetime
    updater_addr_ip: Optional[IPvAnyNetwork] = None  # Limited to Moderator+


class WikiPageVersion(BaseDanbooruModel):
    id: int
    wiki_page_id: int
    title: str  # tag format
    body: str
    other_names: list[str]
    is_locked: bool
    is_deleted: bool
    updater_id: int
    created_at: datetime
    updated_at: datetime
    updater_addr_ip: Optional[IPvAnyNetwork] = None  # Limited to Moderator+


"""Non-versioned Types"""


class Comment(BaseDanbooruModel):
    id: int
    post_id: int
    body: str
    score: int
    is_deleted: bool
    is_sticky: bool
    do_not_bump_post: bool
    creator_id: int
    updater_id: int
    created_at: datetime
    updated_at: datetime
    creator_ip_addr: Optional[IPvAnyNetwork] = None  # Limited to Moderator+
    updater_ip_addr: Optional[IPvAnyNetwork] = None  # Limited to Moderator+


class Dmail(BaseDanbooruModel):
    id: int
    owner_id: int
    to_id: int
    from_id: int
    title: str
    body: str
    is_read: bool
    is_deleted: bool
    is_spam: Optional[bool] = None  # obsolete
    key: bool
    created_at: datetime
    updated_at: datetime


class ForumPost(BaseDanbooruModel):
    id: int
    topic_id: int
    body: str
    is_deleted: bool
    creator_id: int
    updater_id: int
    created_at: datetime
    updated_at: datetime


@unique
class ForumTopicCategoryID(IntEnum):
    General = 0
    Tags = 1
    BugsFeatures = 2


class ForumTopic(BaseDanbooruModel):
    id: int
    title: str
    category_id: ForumTopicCategoryID
    response_count: int
    min_level: int  # Corresponds to the level of user (API:Users)
    is_deleted: bool
    is_sticky: bool
    is_locked: bool
    creator_id: int
    updater_id: int
    created_at: datetime
    updated_at: datetime


@unique
class PostAppealStatus(StrEnum):
    pending = 'pending'
    succeeded = 'succeeded'
    rejected = 'rejected'


class PostAppeal(BaseDanbooruModel):
    id: int
    post_id: int
    reason: str
    status: PostAppealStatus
    creator_id: int
    created_at: datetime
    updated_at: datetime


@unique
class PostFlagCategory(StrEnum):
    normal = 'normal'
    unapproved = 'unapproved'
    rejected = 'rejected'


@unique
class PostFlagStatus(StrEnum):
    pending = 'pending'
    succeeded = 'succeeded'
    rejected = 'rejected'


class PostFlag(BaseDanbooruModel):
    id: int
    post_id: int
    reason: str
    status: PostFlagStatus
    category: PostFlagCategory  # Not in API docs but it exists
    is_resolved: bool
    creator_id: Optional[int] = None  # limited to Moderator+ or the flag creator
    created_at: datetime
    updated_at: datetime


@unique
class TagCategory(IntEnum):
    General = 0
    Artist = 1
    Copyright = 3
    Character = 4
    Meta = 5


class Tag(BaseDanbooruModel):
    id: int
    name: str
    category: TagCategory
    post_count: int
    is_deprecated: bool
    created_at: datetime
    updated_at: datetime
    words: Optional[list[str]] = None  # Not in API docs but it exists, the split words of tag


class TagAlias(BaseDanbooruModel):
    id: int
    antecedent_name: str
    consequent_name: str
    status: Literal['active', 'deleted', 'retired']
    reason: Optional[str] = None  # unused
    forum_topic_id: Optional[int]
    forum_post_id: Optional[int]
    creator_id: int
    approver_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class TagImplication(BaseDanbooruModel):
    id: int
    antecedent_name: str
    consequent_name: str
    status: Literal['active', 'deleted', 'retired']
    reason: Optional[str] = None  # unused
    forum_topic_id: Optional[int]
    forum_post_id: Optional[int]
    creator_id: int
    approver_id: Optional[int]
    created_at: datetime
    updated_at: datetime


class Upload(BaseDanbooruModel):
    id: int
    uploader_id: int
    source: str
    referer_url: str
    media_asset_count: int
    status: str
    error: Optional[str]
    created_at: datetime
    updated_at: datetime


class User(BaseDanbooruModel):
    id: int
    name: str
    level: Literal[10, 20, 30, 31, 32, 40, 50]
    level_string: Optional[str] = None
    inviter_id: Optional[int]
    post_update_count: int
    note_update_count: int
    post_upload_count: int
    favorite_count: Optional[int] = None
    unread_dmail_count: Optional[int] = None
    is_banned: bool
    is_deleted: Optional[bool] = None
    receive_email_notifications: Optional[bool] = None
    always_resize_images: Optional[bool] = None
    enable_post_navigation: Optional[bool] = None
    new_post_navigation_layout: Optional[bool] = None
    enable_private_favorites: Optional[bool] = None
    enable_sequential_post_navigation: Optional[bool] = None
    hide_deleted_posts: Optional[bool] = None
    style_usernames: Optional[bool] = None
    enable_auto_complete: Optional[bool] = None
    show_deleted_children: Optional[bool] = None
    disable_categorized_saved_searches: Optional[bool] = None
    disable_tagged_filenames: Optional[bool] = None
    disable_cropped_thumbnails: Optional[bool] = None
    disable_mobile_gestures: Optional[bool] = None
    enable_safe_mode: Optional[bool] = None
    enable_desktop_mode: Optional[bool] = None
    disable_post_tooltips: Optional[bool] = None
    enable_recommended_posts: Optional[bool] = None
    requires_verification: Optional[bool] = None
    is_verified: Optional[bool] = None
    bit_prefs: Optional[int] = None  # Each bit stores a boolean value. See Bit fields below for more information.
    theme: Optional[Literal['auto', 'light', 'dark']] = None
    favorite_tags: Optional[str] = None
    blacklisted_tags: Optional[str] = None
    comment_threshold: Optional[int] = None
    timezone: Optional[str] = None
    per_page: Optional[int] = None
    default_image_size: Optional[Literal['large', 'original']] = None
    custom_css: Optional[str] = None
    upload_points: Optional[str] = None
    time_zone: Optional[str] = None
    show_deleted_posts: Optional[bool] = None
    statement_timeout: Optional[int] = None
    favorite_group_limit: Optional[int] = None
    tag_query_limit: Optional[int] = None
    max_saved_searches: Optional[int] = None
    wiki_page_version_count: Optional[int] = None
    artist_version_count: Optional[int] = None
    artist_commentary_version_count: Optional[int] = None
    pool_version_count: Optional[int] = None
    forum_post_count: Optional[int] = None
    comment_count: Optional[int] = None
    favorite_group_count: Optional[int] = None
    appeal_count: Optional[int] = None
    flag_count: Optional[int] = None
    positive_feedback_count: Optional[int] = None
    neutral_feedback_count: Optional[int] = None
    negative_feedback_count: Optional[int] = None
    last_forum_read_at: Optional[datetime] = None
    last_logged_in_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


__all__ = [
    'Artist',
    'ArtistCommentary',
    'Note',
    'Pool',
    'Post',
    'PostMediaAsset',
    'PostVariantsType',
    'Wiki',
    'ArtistVersion',
    'ArtistCommentaryVersion',
    'NoteVersion',
    'PoolVersion',
    'PostVersion',
    'WikiPageVersion',
    'Comment',
    'Dmail',
    'ForumPost',
    'ForumTopic',
    'PostAppeal',
    'PostFlag',
    'Tag',
    'TagAlias',
    'TagImplication',
    'Upload',
    'User',
]
