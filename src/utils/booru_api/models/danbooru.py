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
from typing import Any, Literal, TypeVar

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
    is_active: bool | None = None  # unused
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


type PostVariantTypes = PostVariantType180 | PostVariantType360 | PostVariantType720 | PostVariantTypeSample | PostVariantTypeFull | PostVariantTypeOriginal

PostVariant_T = TypeVar('PostVariant_T', bound=PostVariant)


class PostMediaAsset(BaseDanbooruModel):
    id: int
    md5: str | None = None
    file_key: str | None = None
    file_ext: str
    file_size: int
    image_width: int
    image_height: int
    duration: Any | None = None
    status: str
    is_public: bool
    pixel_hash: str
    variants: list[PostVariantTypes] | None = None
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
    approver_id: int | None
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
    rating: Literal['g', 's', 'q', 'e'] | None  # includes [g, s, q, e]
    parent_id: int | None
    has_children: bool
    has_active_children: bool
    has_visible_children: bool
    has_large: bool
    image_width: int
    image_height: int
    source: str
    md5: str | None = None  # some image need Gold+ account
    file_url: str | None = None  # some image need Gold+ account
    large_file_url: str | None = None  # some image need Gold+ account
    preview_file_url: str | None = None  # some image need Gold+ account
    file_ext: str
    file_size: int
    score: int
    up_score: int
    down_score: int
    fav_count: int
    last_comment_bumped_at: datetime | None
    last_noted_at: datetime | None
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
    updater_addr_ip: IPvAnyNetwork | None = None  # Limited to Moderator+


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
    updater_addr_ip: IPvAnyNetwork | None = None  # Limited to Moderator+


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
    updater_addr_ip: IPvAnyNetwork | None = None  # Limited to Moderator+


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
    is_active: bool | None = None  # unused
    is_deleted: bool
    boolean: bool | None = None  # unused
    version: int
    updater_id: int
    created_at: datetime
    updated_at: datetime
    updater_addr_ip: IPvAnyNetwork | None = None  # Limited to Moderator+


class PostVersion(BaseDanbooruModel):
    id: int
    post_id: int
    tags: str  # space delineated, tag format
    added_tags: list[str]  # tag format
    removed_tags: list[str]  # tag format
    rating: Literal['g', 's', 'q', 'e']
    parent_id: int | None
    source: str
    rating_changed: bool
    parent_changed: bool
    source_changed: bool
    version: int
    updater_id: int
    created_at: datetime | None = None  # Actually not exists
    updated_at: datetime
    updater_addr_ip: IPvAnyNetwork | None = None  # Limited to Moderator+


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
    updater_addr_ip: IPvAnyNetwork | None = None  # Limited to Moderator+


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
    creator_ip_addr: IPvAnyNetwork | None = None  # Limited to Moderator+
    updater_ip_addr: IPvAnyNetwork | None = None  # Limited to Moderator+


class Dmail(BaseDanbooruModel):
    id: int
    owner_id: int
    to_id: int
    from_id: int
    title: str
    body: str
    is_read: bool
    is_deleted: bool
    is_spam: bool | None = None  # obsolete
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
    creator_id: int | None = None  # limited to Moderator+ or the flag creator
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
    words: list[str] | None = None  # Not in API docs but it exists, the split words of tag


class TagAlias(BaseDanbooruModel):
    id: int
    antecedent_name: str
    consequent_name: str
    status: Literal['active', 'deleted', 'retired']
    reason: str | None = None  # unused
    forum_topic_id: int | None
    forum_post_id: int | None
    creator_id: int
    approver_id: int | None
    created_at: datetime
    updated_at: datetime


class TagImplication(BaseDanbooruModel):
    id: int
    antecedent_name: str
    consequent_name: str
    status: Literal['active', 'deleted', 'retired']
    reason: str | None = None  # unused
    forum_topic_id: int | None
    forum_post_id: int | None
    creator_id: int
    approver_id: int | None
    created_at: datetime
    updated_at: datetime


class Upload(BaseDanbooruModel):
    id: int
    uploader_id: int
    source: str
    referer_url: str
    media_asset_count: int
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class User(BaseDanbooruModel):
    id: int
    name: str
    level: Literal[10, 20, 30, 31, 32, 40, 50]
    level_string: str | None = None
    inviter_id: int | None
    post_update_count: int
    note_update_count: int
    post_upload_count: int
    favorite_count: int | None = None
    unread_dmail_count: int | None = None
    is_banned: bool
    is_deleted: bool | None = None
    receive_email_notifications: bool | None = None
    always_resize_images: bool | None = None
    enable_post_navigation: bool | None = None
    new_post_navigation_layout: bool | None = None
    enable_private_favorites: bool | None = None
    enable_sequential_post_navigation: bool | None = None
    hide_deleted_posts: bool | None = None
    style_usernames: bool | None = None
    enable_auto_complete: bool | None = None
    show_deleted_children: bool | None = None
    disable_categorized_saved_searches: bool | None = None
    disable_tagged_filenames: bool | None = None
    disable_cropped_thumbnails: bool | None = None
    disable_mobile_gestures: bool | None = None
    enable_safe_mode: bool | None = None
    enable_desktop_mode: bool | None = None
    disable_post_tooltips: bool | None = None
    enable_recommended_posts: bool | None = None
    requires_verification: bool | None = None
    is_verified: bool | None = None
    bit_prefs: int | None = None  # Each bit stores a boolean value. See Bit fields below for more information.
    theme: Literal['auto', 'light', 'dark'] | None = None
    favorite_tags: str | None = None
    blacklisted_tags: str | None = None
    comment_threshold: int | None = None
    timezone: str | None = None
    per_page: int | None = None
    default_image_size: Literal['large', 'original'] | None = None
    custom_css: str | None = None
    upload_points: str | None = None
    time_zone: str | None = None
    show_deleted_posts: bool | None = None
    statement_timeout: int | None = None
    favorite_group_limit: int | None = None
    tag_query_limit: int | None = None
    max_saved_searches: int | None = None
    wiki_page_version_count: int | None = None
    artist_version_count: int | None = None
    artist_commentary_version_count: int | None = None
    pool_version_count: int | None = None
    forum_post_count: int | None = None
    comment_count: int | None = None
    favorite_group_count: int | None = None
    appeal_count: int | None = None
    flag_count: int | None = None
    positive_feedback_count: int | None = None
    neutral_feedback_count: int | None = None
    negative_feedback_count: int | None = None
    last_forum_read_at: datetime | None = None
    last_logged_in_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


__all__ = [
    'Artist',
    'ArtistCommentary',
    'Note',
    'Pool',
    'Post',
    'PostMediaAsset',
    'PostVariantTypes',
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
