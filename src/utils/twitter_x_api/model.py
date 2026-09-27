"""
@Author         : Ailitonia
@Date           : 2026/9/27 22:51
@FileName       : model
@Project        : omega-miya
@Description    : Twitter Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.compat import OptionalUrlStr as OptionalUrl
from .misc import find_dict

_TWEET_CREATED_AT_FORMAT = '%a %b %d %H:%M:%S %z %Y'
"""推文/用户数据中的 created_at 时间格式"""


class TwitterBaseModel(BaseModel):
    """推特数据基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True)


class TwitterEntityUrl(TwitterBaseModel):
    """实体 URL 数据"""
    url: OptionalUrl = None
    display_url: str = ''
    expanded_url: OptionalUrl = None
    indices: list[int] = Field(default_factory=list)


class TwitterMediaVariant(TwitterBaseModel):
    """媒体视频流(变体)"""
    url: OptionalUrl = None
    bitrate: int | None = None
    content_type: str = ''


class TwitterMediaVideoInfo(TwitterBaseModel):
    """媒体视频信息"""
    aspect_ratio: list[int] = Field(default_factory=list)
    duration_millis: int | None = None
    variants: list[TwitterMediaVariant] = Field(default_factory=list)


class TwitterMedia(TwitterBaseModel):
    """推文媒体(图片/视频/GIF)"""
    id: str = Field(validation_alias='id_str')
    type: str = ''  # photo/video/animated_gif
    media_url: OptionalUrl = Field(default=None, validation_alias='media_url_https')
    url: OptionalUrl = None
    display_url: str = ''
    expanded_url: OptionalUrl = None
    source_status_id: str | None = Field(default=None, validation_alias='source_status_id_str')
    source_user_id: str | None = Field(default=None, validation_alias='source_user_id_str')
    width: int | None = None
    height: int | None = None
    video_info: TwitterMediaVideoInfo | None = None

    @model_validator(mode='before')
    @classmethod
    def _parse_original_info(cls, data: Any) -> Any:
        """从 original_info 中提取媒体宽高"""
        if isinstance(data, dict) and isinstance(data.get('original_info'), dict):
            data = {**data}
            original_info = data.pop('original_info')
            data.setdefault('width', original_info.get('width'))
            data.setdefault('height', original_info.get('height'))
        return data

    @property
    def streams(self) -> list[TwitterMediaVariant]:
        """视频流列表(仅视频/GIF 类型可用, 已过滤非视频变体)"""
        if self.video_info is None:
            return []
        return [x for x in self.video_info.variants if x.content_type.startswith('video')]


class TwitterCommunityNote(TwitterBaseModel):
    """社区注释(Community Note)"""
    id: str | None = None
    text: str | None = None


class TwitterUser(TwitterBaseModel):
    """X(Twitter) 用户数据"""
    id: str = Field(validation_alias='rest_id')
    created_at: str = ''
    name: str = ''
    screen_name: str = ''
    profile_image_url: OptionalUrl = Field(default=None, validation_alias='profile_image_url_https')
    profile_banner_url: OptionalUrl = None
    url: OptionalUrl = None
    location: str = ''
    description: str = ''
    description_urls: list[TwitterEntityUrl] = Field(default_factory=list)
    urls: list[TwitterEntityUrl] = Field(default_factory=list)
    pinned_tweet_ids: list[str] = Field(default_factory=list, validation_alias='pinned_tweet_ids_str')
    is_blue_verified: bool = False
    verified: bool = False
    possibly_sensitive: bool = False
    default_profile: bool = False
    default_profile_image: bool = False
    has_custom_timelines: bool = False
    followers_count: int = 0
    fast_followers_count: int = 0
    normal_followers_count: int = 0
    following_count: int = Field(default=0, validation_alias='friends_count')
    favourites_count: int = 0
    listed_count: int = 0
    media_count: int = 0
    statuses_count: int = 0
    is_translator: bool = False
    translator_type: str = ''
    withheld_in_countries: list[str] = Field(default_factory=list)
    protected: bool = False

    @model_validator(mode='before')
    @classmethod
    def _flatten_legacy(cls, data: Any) -> Any:
        """拍平接口返回中的 legacy 嵌套字段, 并提取实体 URL"""
        if not isinstance(data, dict) or not isinstance(data.get('legacy'), dict):
            return data
        merged = {**data['legacy'], **{k: v for k, v in data.items() if k != 'legacy'}}

        entities = merged.get('entities')
        if isinstance(entities, dict):
            description = entities.get('description')
            if isinstance(description, dict):
                merged['description_urls'] = description.get('urls') or []
            url_entities = entities.get('url')
            if isinstance(url_entities, dict):
                merged['urls'] = url_entities.get('urls') or []

        return merged

    @property
    def created_at_datetime(self) -> datetime | None:
        """账号创建时间(解析失败时返回 None)"""
        try:
            return datetime.strptime(self.created_at, _TWEET_CREATED_AT_FORMAT)
        except ValueError:
            return None


class TwitterTweet(TwitterBaseModel):
    """X(Twitter) 推文数据"""
    id: str = Field(validation_alias='rest_id')
    created_at: str = ''
    text: str = ''
    full_text: str = ''
    lang: str = ''
    user: TwitterUser | None = None
    in_reply_to: str | None = Field(default=None, validation_alias='in_reply_to_status_id_str')
    is_quote_status: bool = False
    possibly_sensitive: bool | None = None
    possibly_sensitive_editable: bool | None = None
    quote_count: int = 0
    reply_count: int = 0
    favorite_count: int = 0
    favorited: bool = False
    retweet_count: int = 0
    bookmark_count: int = 0
    bookmarked: bool = False
    view_count: str | None = None
    view_count_state: str | None = None
    has_community_notes: bool | None = None
    editable_until_msecs: int | None = None
    is_edit_eligible: bool | None = None
    edits_remaining: int | None = None
    edit_tweet_ids: list[str] = Field(default_factory=list)
    is_translatable: bool | None = None
    media: list[TwitterMedia] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    urls: list[TwitterEntityUrl] = Field(default_factory=list)
    quote: 'TwitterTweet | None' = None
    retweeted_tweet: 'TwitterTweet | None' = None
    community_note: TwitterCommunityNote | None = None
    has_card: bool = False
    thumbnail_title: str | None = None
    thumbnail_url: OptionalUrl = None

    @model_validator(mode='before')
    @classmethod
    def _parse_from_result(cls, data: Any) -> Any:
        """从 GraphQL 推文结果中解析推文数据

        处理 legacy 嵌套拍平/作者提取/note_tweet 长文本覆盖/引用与转发展开/卡片缩略图等
        """
        if not isinstance(data, dict):
            return data
        # 部分场景下推文数据被 tweet 键包裹
        if isinstance(data.get('tweet'), dict):
            data = data['tweet']
        legacy = data.get('legacy') if isinstance(data.get('legacy'), dict) else {}
        merged = {**legacy, **{k: v for k, v in data.items() if k != 'legacy'}}

        # 作者
        core = data.get('core')
        if isinstance(core, dict) and isinstance(core.get('user_results'), dict):
            merged['user'] = core['user_results'].get('result')

        # 浏览量
        views = data.get('views')
        if isinstance(views, dict):
            merged['view_count'] = views.get('count')
            merged['view_count_state'] = views.get('state')

        # 编辑信息
        edit_control = data.get('edit_control')
        if isinstance(edit_control, dict):
            merged['edit_tweet_ids'] = edit_control.get('edit_tweet_ids') or []
            merged['editable_until_msecs'] = edit_control.get('editable_until_msecs')
            merged['is_edit_eligible'] = edit_control.get('is_edit_eligible')
            merged['edits_remaining'] = edit_control.get('edits_remaining')

        merged['has_community_notes'] = data.get('has_birdwatch_notes')

        # 实体(媒体/URL/话题标签)
        entities = legacy.get('entities') if isinstance(legacy.get('entities'), dict) else {}
        merged['media'] = entities.get('media') or []

        # note_tweet 长文本覆盖(长推文)
        full_text = legacy.get('full_text')
        entity_urls = entities.get('urls')
        entity_hashtags = entities.get('hashtags') or []
        note_tweet_results = find_dict(data, 'note_tweet_results', find_one=True)
        if note_tweet_results:
            text_list = find_dict(note_tweet_results[0], 'text', find_one=True)
            if text_list:
                full_text = text_list[0]
            note_result = note_tweet_results[0].get('result') if isinstance(note_tweet_results[0], dict) else None
            note_entity_set = note_result.get('entity_set') if isinstance(note_result, dict) else None
            if isinstance(note_entity_set, dict):
                entity_urls = note_entity_set.get('urls')
                entity_hashtags = note_entity_set.get('hashtags') or []
        merged['text'] = legacy.get('full_text') or ''
        merged['full_text'] = full_text or ''
        merged['urls'] = entity_urls or []
        merged['hashtags'] = [x['text'] for x in entity_hashtags if isinstance(x, dict) and 'text' in x]

        # 引用推文(墓碑推文除外)
        quoted = data.get('quoted_status_result')
        if isinstance(quoted, dict) and isinstance(quoted.get('result'), dict):
            quoted_data = quoted['result']
            if isinstance(quoted_data.get('tweet'), dict):
                quoted_data = quoted_data['tweet']
            if quoted_data.get('__typename') != 'TweetTombstone' and 'core' in quoted_data and 'legacy' in quoted_data:
                merged['quote'] = quoted_data

        # 转推推文
        retweeted = merged.get('retweeted_status_result')
        if isinstance(retweeted, dict) and isinstance(retweeted.get('result'), dict):
            retweeted_data = retweeted['result']
            if isinstance(retweeted_data.get('tweet'), dict):
                retweeted_data = retweeted_data['tweet']
            if 'core' in retweeted_data and 'legacy' in retweeted_data:
                merged['retweeted_tweet'] = retweeted_data

        # 社区注释
        birdwatch = data.get('birdwatch_pivot')
        if isinstance(birdwatch, dict) and isinstance(birdwatch.get('note'), dict):
            subtitle = birdwatch.get('subtitle') if isinstance(birdwatch.get('subtitle'), dict) else {}
            merged['community_note'] = {
                'id': birdwatch['note'].get('rest_id'),
                'text': subtitle.get('text'),
            }

        # 卡片(链接预览缩略图等)
        card = data.get('card')
        merged['has_card'] = isinstance(card, dict)
        card_legacy = card.get('legacy') if isinstance(card, dict) else None
        binding_values = card_legacy.get('binding_values') if isinstance(card_legacy, dict) else None
        if isinstance(binding_values, list):
            values = {x.get('key'): x.get('value') for x in binding_values if isinstance(x, dict)}
            title = values.get('title')
            if isinstance(title, dict):
                merged['thumbnail_title'] = title.get('string_value')
            thumbnail = values.get('thumbnail_image_original')
            if isinstance(thumbnail, dict) and isinstance(thumbnail.get('image_value'), dict):
                merged['thumbnail_url'] = thumbnail['image_value'].get('url')

        return merged

    @property
    def created_at_datetime(self) -> datetime | None:
        """推文发布时间(解析失败时返回 None)"""
        try:
            return datetime.strptime(self.created_at, _TWEET_CREATED_AT_FORMAT)
        except ValueError:
            return None


TwitterTweet.model_rebuild()


class TwitterHighlightTweetsResult(TwitterBaseModel):
    """用户高光推文结果(带翻页游标)"""
    tweets: list[TwitterTweet] = Field(default_factory=list)
    next_cursor: str | None = None
    previous_cursor: str | None = None


class TwitterGuestActivateResult(TwitterBaseModel):
    """访客令牌激活接口返回"""
    guest_token: str


__all__ = [
    'TwitterBaseModel',
    'TwitterCommunityNote',
    'TwitterEntityUrl',
    'TwitterGuestActivateResult',
    'TwitterHighlightTweetsResult',
    'TwitterMedia',
    'TwitterMediaVariant',
    'TwitterMediaVideoInfo',
    'TwitterTweet',
    'TwitterUser',
]
