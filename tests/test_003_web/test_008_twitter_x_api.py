"""
@Author         : Ailitonia
@Date           : 2026/9/28 00:32
@FileName       : test_008_twitter_x_api
@Project        : omega-miya
@Description    : Twitter(X) API 测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import base64
import os
from typing import TYPE_CHECKING, Any

import pytest
import ujson

if TYPE_CHECKING:
    from nonebot.drivers import Response

_TWITTER_LIVE_ENV = 'OMEGA_TWITTER_X_LIVE_TEST'
"""真实请求测试开关环境变量: 置 1 时启用(仅用户主动发起)"""

requires_live = pytest.mark.skipif(
    os.environ.get(_TWITTER_LIVE_ENV) != '1',
    reason=f'真实请求测试默认禁用, 需用户主动发起: 设置环境变量 {_TWITTER_LIVE_ENV}=1',
)


@pytest.fixture(scope='session')
def _twitter_api_ready(nonebug_init: None) -> None:
    """src.utils.twitter_x_api 导入期依赖 NoneBot 初始化(get_plugin_config), 离线用例的统一屏障"""


def _fake_response(content: Any, status_code: int = 200) -> 'Response':
    """构造携带 JSON 内容的 nonebot Response(罐装响应)"""
    from nonebot.drivers import Response

    return Response(status_code, content=ujson.dumps(content).encode('utf-8'))


# ================================================================== #
# 罐装 payload 构造(对照 twikit guest/user.py / guest/tweet.py 的字段集)
# ================================================================== #


def _user_result_payload(**overrides: Any) -> dict[str, Any]:
    """GraphQL 用户查询 result 节点最小有效 payload"""
    payload: dict[str, Any] = {
        '__typename': 'User',
        'rest_id': '783214',
        'is_blue_verified': True,
        'legacy': {
            'created_at': 'Wed May 23 06:01:13 +0000 2007',
            'name': 'X',
            'screen_name': 'X',
            'profile_image_url_https': 'https://pbs.twimg.com/profile_images/xxx_normal.jpg',
            'location': 'everywhere',
            'description': "What's happening?!",
            'entities': {'description': {'urls': []}},
            'pinned_tweet_ids_str': ['1234567890'],
            'verified': False,
            'possibly_sensitive': False,
            'default_profile': False,
            'default_profile_image': False,
            'has_custom_timelines': True,
            'followers_count': 100,
            'fast_followers_count': 0,
            'normal_followers_count': 100,
            'friends_count': 1,
            'favourites_count': 2,
            'listed_count': 3,
            'media_count': 4,
            'statuses_count': 5,
            'is_translator': False,
            'translator_type': 'none',
            'withheld_in_countries': [],
            'protected': False,
        },
    }
    payload.update(overrides)
    return payload


def _user_response(**overrides: Any) -> dict[str, Any]:
    """UserByScreenName / UserByRestId 完整响应包装"""
    return {'data': {'user': {'result': _user_result_payload(**overrides)}}}


def _tweet_result_payload(**overrides: Any) -> dict[str, Any]:
    """GraphQL 推文 result 节点最小有效 payload"""
    payload: dict[str, Any] = {
        '__typename': 'Tweet',
        'rest_id': '1780000000000000000',
        'core': {'user_results': {'result': _user_result_payload()}},
        'views': {'count': '12345', 'state': 'EnabledWithCount'},
        'edit_control': {
            'edit_tweet_ids': ['1780000000000000000'],
            'editable_until_msecs': 1713270000000,
            'is_edit_eligible': True,
            'edits_remaining': '5',
        },
        'is_translatable': True,
        'has_birdwatch_notes': False,
        'legacy': {
            'created_at': 'Tue Apr 16 10:00:00 +0000 2024',
            'full_text': 'hello https://t.co/abc #tag',
            'lang': 'en',
            'is_quote_status': False,
            'quote_count': 1,
            'reply_count': 2,
            'favorite_count': 3,
            'favorited': False,
            'retweet_count': 4,
            'entities': {
                'media': [{
                    'id_str': '1900000000000000000',
                    'type': 'photo',
                    'media_url_https': 'https://pbs.twimg.com/media/xxx.jpg',
                    'url': 'https://t.co/m',
                    'display_url': 'pic.x.com/m',
                    'expanded_url': 'https://x.com/X/status/1780/photo/1',
                    'original_info': {'width': 800, 'height': 600},
                }],
                'urls': [{
                    'url': 'https://t.co/abc',
                    'display_url': 'example.com',
                    'expanded_url': 'https://example.com/',
                    'indices': [6, 21],
                }],
                'hashtags': [{'text': 'tag', 'indices': [22, 26]}],
            },
        },
    }
    payload.update(overrides)
    return payload


def _timeline_entry(entry_id: str, tweet: dict[str, Any] | None = None) -> dict[str, Any]:
    """TimelineAddEntries 中的推文条目"""
    return {
        'entryId': entry_id,
        'sortIndex': '1',
        'content': {
            'entryType': 'TimelineTimelineItem',
            '__typename': 'TimelineTimelineItem',
            'itemContent': {
                'entryType': 'TimelineTimelineItem',
                '__typename': 'TimelineTimelineItem',
                'tweet_results': {'result': tweet if tweet is not None else _tweet_result_payload()},
            },
        },
    }


def _cursor_entry(entry_id: str, value: str) -> dict[str, Any]:
    """TimelineAddEntries 中的游标条目"""
    return {'entryId': entry_id, 'sortIndex': '2', 'content': {'entryType': 'TimelineTimelineCursor', 'value': value}}


def _timeline_response(entries: list[dict[str, Any]], timeline_key: str = 'timeline') -> dict[str, Any]:
    """UserTweets / UserHighlightsTweets 完整响应包装

    真实接口中 UserTweets 的键为 timeline_v2, UserHighlightsTweets 为 timeline;
    解析端 find_dict 与键路径无关, 此处参数用于让罐装响应贴近日线真实形状
    """
    return {'data': {'user': {'result': {timeline_key: {'timeline': {
        'instructions': [{'type': 'TimelineAddEntries', 'entries': entries, 'direction': 'Top'}
                         ]}}}}}}


# ================================================================== #
# 离线单元测试(罐装响应, 零网络, 默认运行)
# ================================================================== #


@pytest.mark.usefixtures('_twitter_api_ready')
class TestMiscHelpers:
    """misc.py 纯函数测试(零网络)"""

    def test_find_dict_nested(self) -> None:
        from src.utils.twitter_x_api.misc import find_dict

        obj = {'a': {'b': [{'target': 1}, {'c': 2}]}, 'target': 0}
        assert find_dict(obj, 'target') == [0, 1]
        assert find_dict(obj, 'target', find_one=True) == [0]
        assert find_dict(obj, 'missing') == []
        assert find_dict([{'x': {'y': 1}}], 'y') == [1]

    def test_find_entry_by_type(self) -> None:
        from src.utils.twitter_x_api.misc import find_entry_by_type

        entries = [{'type': 'TimelineTerminateTimeline'}, {'type': 'TimelineAddEntries', 'entries': [1]}]
        assert find_entry_by_type(entries, 'TimelineAddEntries') == {'type': 'TimelineAddEntries', 'entries': [1]}
        assert find_entry_by_type(entries, 'None') is None

    def test_flatten_params(self) -> None:
        from src.utils.twitter_x_api.misc import flatten_params

        result = flatten_params({'variables': {'a': 1, 'b': True}, 'features': {'f': False}, 'plain': 'x', 'n': 5})
        assert ujson.loads(result['variables']) == {'a': 1, 'b': True}
        assert ujson.loads(result['features']) == {'f': False}
        assert result['plain'] == 'x'
        assert result['n'] == 5

    def test_find_dict_find_one_with_none_value(self) -> None:
        # 目标键存在但值为 None 时仍视为找到(返回 [None]), 调用方需自行判空
        from src.utils.twitter_x_api.misc import find_dict

        assert find_dict({'result': None}, 'result', find_one=True) == [None]
        assert find_dict({'a': {'result': None}}, 'result', find_one=True) == [None]
        assert find_dict({'a': 1}, 'result', find_one=True) == []

    def test_find_dict_non_container_input(self) -> None:
        from src.utils.twitter_x_api.misc import find_dict

        assert find_dict(None, 'x') == []
        assert find_dict('str', 'x') == []
        assert find_dict(42, 'x') == []

    def test_find_entry_by_type_malformed(self) -> None:
        # M1 加固: 非 list 入参与非 dict 条目一律返回 None 而不抛异常
        from src.utils.twitter_x_api.misc import find_entry_by_type

        assert find_entry_by_type(None, 'TimelineAddEntries') is None
        assert find_entry_by_type('broken', 'TimelineAddEntries') is None
        assert find_entry_by_type({'type': 'TimelineAddEntries'}, 'TimelineAddEntries') is None
        assert find_entry_by_type(
            ['broken', None, {'type': 'TimelineAddEntries'}], 'TimelineAddEntries'
        ) == {'type': 'TimelineAddEntries'}

    def test_flatten_params_scalar_passthrough(self) -> None:
        # 非 dict/list 值原样透传, list 值序列化为 JSON 字符串
        from src.utils.twitter_x_api.misc import flatten_params

        result = flatten_params({'flag': True, 'count': 0, 'list_val': [1, 2], 'none_val': None})
        assert result['flag'] is True
        assert result['count'] == 0
        assert result['none_val'] is None
        assert ujson.loads(result['list_val']) == [1, 2]


@pytest.mark.usefixtures('_twitter_api_ready')
class TestConsts:
    """consts.py 与 twikit 参考实现的静态一致性(防意外漂移)"""

    def test_token_and_domain(self) -> None:
        from src.utils.twitter_x_api import consts

        assert consts.DOMAIN == 'x.com'
        assert consts.TOKEN.startswith('AAAAAAAAAAAAAAAAAAAAANRILg')

    def test_endpoint_urls(self) -> None:
        from src.utils.twitter_x_api import consts

        assert consts.GUEST_ACTIVATE_URL == 'https://api.x.com/1.1/guest/activate.json'
        assert consts.USER_BY_SCREEN_NAME_URL.endswith('/NimuplG1OB7Fd2btCLdBOw/UserByScreenName')
        assert consts.USER_BY_REST_ID_URL.endswith('/tD8zKvQzwY3kdx5yz6YmOw/UserByRestId')
        assert consts.USER_TWEETS_URL.endswith('/QWF3SzpHmykQHsQMixG0cg/UserTweets')
        assert consts.USER_HIGHLIGHTS_TWEETS_URL.endswith('/tHFm_XZc_NNi-CfUThwbNw/UserHighlightsTweets')
        assert consts.TWEET_RESULT_BY_REST_ID_URL.endswith('/Xl5pC_lBk_gcO2ItU39DQw/TweetResultByRestId')

    def test_features_keysets(self) -> None:
        from src.utils.twitter_x_api import consts

        # 键集与 twikit constants.py 同名 dict 逐项一致(FEATURES 21 / USER 11 / HIGHLIGHTS 24 / TWEET_RESULT 24)
        assert len(consts.FEATURES) == 21
        assert len(consts.USER_FEATURES) == 11
        assert len(consts.USER_HIGHLIGHTS_TWEETS_FEATURES) == 24
        assert len(consts.TWEET_RESULT_BY_REST_ID_FEATURES) == 24
        assert consts.FEATURES['rweb_video_timestamps_enabled'] is True
        assert consts.USER_FEATURES['hidden_profile_likes_enabled'] is True
        assert consts.TWEET_RESULT_BY_REST_ID_FEATURES['articles_preview_enabled'] is True


@pytest.mark.usefixtures('_twitter_api_ready')
class TestModels:
    """Pydantic 数据模型测试(零网络)"""

    def test_user_parse(self) -> None:
        from src.utils.twitter_x_api.model import TwitterUser

        user = TwitterUser.model_validate(_user_result_payload())
        assert user.id == '783214'
        assert user.screen_name == 'X'
        assert user.is_blue_verified is True
        assert user.following_count == 1  # friends_count 别名
        assert user.pinned_tweet_ids == ['1234567890']
        assert user.description_urls == []
        assert user.urls == []  # entities.url 缺失时归一空列表
        assert user.protected is False
        assert user.created_at_datetime is not None
        assert user.created_at_datetime.year == 2007

    def test_user_entities_url_extract(self) -> None:
        from src.utils.twitter_x_api.model import TwitterUser

        payload = _user_result_payload()
        payload['legacy']['entities'] = {
            'description': {'urls': [
                {'url': 'https://t.co/d', 'display_url': 'd.com', 'expanded_url': 'https://d.com/'}
            ]},
            'url': {'urls': [
                {'url': 'https://t.co/u', 'display_url': 'u.com', 'expanded_url': 'https://u.com/'}
            ]},
        }
        user = TwitterUser.model_validate(payload)
        assert user.description_urls[0].display_url == 'd.com'
        assert user.urls[0].expanded_url == 'https://u.com/'

    def test_user_no_legacy_passthrough(self) -> None:
        # 无 legacy 键时不拍平, rest_id 仍可解析
        from src.utils.twitter_x_api.model import TwitterUser

        assert TwitterUser.model_validate({'rest_id': '1'}).id == '1'

    def test_user_created_at_invalid(self) -> None:
        from src.utils.twitter_x_api.model import TwitterUser

        user = TwitterUser.model_validate(_user_result_payload(created_at='not a date'))
        assert user.created_at_datetime is None

    def test_tweet_parse(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        tweet = TwitterTweet.model_validate(_tweet_result_payload())
        assert tweet.id == '1780000000000000000'
        assert tweet.text == 'hello https://t.co/abc #tag'
        assert tweet.full_text == tweet.text
        assert tweet.view_count == '12345'
        assert tweet.view_count_state == 'EnabledWithCount'
        assert tweet.has_community_notes is False
        assert tweet.edit_tweet_ids == ['1780000000000000000']
        assert tweet.is_edit_eligible is True
        assert tweet.user is not None
        assert tweet.user.screen_name == 'X'
        assert tweet.urls[0].expanded_url == 'https://example.com/'
        assert tweet.hashtags == ['tag']
        assert tweet.created_at_datetime is not None
        assert tweet.media[0].width == 800  # original_info 提取
        assert tweet.media[0].media_url == 'https://pbs.twimg.com/media/xxx.jpg'

    def test_tweet_note_tweet_override(self) -> None:
        # 长推文: note_tweet 的 text/entity_set 覆盖 full_text/urls/hashtags
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['note_tweet_results'] = {'result': {
            'text': 'long text ' * 100,
            'entity_set': {
                'urls': [{'url': 'https://t.co/n', 'display_url': 'n.com', 'expanded_url': 'https://n.com/'}],
                'hashtags': [{'text': 'longtag'}],
            },
        }}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.text == 'hello https://t.co/abc #tag'  # text 保持 legacy full_text
        assert tweet.full_text == 'long text ' * 100
        assert tweet.urls[0].expanded_url == 'https://n.com/'
        assert tweet.hashtags == ['longtag']

    def test_tweet_quote(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['quoted_status_result'] = {'result': _tweet_result_payload(rest_id='1790000000000000000')}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.quote is not None
        assert tweet.quote.id == '1790000000000000000'

    def test_tweet_quote_tombstone_skipped(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['quoted_status_result'] = {'result': {'__typename': 'TweetTombstone', 'text': 'unavailable'}}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.quote is None

    def test_tweet_retweeted(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['legacy']['retweeted_status_result'] = {'result': _tweet_result_payload(rest_id='1800000000000000000')}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.retweeted_tweet is not None
        assert tweet.retweeted_tweet.id == '1800000000000000000'

    def test_tweet_retweeted_tombstone_skipped(self) -> None:
        # twikit 在此场景 KeyError 崩溃, 项目跳过
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['legacy']['retweeted_status_result'] = {'result': {'__typename': 'TweetTombstone'}}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.retweeted_tweet is None

    def test_tweet_community_note(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['birdwatch_pivot'] = {'note': {'rest_id': '1'}, 'subtitle': {'text': 'note text'}}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.community_note is not None
        assert tweet.community_note.id == '1'
        assert tweet.community_note.text == 'note text'

    def test_tweet_card_thumbnail(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['card'] = {'legacy': {'binding_values': [
            {'key': 'title', 'value': {'string_value': 'card title'}},
            {'key': 'thumbnail_image_original',
             'value': {'image_value': {'url': 'https://pbs.twimg.com/card_img.jpg'}}},
        ]}}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.has_card is True
        assert tweet.thumbnail_title == 'card title'
        assert tweet.thumbnail_url == 'https://pbs.twimg.com/card_img.jpg'

    def test_tweet_no_card(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        tweet = TwitterTweet.model_validate(_tweet_result_payload())
        assert tweet.has_card is False
        assert tweet.thumbnail_title is None
        assert tweet.thumbnail_url is None

    def test_tweet_video_streams(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['legacy']['entities']['media'][0] = {
            'id_str': '1900000000000000001',
            'type': 'video',
            'media_url_https': 'https://pbs.twimg.com/ext_tw_video_thumb/xxx.jpg',
            'original_info': {'width': 1280, 'height': 720},
            'video_info': {
                'aspect_ratio': [16, 9],
                'duration_millis': 30000,
                'variants': [
                    {'content_type': 'application/x-mpegURL', 'url': 'https://video.twimg.com/xxx/playlist.m3u8'},
                    {'content_type': 'video/mp4', 'bitrate': 832000, 'url': 'https://video.twimg.com/xxx/360x360.mp4'},
                    {'content_type': 'video/mp4', 'bitrate': 2176000, 'url': 'https://video.twimg.com/xxx/720x720.mp4'},
                ],
            },
        }
        tweet = TwitterTweet.model_validate(payload)
        media = tweet.media[0]
        assert media.type == 'video'
        assert media.video_info is not None
        assert media.video_info.duration_millis == 30000
        assert [x.bitrate for x in media.streams] == [832000, 2176000]  # 非 video/* 变体被过滤

    def test_highlight_result_and_activate_result(self) -> None:
        from src.utils.twitter_x_api.model import TwitterGuestActivateResult, TwitterHighlightTweetsResult

        assert TwitterGuestActivateResult.model_validate({'guest_token': '123'}).guest_token == '123'
        empty = TwitterHighlightTweetsResult()
        assert empty.tweets == []
        assert empty.next_cursor is None
        assert empty.previous_cursor is None

    def test_optional_url_empty_string_coerced_to_none(self) -> None:
        # 空字符串 URL 回归: OptionalUrl 应将 '' 归一为 None 而非抛 ValidationError
        from src.utils.twitter_x_api.model import TwitterMedia, TwitterUser

        payload = _user_result_payload()
        payload['legacy']['profile_image_url_https'] = ''
        payload['legacy']['profile_banner_url'] = ''
        payload['legacy']['url'] = ''
        user = TwitterUser.model_validate(payload)
        assert user.profile_image_url is None
        assert user.profile_banner_url is None
        assert user.url is None

        media = TwitterMedia.model_validate({
            'id_str': '1',
            'media_url_https': '',
            'url': '',
            'expanded_url': '',
        })
        assert media.media_url is None
        assert media.url is None
        assert media.expanded_url is None

    def test_id_int_coerced_to_str(self) -> None:
        # coerce_numbers_to_str: rest_id/id_str 为 int 时强转为 str
        from src.utils.twitter_x_api.model import TwitterMedia, TwitterUser

        assert TwitterUser.model_validate({'rest_id': 783214}).id == '783214'
        assert TwitterMedia.model_validate({'id_str': 1900000000000000000}).id == '1900000000000000000'

    def test_media_missing_id_raises(self) -> None:
        # id_str 为必填字段(媒体数据缺 id 视为残缺数据)
        from pydantic import ValidationError

        from src.utils.twitter_x_api.model import TwitterMedia

        with pytest.raises(ValidationError):
            TwitterMedia.model_validate({'type': 'photo'})

    def test_media_explicit_size_wins_over_original_info(self) -> None:
        # original_info 提取使用 setdefault: 顶层已存在 width/height 时不覆盖
        from src.utils.twitter_x_api.model import TwitterMedia

        media = TwitterMedia.model_validate({
            'id_str': '1',
            'width': 100,
            'height': 50,
            'original_info': {'width': 800, 'height': 600},
        })
        assert media.width == 100
        assert media.height == 50

    def test_media_streams_empty_without_video_info(self) -> None:
        from src.utils.twitter_x_api.model import TwitterMedia

        media = TwitterMedia.model_validate({'id_str': '1', 'type': 'photo'})
        assert media.video_info is None
        assert media.streams == []

    def test_tweet_view_count_int_coerced(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['views'] = {'count': 12345, 'state': 'EnabledWithCount'}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.view_count == '12345'

    def test_tweet_hashtags_non_dict_filtered(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['legacy']['entities']['hashtags'] = [{'text': 'a'}, 'broken', {'no_text': 1}, None]
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.hashtags == ['a']

    def test_tweet_quote_wrapped_in_tweet_key(self) -> None:
        # 引用推文 result 内再包一层 tweet 键时可正确解包
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['quoted_status_result'] = {'result': {'tweet': _tweet_result_payload(rest_id='1790000000000000001')}}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.quote is not None
        assert tweet.quote.id == '1790000000000000001'

    def test_tweet_quote_missing_core_or_legacy_skipped(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        quoted = _tweet_result_payload(rest_id='1790000000000000002')
        del quoted['core']
        payload['quoted_status_result'] = {'result': quoted}
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.quote is None

    def test_tweet_retweeted_wrapped_in_tweet_key(self) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        payload = _tweet_result_payload()
        payload['legacy']['retweeted_status_result'] = {
            'result': {'tweet': _tweet_result_payload(rest_id='1800000000000000001')}
        }
        tweet = TwitterTweet.model_validate(payload)
        assert tweet.retweeted_tweet is not None
        assert tweet.retweeted_tweet.id == '1800000000000000001'


@pytest.mark.usefixtures('_twitter_api_ready')
class TestParseTweetFromData:
    """helper.py 推文解析守卫测试(零网络)"""

    def test_parse_from_timeline_entry(self) -> None:
        from src.utils.twitter_x_api.helper import parse_tweet_from_data

        tweet = parse_tweet_from_data(_timeline_entry('tweet-1780000000000000000'))
        assert tweet is not None
        assert tweet.id == '1780000000000000000'

    def test_parse_from_tweet_result_response(self) -> None:
        from src.utils.twitter_x_api.helper import parse_tweet_from_data

        tweet = parse_tweet_from_data({'data': {'tweet_result': {'result': _tweet_result_payload()}}})
        assert tweet is not None
        assert tweet.id == '1780000000000000000'

    def test_parse_tombstone_returns_none(self) -> None:
        from src.utils.twitter_x_api.helper import parse_tweet_from_data

        assert parse_tweet_from_data({'tweet_result': {'result': {'__typename': 'TweetTombstone'}}}) is None

    def test_parse_tweet_wrapper_unwrapped(self) -> None:
        # 部分 entry 的 result 内再包一层 tweet 键
        from src.utils.twitter_x_api.helper import parse_tweet_from_data

        tweet = parse_tweet_from_data({'tweet_results': {'result': {'tweet': _tweet_result_payload()}}})
        assert tweet is not None
        assert tweet.id == '1780000000000000000'

    def test_parse_missing_core_or_legacy_returns_none(self) -> None:
        from src.utils.twitter_x_api.helper import parse_tweet_from_data

        payload = _tweet_result_payload()
        del payload['core']
        assert parse_tweet_from_data({'tweet_results': {'result': payload}}) is None

        payload = _tweet_result_payload()
        del payload['legacy']
        assert parse_tweet_from_data({'tweet_results': {'result': payload}}) is None

    def test_parse_no_result_returns_none(self) -> None:
        from src.utils.twitter_x_api.helper import parse_tweet_from_data

        assert parse_tweet_from_data({'data': {'tweet_result': {}}}) is None
        assert parse_tweet_from_data({}) is None

    def test_parse_validation_failure_returns_none(self) -> None:
        # M2: 通过结构守卫但模型校验失败(如缺 rest_id)时返回 None 而非抛 ValidationError
        from src.utils.twitter_x_api.helper import parse_tweet_from_data

        payload = _tweet_result_payload()
        del payload['rest_id']
        assert parse_tweet_from_data({'tweet_results': {'result': payload}}) is None

    def test_parse_wrapped_tombstone_returns_none(self) -> None:
        # 墓碑推文被 tweet 键包裹: 解包后缺 core 同样返回 None
        from src.utils.twitter_x_api.helper import parse_tweet_from_data

        data = {'tweet_results': {'result': {'tweet': {'__typename': 'TweetTombstone', 'text': 'unavailable'}}}}
        assert parse_tweet_from_data(data) is None


def _patch_offline_request(
        monkeypatch: pytest.MonkeyPatch,
        *,
        get_side_effects: list[Any] | None = None,
        post_side_effects: list[Any] | None = None,
        captured: dict[str, Any] | None = None,
        guest_token: str | None = 'gt_offline_test',
) -> None:
    """将 BaseTwitterAPI._request_get/_request_post 替换为罐装实现(零网络)

    - 冻结类级 guest/transaction 状态(BaseTwitterAPI 与 TwitterGuest 两级), 避免真实 activate 与首页请求;
      代码经子类 cls._guest_token = ... 写入会落在子类上, 仅 patch 基类会泄漏, 故两级都冻结
    - side_effects 列表按调用顺序弹出: Exception 实例则抛出, 否则作为 JSON payload 返回 200
    - captured 回写每次调用的 method/url/params/data/headers
    """
    from src.utils.twitter_x_api.api_base import BaseTwitterAPI
    from src.utils.twitter_x_api.guest import TwitterGuest
    from src.utils.twitter_x_api.transaction import ClientTransaction

    for target_cls in (BaseTwitterAPI, TwitterGuest):
        monkeypatch.setattr(target_cls, '_guest_token', guest_token)
        monkeypatch.setattr(target_cls, '_client_transaction', None)
        monkeypatch.setattr(target_cls, '_client_transaction_unavailable', True)

    async def _no_init(self: ClientTransaction, requester: Any) -> None:
        raise RuntimeError('offline test: ClientTransaction.init should not perform network request')

    monkeypatch.setattr(ClientTransaction, 'init', _no_init)

    get_queue = list(get_side_effects or [])
    post_queue = list(post_side_effects or [])

    async def _fake_get(cls: type, url: str, params: Any = None, **kwargs: Any) -> Any:
        if captured is not None:
            captured.update({'method': 'GET', 'url': url, 'params': params, **kwargs})
        if not get_queue:
            raise AssertionError('unexpected _request_get call, no canned side effect left')
        item = get_queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return _fake_response(item)

    async def _fake_post(cls: type, url: str, params: Any = None, *, data: Any = None, **kwargs: Any) -> Any:
        if captured is not None:
            captured.update({'method': 'POST', 'url': url, 'data': data, **kwargs})
        if not post_queue:
            raise AssertionError('unexpected _request_post call, no canned side effect left')
        item = post_queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return _fake_response(item)

    monkeypatch.setattr(BaseTwitterAPI, '_request_get', classmethod(_fake_get))
    monkeypatch.setattr(BaseTwitterAPI, '_request_post', classmethod(_fake_post))


@pytest.mark.usefixtures('_twitter_api_ready')
class TestGuestRequestAssembly:
    """guest.py 各 API 的请求组装(端点/variables/features/headers, 零网络)"""

    async def test_get_user_by_screen_name(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.consts import USER_BY_SCREEN_NAME_URL
        from src.utils.twitter_x_api.guest import TwitterGuest
        from src.utils.twitter_x_api.model import TwitterUser

        captured: dict[str, Any] = {}
        _patch_offline_request(monkeypatch, get_side_effects=[_user_response()], captured=captured)

        user = await TwitterGuest.get_user_by_screen_name('X')

        assert isinstance(user, TwitterUser)
        assert user.screen_name == 'X'
        assert captured['url'] == USER_BY_SCREEN_NAME_URL
        variables = ujson.loads(captured['params']['variables'])
        features = ujson.loads(captured['params']['features'])
        toggles = ujson.loads(captured['params']['fieldToggles'])
        assert variables == {'screen_name': 'X', 'withSafetyModeUserFields': False}
        assert 'hidden_profile_likes_enabled' in features
        assert toggles == {'withAuxiliaryUserLabels': False}
        headers = captured['headers']
        assert headers['authorization'].startswith('Bearer ')
        assert headers['x-guest-token'] == 'gt_offline_test'
        assert headers['x-twitter-active-user'] == 'yes'
        assert 'x-client-transaction-id' not in headers  # transaction 不可用时降级不带

    async def test_get_user_by_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.consts import USER_BY_REST_ID_URL
        from src.utils.twitter_x_api.guest import TwitterGuest

        captured: dict[str, Any] = {}
        _patch_offline_request(monkeypatch, get_side_effects=[_user_response()], captured=captured)

        user = await TwitterGuest.get_user_by_id(783214)

        assert user.id == '783214'  # int 入参经 str() 序列化
        assert captured['url'] == USER_BY_REST_ID_URL
        variables = ujson.loads(captured['params']['variables'])
        assert variables == {'userId': '783214', 'withSafetyModeUserFields': True}
        assert 'fieldToggles' not in captured['params']

    async def test_get_user_tweets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api import consts
        from src.utils.twitter_x_api.consts import USER_TWEETS_URL
        from src.utils.twitter_x_api.guest import TwitterGuest

        entries = [
            _timeline_entry('tweet-1780000000000000000'),
            _timeline_entry('profile-conversation-1', tweet=_tweet_result_payload(rest_id='1781111111111111111')),
            _timeline_entry('promoted-tweet-1', tweet=_tweet_result_payload(rest_id='1782222222222222222')),
            _cursor_entry('cursor-top-1', 'top'),
            _cursor_entry('cursor-bottom-1', 'bottom'),
        ]
        captured: dict[str, Any] = {}
        # UserTweets 真实响应键为 timeline_v2(解析端 find_dict 与键名无关)
        response = _timeline_response(entries, timeline_key='timeline_v2')
        _patch_offline_request(monkeypatch, get_side_effects=[response], captured=captured)

        tweets = await TwitterGuest.get_user_tweets('783214', count=5)

        assert [x.id for x in tweets] == ['1780000000000000000', '1781111111111111111']  # promoted 条目被过滤
        assert captured['url'] == USER_TWEETS_URL
        variables = ujson.loads(captured['params']['variables'])
        assert variables == {
            'userId': '783214', 'count': 5, 'includePromotedContent': True,
            'withQuickPromoteEligibilityTweetFields': True, 'withVoice': True, 'withV2Timeline': True,
        }
        # features 与 consts.FEATURES 全量一致(consts 为纯常量模块, 用例内导入即可)
        assert ujson.loads(captured['params']['features']) == dict(consts.FEATURES)

    async def test_get_user_tweets_empty_instructions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.guest import TwitterGuest

        _patch_offline_request(monkeypatch, get_side_effects=[{'data': None}])
        assert await TwitterGuest.get_user_tweets('783214') == []

        # TimelineAddEntries 缺失(TimelineTerminateTimeline) → 空列表
        response = {'data': {'user': {'result': {'timeline': {'timeline': {
            'instructions': [{'type': 'TimelineTerminateTimeline', 'direction': 'Top'}]
        }}}}}}
        _patch_offline_request(monkeypatch, get_side_effects=[response])
        assert await TwitterGuest.get_user_tweets('783214') == []

    async def test_get_tweet_by_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.consts import TWEET_RESULT_BY_REST_ID_URL
        from src.utils.twitter_x_api.guest import TwitterGuest

        captured: dict[str, Any] = {}
        _patch_offline_request(
            monkeypatch,
            get_side_effects=[{'data': {'tweet_result': {'result': _tweet_result_payload()}}}],
            captured=captured,
        )

        tweet = await TwitterGuest.get_tweet_by_id('1780000000000000000')

        assert tweet.id == '1780000000000000000'
        assert captured['url'] == TWEET_RESULT_BY_REST_ID_URL
        variables = ujson.loads(captured['params']['variables'])
        assert variables == {'tweetId': '1780000000000000000', 'withCommunity': False,
                             'includePromotedContent': False, 'withVoice': False}
        toggles = ujson.loads(captured['params']['fieldToggles'])
        assert toggles == {'withArticleRichContentState': True, 'withArticlePlainText': False, 'withGrokAnalyze': False}

    async def test_get_tweet_by_id_not_found_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        _patch_offline_request(monkeypatch, get_side_effects=[{'data': {'tweet_result': {}}}])

        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_tweet_by_id('1999999999999999999')
        assert exc_info.value.status_code == 404

    async def test_get_user_highlights_tweets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.consts import USER_HIGHLIGHTS_TWEETS_URL
        from src.utils.twitter_x_api.guest import TwitterGuest
        from src.utils.twitter_x_api.model import TwitterHighlightTweetsResult

        entries = [
            _timeline_entry('tweet-1780000000000000000'),
            _cursor_entry('cursor-top-abc', 'prev-cursor'),
            _cursor_entry('cursor-bottom-xyz', 'next-cursor'),
        ]
        captured: dict[str, Any] = {}
        _patch_offline_request(monkeypatch, get_side_effects=[_timeline_response(entries)], captured=captured)

        result = await TwitterGuest.get_user_highlights_tweets('783214', count=20, cursor='prev-cursor')

        assert isinstance(result, TwitterHighlightTweetsResult)
        assert [x.id for x in result.tweets] == ['1780000000000000000']
        assert result.next_cursor == 'next-cursor'
        assert result.previous_cursor == 'prev-cursor'
        variables = ujson.loads(captured['params']['variables'])
        assert variables == {'userId': '783214', 'count': 20, 'includePromotedContent': True,
                             'withVoice': True, 'cursor': 'prev-cursor'}
        assert captured['url'] == USER_HIGHLIGHTS_TWEETS_URL

    async def test_get_user_highlights_tweets_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.guest import TwitterGuest

        _patch_offline_request(monkeypatch, get_side_effects=[{'data': None}])
        result = await TwitterGuest.get_user_highlights_tweets('783214')
        assert result.tweets == []
        assert result.next_cursor is None

    async def test_get_user_tweets_instructions_null(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # M1: instructions 显式为 null 时按空时间线返回而非 TypeError
        from src.utils.twitter_x_api.guest import TwitterGuest

        response = {'data': {'user': {'result': {'timeline_v2': {'timeline': {'instructions': None}}}}}}
        _patch_offline_request(monkeypatch, get_side_effects=[response])
        assert await TwitterGuest.get_user_tweets('783214') == []

    async def test_get_user_tweets_instructions_not_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # M1: instructions 为 dict 等畸形结构时按空时间线返回
        from src.utils.twitter_x_api.guest import TwitterGuest

        response = {'data': {'user': {'result': {'timeline_v2': {'timeline': {'instructions': {'type': 'x'}}}}}}}
        _patch_offline_request(monkeypatch, get_side_effects=[response])
        assert await TwitterGuest.get_user_tweets('783214') == []

    async def test_get_user_tweets_malformed_entries_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # M1: entries 中的非 dict 条目与非 str entryId 被跳过, 不影响其余条目
        from src.utils.twitter_x_api.guest import TwitterGuest

        entries = [
            'broken',
            None,
            {'entryId': None},
            {'entryId': 123},
            _timeline_entry('tweet-1780000000000000000'),
        ]
        response = _timeline_response(entries, timeline_key='timeline_v2')
        _patch_offline_request(monkeypatch, get_side_effects=[response])
        tweets = await TwitterGuest.get_user_tweets('783214')
        assert [x.id for x in tweets] == ['1780000000000000000']

    async def test_get_user_highlights_instructions_null(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # M1: highlights 的 instructions 为 null 时返回空结果
        from src.utils.twitter_x_api.guest import TwitterGuest

        response = {'data': {'user': {'result': {'timeline': {'timeline': {'instructions': None}}}}}}
        _patch_offline_request(monkeypatch, get_side_effects=[response])
        result = await TwitterGuest.get_user_highlights_tweets('783214')
        assert result.tweets == []
        assert result.next_cursor is None

    async def test_get_user_highlights_malformed_cursor_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # M1: 游标条目缺 content 或 content 非 dict 时游标归 None, 畸形条目被跳过
        from src.utils.twitter_x_api.guest import TwitterGuest

        entries = [
            _timeline_entry('tweet-1780000000000000000'),
            {'entryId': 'cursor-top-1'},  # 无 content 键
            {'entryId': 'cursor-bottom-1', 'content': None},  # content 非 dict
            'broken',
        ]
        _patch_offline_request(monkeypatch, get_side_effects=[_timeline_response(entries)])
        result = await TwitterGuest.get_user_highlights_tweets('783214')
        assert [x.id for x in result.tweets] == ['1780000000000000000']
        assert result.previous_cursor is None
        assert result.next_cursor is None


@pytest.mark.usefixtures('_twitter_api_ready')
class TestGuestSession:
    """api_base.py 访客会话管理(activate/缓存/401 重试, 零网络)"""

    async def test_activate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.consts import GUEST_ACTIVATE_URL
        from src.utils.twitter_x_api.guest import TwitterGuest

        captured: dict[str, Any] = {}
        _patch_offline_request(
            monkeypatch, guest_token=None,
            post_side_effects=[{'guest_token': 'gt_new_token'}], captured=captured,
        )

        token = await TwitterGuest.activate()

        assert token == 'gt_new_token'
        # token 已缓存(cls._activate_guest 写在 cls 即 TwitterGuest 上)
        assert TwitterGuest._guest_token == 'gt_new_token'
        assert captured['url'] == GUEST_ACTIVATE_URL
        assert captured['data'] == {}
        headers = captured['headers']
        assert 'x-twitter-active-user' not in headers  # activate 时移除
        assert 'x-guest-token' not in headers  # activate 前尚无 token

    async def test_ensure_guest_token_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        _patch_offline_request(monkeypatch, guest_token='gt_cached')
        assert await BaseTwitterAPI._ensure_guest_token() == 'gt_cached'
        # 无 post side effect 也未调用 activate: 若调用会 AssertionError

    async def test_gql_retry_on_401(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        captured: dict[str, Any] = {}
        _patch_offline_request(
            monkeypatch, guest_token='gt_stale',
            get_side_effects=[
                WebSourceException(401, 'test unauthorized'),
                _user_response(),
            ],
            post_side_effects=[{'guest_token': 'gt_refreshed'}],
            captured=captured,
        )

        user = await TwitterGuest.get_user_by_screen_name('X')

        assert user.screen_name == 'X'  # 重试成功
        # 第一次 GET 401(stale token) → reset → activate(POST) → 第二次 GET(refreshed token)
        assert captured['method'] == 'GET'
        assert captured['headers']['x-guest-token'] == 'gt_refreshed'

    async def test_gql_retry_on_403_only_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        _patch_offline_request(
            monkeypatch, guest_token='gt_stale',
            get_side_effects=[
                WebSourceException(403, 'test forbidden'),
                WebSourceException(403, 'test forbidden again'),
            ],
            post_side_effects=[{'guest_token': 'gt_refreshed'}],
        )

        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_user_by_screen_name('X')
        assert exc_info.value.status_code == 403  # 重试一次后仍失败则抛出

    async def test_gql_no_retry_on_404(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        _patch_offline_request(monkeypatch, get_side_effects=[WebSourceException(404, 'test not found')])

        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_user_by_screen_name('X')
        assert exc_info.value.status_code == 404

    async def test_user_data_missing_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 上游 200 但 data.user 缺失(如用户不存在): _extract_user_result 抛 WebSourceException(400)
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        _patch_offline_request(monkeypatch, get_side_effects=[{'data': {'user': None}}])

        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_user_by_screen_name('no_such_user_xyz')
        assert exc_info.value.status_code == 400

    async def test_download_resource_delegates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # download_resource 走 BaseCommonAPI._download_resource, 此处仅验证透传不被 guest 状态干扰
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        captured: dict[str, Any] = {}

        async def _fake_download(cls: type, **kwargs: Any) -> str:
            captured.update(kwargs)
            return 'fake'

        monkeypatch.setattr(BaseTwitterAPI, '_download_resource', classmethod(_fake_download))
        result = await BaseTwitterAPI.download_resource('https://pbs.twimg.com/media/xxx.jpg')
        assert result == 'fake'
        assert captured['url'] == 'https://pbs.twimg.com/media/xxx.jpg'

    async def test_gql_retry_activate_failure_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 401 重试链中 activate(POST) 自身失败时直接抛出, 不再继续重试
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        _patch_offline_request(
            monkeypatch, guest_token='gt_stale',
            get_side_effects=[WebSourceException(401, 'test unauthorized')],
            post_side_effects=[WebSourceException(403, 'test activate blocked')],
        )

        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_user_by_screen_name('X')
        assert exc_info.value.status_code == 403
        assert exc_info.value.message == 'test activate blocked'

    async def test_activate_malformed_response_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # activate 响应缺 guest_token 字段: 抛出 ValidationError(现状行为记录)
        from pydantic import ValidationError

        from src.utils.twitter_x_api.guest import TwitterGuest

        _patch_offline_request(monkeypatch, guest_token=None, post_side_effects=[{'unexpected': 'shape'}])

        with pytest.raises(ValidationError):
            await TwitterGuest.activate()

    async def test_user_unavailable_raises_web_source_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # M2: 不可用用户(如封禁账号, result 缺 rest_id)统一抛出 WebSourceException(400) 而非 ValidationError
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        response = {'data': {'user': {'result': {'__typename': 'UserUnavailable', 'reason': 'suspended'}}}}
        _patch_offline_request(monkeypatch, get_side_effects=[response])

        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_user_by_screen_name('suspended_user')
        assert exc_info.value.status_code == 400
        assert 'parse error' in exc_info.value.message

    async def test_user_data_missing_message_truncated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # M3: 异常消息中的响应体被截断, 不整体进入异常消息与日志
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        _patch_offline_request(monkeypatch, get_side_effects=[{'data': {'user': None}, 'padding': 'x' * 5000}])

        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_user_by_screen_name('X')
        assert 'user data not found' in exc_info.value.message
        assert len(exc_info.value.message) < 1000

    def test_reset_guest_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.guest import TwitterGuest

        monkeypatch.setattr(TwitterGuest, '_guest_token', 'gt')
        monkeypatch.setattr(TwitterGuest, '_client_transaction', object())
        monkeypatch.setattr(TwitterGuest, '_client_transaction_unavailable', True)

        TwitterGuest._reset_guest_state()

        assert TwitterGuest._guest_token is None
        assert TwitterGuest._client_transaction is None
        assert TwitterGuest._client_transaction_unavailable is False


@pytest.mark.usefixtures('_twitter_api_ready')
class TestApiBaseHeaders:
    """api_base.py 请求头构造(零网络)"""

    def test_api_headers_default(self) -> None:
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        headers = BaseTwitterAPI._get_api_headers()
        assert headers['authorization'].startswith('Bearer ')
        assert headers['content-type'] == 'application/json'
        assert headers['origin'] == 'https://x.com'
        assert headers['referer'] == 'https://x.com/'
        assert headers['sec-fetch-dest'] == 'empty'
        assert headers['sec-fetch-mode'] == 'cors'
        assert headers['sec-fetch-site'] == 'same-site'
        assert headers['x-twitter-active-user'] == 'yes'
        assert 'x-guest-token' not in headers

    def test_api_headers_with_guest_token(self) -> None:
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        headers = BaseTwitterAPI._get_api_headers(guest_token='gt_x')
        assert headers['x-guest-token'] == 'gt_x'

    def test_api_headers_without_active_user(self) -> None:
        # activate 场景不携带 x-twitter-active-user
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        headers = BaseTwitterAPI._get_api_headers(with_active_user=False)
        assert 'x-twitter-active-user' not in headers

    def test_transaction_headers_without_transaction(self) -> None:
        # transaction 不可用时降级为空 headers
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        assert BaseTwitterAPI._get_transaction_headers('GET', 'https://x.com/i/api/graphql/qid/Endpoint', None) == {}

    def test_transaction_headers_with_transaction(self) -> None:
        # transaction 可用时按 method+path(不含 query) 生成 ctid
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        class _FakeTransaction:
            @staticmethod
            def generate_transaction_id(method: str, path: str) -> str:
                assert method == 'GET'
                assert path == '/i/api/graphql/qid/Endpoint'  # query 已被剥离
                return 'fake-tid'

        headers = BaseTwitterAPI._get_transaction_headers(
            'GET', 'https://x.com/i/api/graphql/qid/Endpoint?variables=%7B%7D', _FakeTransaction()
        )
        assert headers == {'x-client-transaction-id': 'fake-tid'}


# ================================================================== #
# ClientTransaction 离线测试(合成首页与 ondemand.s, 零网络)
# ================================================================== #

_TX_KEY_BYTES = list(range(32))
"""合成 twitter-site-verification key 的字节序列: key_bytes[5]%4=1 选 1 号帧, key_bytes[3]%16=3 选 3 号动画行"""

_TX_KEY = base64.b64encode(bytes(_TX_KEY_BYTES)).decode()

_TX_FRAME_ROWS = [
    [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120],
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    [200, 150, 100, 50, 250, 0, 120, 10, 20, 30, 40, 50],
    [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60],  # row_index=3 命中此行
]


def _make_transaction_html(*, ondemand_ref: str = "'ondemand.s': 'abc123',") -> str:
    """合成 X 首页: 验证 meta + 4 帧 loading-x-anim SVG + 内联 ondemand.s 哈希引用

    d 属性结构对齐实现解析逻辑(`get('d')[9:].split('C')`): 前 9 字符为 'M' 前缀,
    其后为 4 行数值以 'C' 分隔; key_bytes[5]%4=1 选 1 号帧, key_bytes[3]%16=3 选 arr[3](即 _TX_FRAME_ROWS[3])
    """
    svgs = []
    for i in range(4):
        d_attr = 'M12345678' + 'C'.join(' '.join(str(v) for v in row) for row in _TX_FRAME_ROWS)
        svgs.append(f'<svg id="loading-x-anim-{i}"><g><path/><path d="{d_attr}"/></g></svg>')
    return (
            '<html><head>'
            f'<meta name="twitter-site-verification" content="{_TX_KEY}"/>'
            f'<script>var a = {{{ondemand_ref}}};</script>'
            '</head><body>' + ''.join(svgs) + '</body></html>'
    )


def _make_ondemand_js() -> str:
    """合成 ondemand.s 脚本: INDICES_REGEX 提取出 [3, 7, 12, 14]"""
    return 'function f(e,t){return (e[3],16)&&(e[7],16),(e[12],16),(e[14],16)}'


def _fake_response_text(content: str) -> 'Response':
    from nonebot.drivers import Response

    return Response(200, content=content.encode('utf-8'))


class _FakeTxRequester:
    """ClientTransaction.init 用假请求器: 首页与 ondemand.s 均返回合成内容"""

    def __init__(self, home_html: str, ondemand_js: str) -> None:
        self._home_html = home_html
        self._ondemand_js = ondemand_js
        self.requested_urls: list[str] = []

    async def get(self, url: str, **kwargs: Any) -> 'Response':
        self.requested_urls.append(url)
        if url == 'https://x.com':
            return _fake_response_text(self._home_html)
        if 'ondemand.s.' in url:
            return _fake_response_text(self._ondemand_js)
        raise AssertionError(f'unexpected url in fake requester: {url}')

    async def post(self, url: str, **kwargs: Any) -> 'Response':
        raise AssertionError('fake requester should not receive POST for transaction init')


class _MappingTxRequester:
    """ClientTransaction 迁移分支测试用假请求器: 按 URL 映射返回页面并记录请求"""

    def __init__(self, pages: dict[str, str]) -> None:
        self._pages = pages
        self.get_urls: list[str] = []
        self.posts: list[tuple[str, Any]] = []

    async def get(self, url: str, **kwargs: Any) -> 'Response':
        self.get_urls.append(url)
        if url not in self._pages:
            raise AssertionError(f'unexpected GET url in fake requester: {url}')
        return _fake_response_text(self._pages[url])

    async def post(self, url: str, **kwargs: Any) -> 'Response':
        self.posts.append((url, kwargs.get('data')))
        if url not in self._pages:
            raise AssertionError(f'unexpected POST url in fake requester: {url}')
        return _fake_response_text(self._pages[url])


@pytest.mark.usefixtures('_twitter_api_ready')
class TestTransactionPureFunctions:
    """transaction.py 数值函数测试(与浏览器 Number.toString(16) 行为对齐)"""

    def test_float_to_hex(self) -> None:
        # 与 twikit 参考实现行为一致(非浏览器 toString(16)): 无前导零、大写 A-F;
        # '.8' 形态由 _animate 调用方补偿(startswith('.') 时补 0 并 lower)
        from src.utils.twitter_x_api.transaction import _float_to_hex

        assert _float_to_hex(0.0) == ''
        assert _float_to_hex(10.0) == 'A'
        assert _float_to_hex(255.0) == 'FF'
        assert _float_to_hex(0.5) == '.8'
        assert _float_to_hex(1.5) == '1.8'  # 整数位 1, 小数 0.5*16=8

    def test_is_odd(self) -> None:
        from src.utils.twitter_x_api.transaction import _is_odd

        assert _is_odd(1) == -1.0
        assert _is_odd(2) == 0.0

    def test_interpolate_mismatch_raises(self) -> None:
        from src.utils.twitter_x_api.transaction import _interpolate

        with pytest.raises(ValueError, match='Mismatched interpolation'):
            _interpolate([1.0], [1.0, 2.0], 0.5)

    def test_convert_rotation_to_matrix_zero(self) -> None:
        from src.utils.twitter_x_api.transaction import _convert_rotation_to_matrix

        assert _convert_rotation_to_matrix(0.0) == [1.0, 0.0, 0.0, 1.0]

    def test_cubic_get_value_bounds(self) -> None:
        from src.utils.twitter_x_api.transaction import _Cubic

        cubic = _Cubic([0.25, 0.1, 0.25, 1.0])
        assert cubic.get_value(0.0) == 0.0
        assert cubic.get_value(1.0) == 1.0
        assert 0.0 <= cubic.get_value(0.5) <= 1.0


@pytest.mark.usefixtures('_twitter_api_ready')
class TestOnDemandHashExtraction:
    """_extract_on_demand_file_hash 新旧打包格式兼容"""

    def test_legacy_format(self) -> None:
        from src.utils.twitter_x_api.transaction import ClientTransaction

        assert ClientTransaction._extract_on_demand_file_hash(_make_transaction_html()) == 'abc123'

    def test_webpack_chunk_format(self) -> None:
        from src.utils.twitter_x_api.transaction import ClientTransaction

        html = _make_transaction_html(ondemand_ref=',123:"ondemand.s"') + '<script>var h={,123:"deadbeef"};</script>'
        assert ClientTransaction._extract_on_demand_file_hash(html) == 'deadbeef'

    def test_no_match_returns_none(self) -> None:
        from src.utils.twitter_x_api.transaction import ClientTransaction

        assert ClientTransaction._extract_on_demand_file_hash('<html><body>nothing</body></html>') is None

    def test_chunk_format_without_hash_returns_none(self) -> None:
        # chunk 索引存在但哈希映射表缺失: 返回 None
        from src.utils.twitter_x_api.transaction import ClientTransaction

        html = _make_transaction_html(ondemand_ref=',123:"ondemand.s"')
        assert ClientTransaction._extract_on_demand_file_hash(html) is None

    def test_chunk_hash_of_other_id_not_matched(self) -> None:
        # 哈希映射表中仅有其他 chunk id 的哈希时不误匹配
        from src.utils.twitter_x_api.transaction import ClientTransaction

        html = _make_transaction_html(ondemand_ref=',123:"ondemand.s"') + '<script>var h={,124:"deadbeef"};</script>'
        assert ClientTransaction._extract_on_demand_file_hash(html) is None


@pytest.mark.usefixtures('_twitter_api_ready')
class TestClientTransaction:
    """ClientTransaction 初始化与 transaction id 生成(合成首页, 零网络)"""

    async def test_init_and_generate(self) -> None:
        from src.utils.twitter_x_api.transaction import ClientTransaction

        ct = ClientTransaction()
        requester = _FakeTxRequester(_make_transaction_html(), _make_ondemand_js())
        await ct.init(requester=requester)

        assert ct.is_initialized is True
        assert 'https://x.com' in requester.requested_urls
        assert any('ondemand.s.abc123a.js' in url for url in requester.requested_urls)

        tid = ct.generate_transaction_id('GET', '/i/api/graphql/x/UserByScreenName', time_now=1000)
        assert isinstance(tid, str)
        assert tid
        assert '=' not in tid  # base64 padding 已剥离
        decoded = base64.b64decode(tid + '==')
        assert len(decoded) == 54  # 1(random) + 32(key) + 4(time) + 16(hash) + 1(const)

        # 首字节为随机数, 其余字节为 XOR(random) 编码: 解码后 key/time 段确定性可断言
        random_num = decoded[0]
        payload = bytes(b ^ random_num for b in decoded[1:])
        assert list(payload[:32]) == _TX_KEY_BYTES  # key 段
        assert payload[32:36] == (1000).to_bytes(4, 'little')  # time_now=1000 小端 4 字节
        assert payload[-1] == ClientTransaction._ADDITIONAL_RANDOM_NUMBER  # 常量尾字节

        # 首字节随 random_num 波动, 不同调用产生不同 id(随机数碰撞除外)
        tids = {ct.generate_transaction_id('GET', '/x', time_now=1000) for _ in range(8)}
        assert len(tids) > 1, 'transaction id 首字节应携带随机数, 多次调用不应全同'

    async def test_generate_with_explicit_zero_time(self) -> None:
        # P1 修复验证: 显式 time_now=0 不应被覆盖为当前时间
        from src.utils.twitter_x_api.transaction import ClientTransaction

        ct = ClientTransaction()
        await ct.init(requester=_FakeTxRequester(_make_transaction_html(), _make_ondemand_js()))

        zero_tid = ct.generate_transaction_id('GET', '/x', time_now=0)
        decoded = base64.b64decode(zero_tid + '==')
        random_num = decoded[0]
        payload = bytes(b ^ random_num for b in decoded[1:])
        assert payload[32:36] == b'\x00\x00\x00\x00'  # key(32) 之后 4 字节时间位为零
        # 不显式传 time_now(即真实当前时间)时时间位非全零, 与 0 时刻区分
        now_decoded = base64.b64decode(ct.generate_transaction_id('GET', '/x') + '==')
        now_payload = bytes(b ^ now_decoded[0] for b in now_decoded[1:])
        assert now_payload[32:36] != b'\x00\x00\x00\x00'

    async def test_init_failure_on_bad_home_page(self) -> None:
        from src.utils.twitter_x_api.transaction import ClientTransaction

        ct = ClientTransaction()
        with pytest.raises(RuntimeError):
            await ct.init(requester=_FakeTxRequester('', ''))  # 空 HTML 解析失败

    async def test_init_failure_on_missing_key_meta(self) -> None:
        # 首页缺 twitter-site-verification meta → _get_key 抛 "Couldn't get key"
        from src.utils.twitter_x_api.transaction import ClientTransaction

        html = _make_transaction_html().replace(
            f'<meta name="twitter-site-verification" content="{_TX_KEY}"/>', ''
        )
        ct = ClientTransaction()
        with pytest.raises(RuntimeError):
            await ct.init(requester=_FakeTxRequester(html, _make_ondemand_js()))

    async def test_init_failure_on_missing_indices(self) -> None:
        from src.utils.twitter_x_api.transaction import ClientTransaction

        ct = ClientTransaction()
        with pytest.raises(RuntimeError, match='KEY_BYTE'):
            await ct.init(requester=_FakeTxRequester(_make_transaction_html(), 'no indices here'))

    def test_generate_before_init_raises(self) -> None:
        from src.utils.twitter_x_api.transaction import ClientTransaction

        with pytest.raises(RuntimeError, match='not initialized'):
            ClientTransaction().generate_transaction_id('GET', '/x')

    async def test_init_failure_on_broken_frames(self) -> None:
        # 首页帧结构残缺(帧数不足)时 init 抛错, 由上层 _ensure_client_transaction 降级为不携带 ctid
        from src.utils.twitter_x_api.transaction import ClientTransaction

        html = (
            '<html><head>'
            f'<meta name="twitter-site-verification" content="{_TX_KEY}"/>'
            f"<script>var a = {{'ondemand.s': 'abc123'}};</script>"
            '</head><body>'
            '<svg id="loading-x-anim-0"><g><path/><path d="M123456781 2 3 4 5 6 7 8 9 10 11 12"/></g></svg>'
            '</body></html>'
        )
        ct = ClientTransaction()
        with pytest.raises(IndexError):
            await ct.init(requester=_FakeTxRequester(html, _make_ondemand_js()))


@pytest.mark.usefixtures('_twitter_api_ready')
class TestEnsureClientTransaction:
    """api_base.py _ensure_client_transaction 三态(成功缓存/失败置位/重置重试, 零网络)"""

    @staticmethod
    def _patch_init_success(monkeypatch: pytest.MonkeyPatch, counter: list[int]) -> None:
        from src.utils.twitter_x_api.transaction import ClientTransaction

        async def _fake_init(self: ClientTransaction, requester: Any) -> None:
            counter.append(1)
            self.key = _TX_KEY
            self.key_bytes = _TX_KEY_BYTES
            self.animation_key = 'anim_key'
            self.default_row_index = 0
            self.default_key_bytes_indices = [1, 2]

        monkeypatch.setattr(ClientTransaction, 'init', _fake_init)

    async def test_success_and_cached(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        counter: list[int] = []
        self._patch_init_success(monkeypatch, counter)
        monkeypatch.setattr(BaseTwitterAPI, '_client_transaction', None)
        monkeypatch.setattr(BaseTwitterAPI, '_client_transaction_unavailable', False)

        transaction = await BaseTwitterAPI._ensure_client_transaction()

        assert transaction is not None
        assert transaction.is_initialized is True
        assert len(counter) == 1

        # 二次调用复用缓存, 不重复初始化
        assert await BaseTwitterAPI._ensure_client_transaction() is transaction
        assert len(counter) == 1

    async def test_failure_marks_unavailable_and_no_repeat(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI
        from src.utils.twitter_x_api.transaction import ClientTransaction

        counter: list[int] = []

        async def _failing_init(self: ClientTransaction, requester: Any) -> None:
            counter.append(1)
            raise RuntimeError('test init failed')

        monkeypatch.setattr(ClientTransaction, 'init', _failing_init)
        monkeypatch.setattr(BaseTwitterAPI, '_client_transaction', None)
        monkeypatch.setattr(BaseTwitterAPI, '_client_transaction_unavailable', False)

        assert await BaseTwitterAPI._ensure_client_transaction() is None
        assert len(counter) == 1
        assert BaseTwitterAPI._client_transaction_unavailable is True

        # 置位后不再重复尝试
        assert await BaseTwitterAPI._ensure_client_transaction() is None
        assert len(counter) == 1

        # 重置访客状态后允许再次尝试
        BaseTwitterAPI._reset_guest_state()
        assert BaseTwitterAPI._client_transaction_unavailable is False
        assert await BaseTwitterAPI._ensure_client_transaction() is None
        assert len(counter) == 2

    async def test_gql_request_carries_transaction_id_when_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # transaction 初始化成功时, GQL 请求携带 x-client-transaction-id
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI
        from src.utils.twitter_x_api.guest import TwitterGuest

        captured: dict[str, Any] = {}
        _patch_offline_request(monkeypatch, get_side_effects=[_user_response()], captured=captured)
        counter: list[int] = []
        self._patch_init_success(monkeypatch, counter)
        # _patch_offline_request 将 transaction 置为不可用, 此处恢复为可初始化
        for target_cls in (BaseTwitterAPI, TwitterGuest):
            monkeypatch.setattr(target_cls, '_client_transaction_unavailable', False)

        user = await TwitterGuest.get_user_by_screen_name('X')

        assert user.id == '783214'
        assert len(counter) == 1
        assert captured['headers']['x-client-transaction-id']


@pytest.mark.usefixtures('_twitter_api_ready')
class TestClientTransactionMigration:
    """ClientTransaction._handle_x_migration 迁移跳转分支(合成页面, 零网络)"""

    async def test_meta_refresh_redirect(self) -> None:
        # 首页 meta refresh 指向迁移链接: 跟随跳转后在新页面上完成初始化
        from src.utils.twitter_x_api.transaction import ClientTransaction

        migration_url = 'https://x.com/x/migrate?tok=abc123_X-Y%2F'
        redirect_html = (
            '<html><head>'
            f'<meta http-equiv="refresh" content="0;url={migration_url}"/>'
            '</head><body></body></html>'
        )
        requester = _MappingTxRequester({
            'https://x.com': redirect_html,
            migration_url: _make_transaction_html(),
            'https://abs.twimg.com/responsive-web/client-web/ondemand.s.abc123a.js': _make_ondemand_js(),
        })

        ct = ClientTransaction()
        await ct.init(requester=requester)

        assert ct.is_initialized is True
        assert requester.get_urls[0] == 'https://x.com'
        assert migration_url in requester.get_urls

    async def test_migration_form_post(self) -> None:
        # 首页含迁移表单: 按表单字段 POST 迁移地址后完成初始化
        from src.utils.twitter_x_api.transaction import ClientTransaction

        form_html = (
            '<html><head></head><body>'
            '<form name="f" action="https://x.com/x/migrate" method="POST">'
            '<input name="tok" value="abc123"/>'
            '<input name="unstable" value="true"/>'
            '</form>'
            '</body></html>'
        )
        requester = _MappingTxRequester({
            'https://x.com': form_html,
            'https://x.com/x/migrate/?mx=2': _make_transaction_html(),
            'https://abs.twimg.com/responsive-web/client-web/ondemand.s.abc123a.js': _make_ondemand_js(),
        })

        ct = ClientTransaction()
        await ct.init(requester=requester)

        assert ct.is_initialized is True
        assert requester.posts == [('https://x.com/x/migrate/?mx=2', {'tok': 'abc123', 'unstable': 'true'})]


@pytest.mark.usefixtures('_twitter_api_ready')
class TestConfig:
    """config.py 资源路径配置(零网络)"""

    def test_default_download_folder(self) -> None:
        from src.resource import TemporaryResource
        from src.utils.twitter_x_api.config import twitter_api_config

        folder = twitter_api_config.default_download_folder
        assert isinstance(folder, TemporaryResource)
        assert folder.path.parts[-2:] == ('twitter', 'download')


# ================================================================== #
# 真实请求测试(默认全部跳过, 仅用户主动发起: 设置环境变量 OMEGA_TWITTER_X_LIVE_TEST=1 后运行本文件)
# 依赖 .env.test 的代理配置(OMEGA_REQUESTS_ENABLE_PROXY=true, 127.0.0.1:1081)访问 x.com
# ================================================================== #


@requires_live
class TestTwitterGuestLive:
    """TwitterGuest 真实请求验证(访客 API)

    所有真实请求仅经由本类用例发起; 用例自足链式取样, 不依赖执行顺序。
    X 访客 API 限速较严, 每用例前 pacing 2s。
    """

    @pytest.fixture(autouse=True)
    async def _pace(self) -> None:
        await asyncio.sleep(2)

    async def test_activate(self) -> None:
        from src.utils.twitter_x_api.guest import TwitterGuest

        token = await TwitterGuest.activate()

        assert isinstance(token, str)
        assert token
        # 二次调用复用缓存 token(不重复 activate)
        assert await TwitterGuest._ensure_guest_token() == token

    async def test_get_user_by_screen_name(self) -> None:
        from src.utils.twitter_x_api.guest import TwitterGuest
        from src.utils.twitter_x_api.model import TwitterUser

        user = await TwitterGuest.get_user_by_screen_name('X')

        assert isinstance(user, TwitterUser)
        assert user.screen_name == 'X'
        assert user.id.isdigit()
        assert user.is_blue_verified is True  # 官方账号为蓝标
        assert user.created_at_datetime is not None
        assert user.followers_count >= 0
        assert user.profile_image_url is not None

    async def test_get_user_by_id(self) -> None:
        """UserByRestId 实测行为记录(2026-09)

        当前网络环境下该端点被 Cloudflare WAF 拦截: 稳定 403 且响应体为 Cloudflare HTML 拦截页,
        与请求参数无关(已对照 withSafetyModeUserFields/fieldToggles/去 active-user 头共 4 种变体),
        twikit 参考实现的相同参数同样被拦; UserByScreenName/UserTweets/TweetResultByRestId/
        UserHighlightsTweets 均不受影响。客户端经 403 自动重试(重置访客会话并重新激活)后仍 403,
        最终抛出 WebSourceException — 重试路径在真实环境的行为一并得到验证。
        上游恢复后应将本用例改回正向查询断言。
        """
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        user = await TwitterGuest.get_user_by_screen_name('X')
        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_user_by_id(user.id)
        assert exc_info.value.status_code == 403

    async def test_client_transaction_availability_probe(self) -> None:
        """首页 ClientTransaction 初始化探测(2026-09 实测行为记录)

        当前访客首页为 X 新版精简 app shell(约 35KB, data-app-env="prod" 的 x-web 模块结构),
        不含 twitter-site-verification meta / loading-x-anim SVG / ondemand.s 脚本引用,
        ClientTransaction 无法初始化 — twikit 的 x_client_transaction 在此首页上同样失效。
        客户端按设计降级为不携带 X-Client-Transaction-Id 请求, 其余 live 用例通过证明
        该降级下访客 API 可用。上游首页结构恢复后, 本用例自动转为验证初始化成功路径。
        """
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        BaseTwitterAPI._reset_guest_state()
        transaction = await BaseTwitterAPI._ensure_client_transaction()
        # 初始化成功或降级为 None, 均为合法结果; 不应抛异常
        assert transaction is None or transaction.is_initialized

    async def test_get_user_tweets_and_tweet_by_id(self) -> None:
        from src.utils.twitter_x_api.guest import TwitterGuest
        from src.utils.twitter_x_api.model import TwitterTweet

        user = await TwitterGuest.get_user_by_screen_name('X')
        tweets = await TwitterGuest.get_user_tweets(user.id, count=10)

        assert tweets, '官方账号 UserTweets 返回空列表'
        assert all(isinstance(x, TwitterTweet) for x in tweets)
        for tweet in tweets:
            assert tweet.id.isdigit()
            assert tweet.user is not None
            assert tweet.user.screen_name
            assert tweet.created_at_datetime is not None
            assert tweet.favorite_count >= 0
            assert tweet.retweet_count >= 0

        detail = await TwitterGuest.get_tweet_by_id(tweets[0].id)
        assert detail.id == tweets[0].id
        assert detail.text == tweets[0].text  # 同一推文两次查询文本一致

    async def test_get_user_tweets_media_model(self) -> None:
        from src.utils.twitter_x_api.guest import TwitterGuest

        user = await TwitterGuest.get_user_by_screen_name('X')
        tweets = await TwitterGuest.get_user_tweets(user.id, count=20)
        with_media = next((t for t in tweets if t.media), None)
        if with_media is None:
            pytest.skip('近期推文无媒体样本, 无法校验 TwitterMedia')

        media = with_media.media[0]
        assert media.id.isdigit()
        assert media.type in ('photo', 'video', 'animated_gif')
        assert media.media_url is not None
        assert media.width > 0  # original_info 提取
        assert media.height > 0
        if media.type in ('video', 'animated_gif'):
            assert media.video_info is not None
            assert all(x.content_type.startswith('video') for x in media.streams)

    async def test_get_user_highlights_tweets(self) -> None:
        from src.utils.twitter_x_api.guest import TwitterGuest
        from src.utils.twitter_x_api.model import TwitterHighlightTweetsResult

        user = await TwitterGuest.get_user_by_screen_name('X')
        result = await TwitterGuest.get_user_highlights_tweets(user.id)

        assert isinstance(result, TwitterHighlightTweetsResult)
        if not result.tweets:
            pytest.skip('官方账号无高光推文样本, 仅验证空结果形状')
        for tweet in result.tweets:
            assert tweet.id.isdigit()
            assert tweet.created_at_datetime is not None
        if result.next_cursor:
            next_page = await TwitterGuest.get_user_highlights_tweets(user.id, cursor=result.next_cursor)
            assert isinstance(next_page.tweets, list)

    async def test_get_user_by_screen_name_not_found(self) -> None:
        # 实测行为记录(2026-09): X 对不存在用户返回 200 + data.user=null, 客户端转为 WebSourceException(400)
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_user_by_screen_name('omega_miya_no_such_user_9x7z')
        assert exc_info.value.status_code == 400

    async def test_get_tweet_by_id_not_found(self) -> None:
        # 实测行为记录(2026-09): 不存在推文 → WebSourceException(404)
        from src.exception import WebSourceException
        from src.utils.twitter_x_api.guest import TwitterGuest

        with pytest.raises(WebSourceException) as exc_info:
            await TwitterGuest.get_tweet_by_id('1999999999999999999')
        assert exc_info.value.status_code == 404

    async def test_download_resource(self) -> None:
        from src.utils.twitter_x_api.guest import TwitterGuest

        user = await TwitterGuest.get_user_by_screen_name('X')
        if user.profile_image_url is None:
            pytest.skip('样本无头像 URL')
        resource = await TwitterGuest.download_resource(str(user.profile_image_url))
        assert resource.path.exists()
        assert resource.path.stat().st_size > 0
        resource.path.unlink(missing_ok=True)
