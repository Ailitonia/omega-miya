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
from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING, Any

import pytest
import ujson
from pydantic import ValidationError

from tests.test_003_web.helpers import require_env_flag

if TYPE_CHECKING:
    from nonebot.drivers import Response

    from src.exception import WebSourceException
    from src.utils.twitter_x_api.api_base import BaseTwitterAPI
    from src.utils.twitter_x_api.guest import TwitterGuest
    from src.utils.twitter_x_api.model import TwitterUser
    from src.utils.twitter_x_api.transaction import ClientTransaction

requires_live = require_env_flag('OMEGA_TWITTER_X_LIVE_TEST')
"""真实请求测试门禁: 日常运行(含全量套件)一律跳过, 由用户手动设置 OMEGA_TWITTER_X_LIVE_TEST=1 后发起"""

pytestmark = pytest.mark.usefixtures('_twitter_api_ready')
"""模块级 nonebug 初始化屏障, 统一作用于全部用例(含 TestTwitterGuestLive; 屏障本就会话级激活, 对 live 类为 no-op)"""


@pytest.fixture(scope='session')
def _twitter_api_ready(nonebug_init: None) -> None:
    """src.utils.twitter_x_api 导入期依赖 NoneBot 初始化(get_plugin_config), 离线用例的统一屏障"""


def _fake_response(content: Any, status_code: int = 200) -> 'Response':
    """构造罐装 nonebot Response: str/bytes 原样作为响应体, 其余按 JSON 序列化"""
    from nonebot.drivers import Response

    if isinstance(content, str):
        body = content.encode('utf-8')
    elif isinstance(content, bytes):
        body = content
    else:
        body = ujson.dumps(content).encode('utf-8')
    return Response(status_code, content=body)


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
    解析端 find_dict 与键路径无关, 此处参数用于让罐装响应贴近线上真实形状
    """
    return {'data': {'user': {'result': {timeline_key: {'timeline': {
        'instructions': [{'type': 'TimelineAddEntries', 'entries': entries, 'direction': 'Top'}
                         ]}}}}}}


def _set_deep(payload: dict[str, Any], dotted_key: str, value: Any) -> None:
    """按点分键路径写入嵌套 dict(参数化用例构造罐装 payload 用)"""
    node = payload
    *parents, leaf = dotted_key.split('.')
    for key in parents:
        node = node[key]
    node[leaf] = value


class TestMiscHelpers:
    """misc.py 纯函数测试(零网络)"""

    @pytest.fixture
    def misc(self) -> ModuleType:
        from src.utils.twitter_x_api import misc
        return misc

    def test_find_dict_nested(self, misc: ModuleType) -> None:
        obj = {'a': {'b': [{'target': 1}, {'c': 2}]}, 'target': 0}
        assert misc.find_dict(obj, 'target') == [0, 1]
        assert misc.find_dict(obj, 'target', find_one=True) == [0]
        assert misc.find_dict(obj, 'missing') == []
        assert misc.find_dict([{'x': {'y': 1}}], 'y') == [1]

    def test_find_entry_by_type(self, misc: ModuleType) -> None:
        entries = [{'type': 'TimelineTerminateTimeline'}, {'type': 'TimelineAddEntries', 'entries': [1]}]
        assert misc.find_entry_by_type(entries, 'TimelineAddEntries') == {'type': 'TimelineAddEntries', 'entries': [1]}
        assert misc.find_entry_by_type(entries, 'None') is None

    def test_flatten_params(self, misc: ModuleType) -> None:
        result = misc.flatten_params({'variables': {'a': 1, 'b': True}, 'features': {'f': False}, 'plain': 'x', 'n': 5})
        assert ujson.loads(result['variables']) == {'a': 1, 'b': True}
        assert ujson.loads(result['features']) == {'f': False}
        assert result['plain'] == 'x'
        assert result['n'] == 5

    def test_find_dict_find_one_with_none_value(self, misc: ModuleType) -> None:
        # 目标键存在但值为 None 时仍视为找到(返回 [None]), 调用方需自行判空
        assert misc.find_dict({'result': None}, 'result', find_one=True) == [None]
        assert misc.find_dict({'a': {'result': None}}, 'result', find_one=True) == [None]
        assert misc.find_dict({'a': 1}, 'result', find_one=True) == []

    def test_find_dict_non_container_input(self, misc: ModuleType) -> None:
        assert misc.find_dict(None, 'x') == []
        assert misc.find_dict('str', 'x') == []
        assert misc.find_dict(42, 'x') == []

    def test_find_entry_by_type_malformed(self, misc: ModuleType) -> None:
        # 非 list 入参与非 dict 条目一律返回 None 而不抛异常
        assert misc.find_entry_by_type(None, 'TimelineAddEntries') is None
        assert misc.find_entry_by_type('broken', 'TimelineAddEntries') is None
        assert misc.find_entry_by_type({'type': 'TimelineAddEntries'}, 'TimelineAddEntries') is None
        assert misc.find_entry_by_type(
            ['broken', None, {'type': 'TimelineAddEntries'}], 'TimelineAddEntries'
        ) == {'type': 'TimelineAddEntries'}

    def test_flatten_params_scalar_passthrough(self, misc: ModuleType) -> None:
        # 非 dict/list 值原样透传, list 值序列化为 JSON 字符串
        result = misc.flatten_params({'flag': True, 'count': 0, 'list_val': [1, 2], 'none_val': None})
        assert result['flag'] is True
        assert result['count'] == 0
        assert result['none_val'] is None
        assert ujson.loads(result['list_val']) == [1, 2]


class TestConsts:
    """consts.py 与 twikit 参考实现的静态一致性(防意外漂移)"""

    @pytest.fixture
    def consts(self) -> ModuleType:
        from src.utils.twitter_x_api import consts
        return consts

    def test_token_and_domain(self, consts: ModuleType) -> None:
        assert consts.DOMAIN == 'x.com'
        assert consts.TOKEN.startswith('AAAAAAAAAAAAAAAAAAAAANRILg')

    def test_endpoint_urls(self, consts: ModuleType) -> None:
        assert consts.GUEST_ACTIVATE_URL == 'https://api.x.com/1.1/guest/activate.json'
        assert consts.USER_BY_SCREEN_NAME_URL.endswith('/NimuplG1OB7Fd2btCLdBOw/UserByScreenName')
        assert consts.USER_BY_REST_ID_URL.endswith('/tD8zKvQzwY3kdx5yz6YmOw/UserByRestId')
        assert consts.USER_TWEETS_URL.endswith('/QWF3SzpHmykQHsQMixG0cg/UserTweets')
        assert consts.USER_HIGHLIGHTS_TWEETS_URL.endswith('/tHFm_XZc_NNi-CfUThwbNw/UserHighlightsTweets')
        assert consts.TWEET_RESULT_BY_REST_ID_URL.endswith('/Xl5pC_lBk_gcO2ItU39DQw/TweetResultByRestId')

    def test_features_keysets(self, consts: ModuleType) -> None:
        # 键集与 twikit constants.py 同名 dict 逐项一致(FEATURES 21 / USER 11 / HIGHLIGHTS 24 / TWEET_RESULT 24)
        assert len(consts.FEATURES) == 21
        assert len(consts.USER_FEATURES) == 11
        assert len(consts.USER_HIGHLIGHTS_TWEETS_FEATURES) == 24
        assert len(consts.TWEET_RESULT_BY_REST_ID_FEATURES) == 24
        assert consts.FEATURES['rweb_video_timestamps_enabled'] is True
        assert consts.USER_FEATURES['hidden_profile_likes_enabled'] is True
        assert consts.TWEET_RESULT_BY_REST_ID_FEATURES['articles_preview_enabled'] is True


class TestModels:
    """Pydantic 数据模型测试(零网络)"""

    @pytest.fixture
    def model(self) -> ModuleType:
        from src.utils.twitter_x_api import model
        return model

    def test_user_parse(self, model: ModuleType) -> None:
        user = model.TwitterUser.model_validate(_user_result_payload())
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

    def test_user_entities_url_extract(self, model: ModuleType) -> None:
        payload = _user_result_payload()
        payload['legacy']['entities'] = {
            'description': {'urls': [
                {'url': 'https://t.co/d', 'display_url': 'd.com', 'expanded_url': 'https://d.com/'}
            ]},
            'url': {'urls': [
                {'url': 'https://t.co/u', 'display_url': 'u.com', 'expanded_url': 'https://u.com/'}
            ]},
        }
        user = model.TwitterUser.model_validate(payload)
        assert user.description_urls[0].display_url == 'd.com'
        assert user.urls[0].expanded_url == 'https://u.com/'

    def test_user_no_legacy_passthrough(self, model: ModuleType) -> None:
        # 无 legacy 键时不拍平, rest_id 仍可解析
        assert model.TwitterUser.model_validate({'rest_id': '1'}).id == '1'

    def test_user_created_at_invalid(self, model: ModuleType) -> None:
        user = model.TwitterUser.model_validate(_user_result_payload(created_at='not a date'))
        assert user.created_at_datetime is None

    def test_tweet_parse(self, model: ModuleType) -> None:
        tweet = model.TwitterTweet.model_validate(_tweet_result_payload())
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

    def test_tweet_note_tweet_override(self, model: ModuleType) -> None:
        # 长推文: note_tweet 的 text/entity_set 覆盖 full_text/urls/hashtags
        payload = _tweet_result_payload()
        payload['note_tweet_results'] = {'result': {
            'text': 'long text ' * 100,
            'entity_set': {
                'urls': [{'url': 'https://t.co/n', 'display_url': 'n.com', 'expanded_url': 'https://n.com/'}],
                'hashtags': [{'text': 'longtag'}],
            },
        }}
        tweet = model.TwitterTweet.model_validate(payload)
        assert tweet.text == 'hello https://t.co/abc #tag'  # text 保持 legacy full_text
        assert tweet.full_text == 'long text ' * 100
        assert tweet.urls[0].expanded_url == 'https://n.com/'
        assert tweet.hashtags == ['longtag']

    @pytest.mark.parametrize(
        ('result_key', 'attr', 'rest_id'),
        [
            pytest.param('quoted_status_result', 'quote', '1790000000000000000', id='quote'),
            pytest.param('legacy.retweeted_status_result', 'retweeted_tweet', '1800000000000000000', id='retweeted'),
        ],
    )
    def test_tweet_quote_and_retweeted(
            self, model: ModuleType, result_key: str, attr: str, rest_id: str,
    ) -> None:
        payload = _tweet_result_payload()
        _set_deep(payload, result_key, {'result': _tweet_result_payload(rest_id=rest_id)})
        tweet = model.TwitterTweet.model_validate(payload)
        assert (parsed := getattr(tweet, attr)) is not None
        assert parsed.id == rest_id

    @pytest.mark.parametrize(
        ('result_key', 'attr'),
        [
            pytest.param('quoted_status_result', 'quote', id='quote'),
            pytest.param('legacy.retweeted_status_result', 'retweeted_tweet', id='retweeted'),
        ],
    )
    def test_tweet_quote_and_retweeted_tombstone_skipped(self, model: ModuleType, result_key: str, attr: str) -> None:
        # 墓碑推文被跳过(twikit 在转推墓碑场景 KeyError 崩溃, 项目归一为 None)
        payload = _tweet_result_payload()
        _set_deep(payload, result_key, {'result': {'__typename': 'TweetTombstone', 'text': 'unavailable'}})
        tweet = model.TwitterTweet.model_validate(payload)
        assert getattr(tweet, attr) is None

    def test_tweet_community_note(self, model: ModuleType) -> None:
        payload = _tweet_result_payload()
        payload['birdwatch_pivot'] = {'note': {'rest_id': '1'}, 'subtitle': {'text': 'note text'}}
        tweet = model.TwitterTweet.model_validate(payload)
        assert tweet.community_note is not None
        assert tweet.community_note.id == '1'
        assert tweet.community_note.text == 'note text'

    def test_tweet_card_thumbnail(self, model: ModuleType) -> None:
        payload = _tweet_result_payload()
        payload['card'] = {'legacy': {'binding_values': [
            {'key': 'title', 'value': {'string_value': 'card title'}},
            {'key': 'thumbnail_image_original',
             'value': {'image_value': {'url': 'https://pbs.twimg.com/card_img.jpg'}}},
        ]}}
        tweet = model.TwitterTweet.model_validate(payload)
        assert tweet.has_card is True
        assert tweet.thumbnail_title == 'card title'
        assert tweet.thumbnail_url == 'https://pbs.twimg.com/card_img.jpg'

    def test_tweet_no_card(self, model: ModuleType) -> None:
        tweet = model.TwitterTweet.model_validate(_tweet_result_payload())
        assert tweet.has_card is False
        assert tweet.thumbnail_title is None
        assert tweet.thumbnail_url is None

    def test_tweet_video_streams(self, model: ModuleType) -> None:
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
        tweet = model.TwitterTweet.model_validate(payload)
        media = tweet.media[0]
        assert media.type == 'video'
        assert media.video_info is not None
        assert media.video_info.duration_millis == 30000
        assert [x.bitrate for x in media.streams] == [832000, 2176000]  # 非 video/* 变体被过滤

    def test_highlight_result_and_activate_result(self, model: ModuleType) -> None:
        assert model.TwitterGuestActivateResult.model_validate({'guest_token': '123'}).guest_token == '123'
        empty = model.TwitterHighlightTweetsResult()
        assert empty.tweets == []
        assert empty.next_cursor is None
        assert empty.previous_cursor is None

    def test_optional_url_empty_string_coerced_to_none(self, model: ModuleType) -> None:
        # OptionalUrl 将空字符串 URL 归一为 None 而非抛 ValidationError
        payload = _user_result_payload()
        payload['legacy']['profile_image_url_https'] = ''
        payload['legacy']['profile_banner_url'] = ''
        payload['legacy']['url'] = ''
        user = model.TwitterUser.model_validate(payload)
        assert user.profile_image_url is None
        assert user.profile_banner_url is None
        assert user.url is None

        media = model.TwitterMedia.model_validate({
            'id_str': '1',
            'media_url_https': '',
            'url': '',
            'expanded_url': '',
        })
        assert media.media_url is None
        assert media.url is None
        assert media.expanded_url is None

    def test_id_int_coerced_to_str(self, model: ModuleType) -> None:
        # coerce_numbers_to_str: rest_id/id_str 为 int 时强转为 str
        assert model.TwitterUser.model_validate({'rest_id': 783214}).id == '783214'
        assert model.TwitterMedia.model_validate({'id_str': 1900000000000000000}).id == '1900000000000000000'

    def test_media_missing_id_raises(self, model: ModuleType) -> None:
        # id_str 为必填字段(媒体数据缺 id 视为残缺数据)
        with pytest.raises(ValidationError):
            model.TwitterMedia.model_validate({'type': 'photo'})

    def test_media_explicit_size_wins_over_original_info(self, model: ModuleType) -> None:
        # original_info 提取使用 setdefault: 顶层已存在 width/height 时不覆盖
        media = model.TwitterMedia.model_validate({
            'id_str': '1',
            'width': 100,
            'height': 50,
            'original_info': {'width': 800, 'height': 600},
        })
        assert media.width == 100
        assert media.height == 50

    def test_media_streams_empty_without_video_info(self, model: ModuleType) -> None:
        media = model.TwitterMedia.model_validate({'id_str': '1', 'type': 'photo'})
        assert media.video_info is None
        assert media.streams == []

    def test_tweet_view_count_int_coerced(self, model: ModuleType) -> None:
        payload = _tweet_result_payload()
        payload['views'] = {'count': 12345, 'state': 'EnabledWithCount'}
        tweet = model.TwitterTweet.model_validate(payload)
        assert tweet.view_count == '12345'

    def test_tweet_hashtags_non_dict_filtered(self, model: ModuleType) -> None:
        payload = _tweet_result_payload()
        payload['legacy']['entities']['hashtags'] = [{'text': 'a'}, 'broken', {'no_text': 1}, None]
        tweet = model.TwitterTweet.model_validate(payload)
        assert tweet.hashtags == ['a']

    @pytest.mark.parametrize(
        ('result_key', 'attr', 'rest_id'),
        [
            pytest.param('quoted_status_result', 'quote', '1790000000000000001', id='quote'),
            pytest.param('legacy.retweeted_status_result', 'retweeted_tweet', '1800000000000000001', id='retweeted'),
        ],
    )
    def test_tweet_quote_and_retweeted_wrapped_in_tweet_key(
            self, model: ModuleType, result_key: str, attr: str, rest_id: str,
    ) -> None:
        # 引用/转推推文 result 内再包一层 tweet 键时可正确解包
        payload = _tweet_result_payload()
        _set_deep(payload, result_key, {'result': {'tweet': _tweet_result_payload(rest_id=rest_id)}})
        tweet = model.TwitterTweet.model_validate(payload)
        assert (parsed := getattr(tweet, attr)) is not None
        assert parsed.id == rest_id

    def test_tweet_quote_missing_core_or_legacy_skipped(self, model: ModuleType) -> None:
        payload = _tweet_result_payload()
        quoted = _tweet_result_payload(rest_id='1790000000000000002')
        del quoted['core']
        payload['quoted_status_result'] = {'result': quoted}
        tweet = model.TwitterTweet.model_validate(payload)
        assert tweet.quote is None


class TestParseTweetFromData:
    """helper.py 推文解析守卫测试(零网络)"""

    @pytest.fixture
    def parse_tweet_from_data(self) -> Callable[..., Any]:
        from src.utils.twitter_x_api.helper import parse_tweet_from_data
        return parse_tweet_from_data

    def test_parse_from_timeline_entry(self, parse_tweet_from_data: Callable[..., Any]) -> None:
        tweet = parse_tweet_from_data(_timeline_entry('tweet-1780000000000000000'))
        assert tweet is not None
        assert tweet.id == '1780000000000000000'

    def test_parse_from_tweet_result_response(self, parse_tweet_from_data: Callable[..., Any]) -> None:
        tweet = parse_tweet_from_data({'data': {'tweet_result': {'result': _tweet_result_payload()}}})
        assert tweet is not None
        assert tweet.id == '1780000000000000000'

    def test_parse_tombstone_returns_none(self, parse_tweet_from_data: Callable[..., Any]) -> None:
        assert parse_tweet_from_data({'tweet_result': {'result': {'__typename': 'TweetTombstone'}}}) is None

    def test_parse_tweet_wrapper_unwrapped(self, parse_tweet_from_data: Callable[..., Any]) -> None:
        # 部分 entry 的 result 内再包一层 tweet 键
        tweet = parse_tweet_from_data({'tweet_results': {'result': {'tweet': _tweet_result_payload()}}})
        assert tweet is not None
        assert tweet.id == '1780000000000000000'

    def test_parse_missing_core_or_legacy_returns_none(self, parse_tweet_from_data: Callable[..., Any]) -> None:
        payload = _tweet_result_payload()
        del payload['core']
        assert parse_tweet_from_data({'tweet_results': {'result': payload}}) is None

        payload = _tweet_result_payload()
        del payload['legacy']
        assert parse_tweet_from_data({'tweet_results': {'result': payload}}) is None

    def test_parse_no_result_returns_none(self, parse_tweet_from_data: Callable[..., Any]) -> None:
        assert parse_tweet_from_data({'data': {'tweet_result': {}}}) is None
        assert parse_tweet_from_data({}) is None

    def test_parse_validation_failure_returns_none(self, parse_tweet_from_data: Callable[..., Any]) -> None:
        # 通过结构守卫但模型校验失败(如缺 rest_id)时返回 None 而非抛 ValidationError
        payload = _tweet_result_payload()
        del payload['rest_id']
        assert parse_tweet_from_data({'tweet_results': {'result': payload}}) is None

    def test_parse_wrapped_tombstone_returns_none(self, parse_tweet_from_data: Callable[..., Any]) -> None:
        # 墓碑推文被 tweet 键包裹: 解包后缺 core 同样返回 None
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


class TestGuestRequestAssembly:
    """guest.py 各 API 的请求组装(端点/variables/features/headers, 零网络)"""

    @pytest.fixture
    def twitter_guest(self) -> type['TwitterGuest']:
        from src.utils.twitter_x_api.guest import TwitterGuest
        return TwitterGuest

    @pytest.fixture
    def consts(self) -> ModuleType:
        from src.utils.twitter_x_api import consts
        return consts

    async def test_get_user_by_screen_name(
            self, twitter_guest: type['TwitterGuest'], consts: ModuleType, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from src.utils.twitter_x_api.model import TwitterUser

        captured: dict[str, Any] = {}
        _patch_offline_request(monkeypatch, get_side_effects=[_user_response()], captured=captured)

        user = await twitter_guest.get_user_by_screen_name('X')

        assert isinstance(user, TwitterUser)
        assert user.screen_name == 'X'
        assert captured['url'] == consts.USER_BY_SCREEN_NAME_URL
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

    async def test_get_user_by_id(
            self, twitter_guest: type['TwitterGuest'], consts: ModuleType, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}
        _patch_offline_request(monkeypatch, get_side_effects=[_user_response()], captured=captured)

        user = await twitter_guest.get_user_by_id(783214)

        assert user.id == '783214'  # int 入参经 str() 序列化
        assert captured['url'] == consts.USER_BY_REST_ID_URL
        variables = ujson.loads(captured['params']['variables'])
        assert variables == {'userId': '783214', 'withSafetyModeUserFields': True}
        assert 'fieldToggles' not in captured['params']

    async def test_get_user_tweets(
            self, twitter_guest: type['TwitterGuest'], consts: ModuleType, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
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

        tweets = await twitter_guest.get_user_tweets('783214', count=5)

        assert [x.id for x in tweets] == ['1780000000000000000', '1781111111111111111']  # promoted 条目被过滤
        assert captured['url'] == consts.USER_TWEETS_URL
        variables = ujson.loads(captured['params']['variables'])
        assert variables == {
            'userId': '783214', 'count': 5, 'includePromotedContent': True,
            'withQuickPromoteEligibilityTweetFields': True, 'withVoice': True, 'withV2Timeline': True,
        }
        # features 与 consts.FEATURES 全量一致
        assert ujson.loads(captured['params']['features']) == dict(consts.FEATURES)

    async def test_get_user_tweets_empty_instructions(
            self, twitter_guest: type['TwitterGuest'], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_offline_request(monkeypatch, get_side_effects=[{'data': None}])
        assert await twitter_guest.get_user_tweets('783214') == []

        # TimelineAddEntries 缺失(TimelineTerminateTimeline) → 空列表
        response = {'data': {'user': {'result': {'timeline': {'timeline': {
            'instructions': [{'type': 'TimelineTerminateTimeline', 'direction': 'Top'}]
        }}}}}}
        _patch_offline_request(monkeypatch, get_side_effects=[response])
        assert await twitter_guest.get_user_tweets('783214') == []

    async def test_get_tweet_by_id(
            self, twitter_guest: type['TwitterGuest'], consts: ModuleType, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}
        _patch_offline_request(
            monkeypatch,
            get_side_effects=[{'data': {'tweet_result': {'result': _tweet_result_payload()}}}],
            captured=captured,
        )

        tweet = await twitter_guest.get_tweet_by_id('1780000000000000000')

        assert tweet.id == '1780000000000000000'
        assert captured['url'] == consts.TWEET_RESULT_BY_REST_ID_URL
        variables = ujson.loads(captured['params']['variables'])
        assert variables == {'tweetId': '1780000000000000000', 'withCommunity': False,
                             'includePromotedContent': False, 'withVoice': False}
        toggles = ujson.loads(captured['params']['fieldToggles'])
        assert toggles == {'withArticleRichContentState': True, 'withArticlePlainText': False, 'withGrokAnalyze': False}

    async def test_get_tweet_by_id_not_found_raises(
            self, twitter_guest: type['TwitterGuest'], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from src.exception import WebSourceException

        _patch_offline_request(monkeypatch, get_side_effects=[{'data': {'tweet_result': {}}}])

        with pytest.raises(WebSourceException) as exc_info:
            await twitter_guest.get_tweet_by_id('1999999999999999999')
        assert exc_info.value.status_code == 404

    async def test_get_user_highlights_tweets(
            self, twitter_guest: type['TwitterGuest'], consts: ModuleType, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from src.utils.twitter_x_api.model import TwitterHighlightTweetsResult

        entries = [
            _timeline_entry('tweet-1780000000000000000'),
            _cursor_entry('cursor-top-abc', 'prev-cursor'),
            _cursor_entry('cursor-bottom-xyz', 'next-cursor'),
        ]
        captured: dict[str, Any] = {}
        _patch_offline_request(monkeypatch, get_side_effects=[_timeline_response(entries)], captured=captured)

        result = await twitter_guest.get_user_highlights_tweets('783214', count=20, cursor='prev-cursor')

        assert isinstance(result, TwitterHighlightTweetsResult)
        assert [x.id for x in result.tweets] == ['1780000000000000000']
        assert result.next_cursor == 'next-cursor'
        assert result.previous_cursor == 'prev-cursor'
        variables = ujson.loads(captured['params']['variables'])
        assert variables == {'userId': '783214', 'count': 20, 'includePromotedContent': True,
                             'withVoice': True, 'cursor': 'prev-cursor'}
        assert captured['url'] == consts.USER_HIGHLIGHTS_TWEETS_URL

    async def test_get_user_highlights_tweets_empty(
            self, twitter_guest: type['TwitterGuest'], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_offline_request(monkeypatch, get_side_effects=[{'data': None}])
        result = await twitter_guest.get_user_highlights_tweets('783214')
        assert result.tweets == []
        assert result.next_cursor is None

    @pytest.mark.parametrize(
        'instructions',
        [
            pytest.param(None, id='null'),
            pytest.param({'type': 'x'}, id='not_list'),
        ],
    )
    async def test_get_user_tweets_malformed_instructions(
            self, twitter_guest: type['TwitterGuest'], monkeypatch: pytest.MonkeyPatch, instructions: Any,
    ) -> None:
        # instructions 显式为 null 或为 dict 等畸形结构时按空时间线返回而非 TypeError
        response = {'data': {'user': {'result': {'timeline_v2': {'timeline': {'instructions': instructions}}}}}}
        _patch_offline_request(monkeypatch, get_side_effects=[response])
        assert await twitter_guest.get_user_tweets('783214') == []

    async def test_get_user_tweets_malformed_entries_skipped(
            self, twitter_guest: type['TwitterGuest'], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # entries 中的非 dict 条目与非 str entryId 被跳过, 不影响其余条目
        entries = [
            'broken',
            None,
            {'entryId': None},
            {'entryId': 123},
            _timeline_entry('tweet-1780000000000000000'),
        ]
        response = _timeline_response(entries, timeline_key='timeline_v2')
        _patch_offline_request(monkeypatch, get_side_effects=[response])
        tweets = await twitter_guest.get_user_tweets('783214')
        assert [x.id for x in tweets] == ['1780000000000000000']

    @pytest.mark.parametrize(
        ('timeline', 'expected_ids'),
        [
            pytest.param({'instructions': None}, [], id='instructions_null'),
            pytest.param(
                {'instructions': [{'type': 'TimelineAddEntries', 'entries': [
                    _timeline_entry('tweet-1780000000000000000'),
                    {'entryId': 'cursor-top-1'},  # 无 content 键
                    {'entryId': 'cursor-bottom-1', 'content': None},  # content 非 dict
                    'broken',
                ]}]},
                ['1780000000000000000'],
                id='malformed_cursor_entries',
            ),
        ],
    )
    async def test_get_user_highlights_malformed_structure(
            self, twitter_guest: type['TwitterGuest'], monkeypatch: pytest.MonkeyPatch,
            timeline: dict[str, Any], expected_ids: list[str],
    ) -> None:
        # highlights 的 instructions 为 null 时返回空结果; 游标条目缺 content 或 content 非 dict 时游标归 None,
        # 畸形条目被跳过
        response = {'data': {'user': {'result': {'timeline': {'timeline': timeline}}}}}
        _patch_offline_request(monkeypatch, get_side_effects=[response])
        result = await twitter_guest.get_user_highlights_tweets('783214')
        assert [x.id for x in result.tweets] == expected_ids
        assert result.previous_cursor is None
        assert result.next_cursor is None


class TestGuestSession:
    """api_base.py 访客会话管理(activate/缓存/401 重试, 零网络)"""

    @pytest.fixture
    def twitter_guest(self) -> type['TwitterGuest']:
        from src.utils.twitter_x_api.guest import TwitterGuest
        return TwitterGuest

    @pytest.fixture
    def base_twitter_api(self) -> type['BaseTwitterAPI']:
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI
        return BaseTwitterAPI

    @pytest.fixture
    def web_source_exception(self) -> type['WebSourceException']:
        from src.exception import WebSourceException
        return WebSourceException

    async def test_activate(self, twitter_guest: type['TwitterGuest'], monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.twitter_x_api.consts import GUEST_ACTIVATE_URL

        captured: dict[str, Any] = {}
        _patch_offline_request(
            monkeypatch, guest_token=None,
            post_side_effects=[{'guest_token': 'gt_new_token'}], captured=captured,
        )

        token = await twitter_guest.activate()

        assert token == 'gt_new_token'
        # token 已缓存(cls._activate_guest 写在 cls 即 TwitterGuest 上)
        assert twitter_guest._guest_token == 'gt_new_token'
        assert captured['url'] == GUEST_ACTIVATE_URL
        assert captured['data'] == {}
        headers = captured['headers']
        assert 'x-twitter-active-user' not in headers  # activate 时移除
        assert 'x-guest-token' not in headers  # activate 前尚无 token

    async def test_ensure_guest_token_cached(
            self, base_twitter_api: type['BaseTwitterAPI'], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _patch_offline_request(monkeypatch, guest_token='gt_cached')
        assert await base_twitter_api._ensure_guest_token() == 'gt_cached'
        # 无 post side effect 也未调用 activate: 若调用会 AssertionError

    async def test_gql_retry_on_401(
            self, twitter_guest: type['TwitterGuest'], web_source_exception: type['WebSourceException'],
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}
        _patch_offline_request(
            monkeypatch, guest_token='gt_stale',
            get_side_effects=[
                web_source_exception(401, 'test unauthorized'),
                _user_response(),
            ],
            post_side_effects=[{'guest_token': 'gt_refreshed'}],
            captured=captured,
        )

        user = await twitter_guest.get_user_by_screen_name('X')

        assert user.screen_name == 'X'  # 重试成功
        # 第一次 GET 401(stale token) → reset → activate(POST) → 第二次 GET(refreshed token)
        assert captured['method'] == 'GET'
        assert captured['headers']['x-guest-token'] == 'gt_refreshed'

    @pytest.mark.parametrize(
        ('get_effects', 'post_effects', 'expected_status', 'expected_message'),
        [
            pytest.param(
                [(403, 'test forbidden'), (403, 'test forbidden again')], [{'guest_token': 'gt_refreshed'}],
                403, 'test forbidden again',
                id='retry_on_403_only_once',
            ),
            pytest.param(
                [(404, 'test not found')], [],
                404, 'test not found',
                id='no_retry_on_404',
            ),
            pytest.param(
                [(401, 'test unauthorized')], [(403, 'test activate blocked')],
                403, 'test activate blocked',
                id='activate_failure_propagates',
            ),
        ],
    )
    async def test_gql_retry_behavior(
            self, twitter_guest: type['TwitterGuest'], web_source_exception: type['WebSourceException'],
            monkeypatch: pytest.MonkeyPatch,
            get_effects: list[Any], post_effects: list[Any], expected_status: int, expected_message: str,
    ) -> None:
        # 401/403 重试一次后仍失败(或重试链中 activate 自身失败)则抛出; 404 等状态码不重试直接抛出
        _patch_offline_request(
            monkeypatch, guest_token='gt_stale',
            get_side_effects=[web_source_exception(*error) for error in get_effects],
            post_side_effects=[
                web_source_exception(*effect) if isinstance(effect, tuple) else effect
                for effect in post_effects
            ],
        )

        with pytest.raises(web_source_exception) as exc_info:
            await twitter_guest.get_user_by_screen_name('X')
        assert exc_info.value.status_code == expected_status
        assert exc_info.value.message == expected_message

    async def test_download_resource_delegates(
            self, base_twitter_api: type['BaseTwitterAPI'], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # download_resource 走 BaseCommonAPI._download_resource, 此处仅验证透传不被 guest 状态干扰
        captured: dict[str, Any] = {}

        async def _fake_download(cls: type, **kwargs: Any) -> str:
            captured.update(kwargs)
            return 'fake'

        monkeypatch.setattr(base_twitter_api, '_download_resource', classmethod(_fake_download))
        result = await base_twitter_api.download_resource('https://pbs.twimg.com/media/xxx.jpg')
        assert result == 'fake'
        assert captured['url'] == 'https://pbs.twimg.com/media/xxx.jpg'

    async def test_activate_malformed_response_raises(
            self, twitter_guest: type['TwitterGuest'], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # activate 响应缺 guest_token 字段时抛出 ValidationError
        _patch_offline_request(monkeypatch, guest_token=None, post_side_effects=[{'unexpected': 'shape'}])

        with pytest.raises(ValidationError):
            await twitter_guest.activate()

    @pytest.mark.parametrize(
        ('response', 'screen_name', 'message_parts', 'max_message_len'),
        [
            pytest.param(
                {'data': {'user': None}}, 'no_such_user_xyz', [], None,
                id='user_data_missing',
            ),
            pytest.param(
                {'data': {'user': {'result': {'__typename': 'UserUnavailable', 'reason': 'suspended'}}}},
                'suspended_user', ['parse error'], None,
                id='user_unavailable',
            ),
            pytest.param(
                {'data': {'user': None}, 'padding': 'x' * 5000}, 'X', ['user data not found'], 1000,
                id='message_truncated',
            ),
        ],
    )
    async def test_user_missing_raises(
            self, twitter_guest: type['TwitterGuest'], web_source_exception: type['WebSourceException'],
            monkeypatch: pytest.MonkeyPatch,
            response: dict[str, Any], screen_name: str, message_parts: list[str], max_message_len: int | None,
    ) -> None:
        # 上游 200 但用户数据缺失/不可用(如用户不存在或封禁账号)时统一抛出 WebSourceException(400);
        # 异常消息中的响应体被截断, 不整体进入异常消息与日志
        _patch_offline_request(monkeypatch, get_side_effects=[response])

        with pytest.raises(web_source_exception) as exc_info:
            await twitter_guest.get_user_by_screen_name(screen_name)
        assert exc_info.value.status_code == 400
        for part in message_parts:
            assert part in exc_info.value.message
        if max_message_len is not None:
            assert len(exc_info.value.message) < max_message_len

    def test_reset_guest_state(self, twitter_guest: type['TwitterGuest'], monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(twitter_guest, '_guest_token', 'gt')
        monkeypatch.setattr(twitter_guest, '_client_transaction', object())
        monkeypatch.setattr(twitter_guest, '_client_transaction_unavailable', True)

        twitter_guest._reset_guest_state()

        assert twitter_guest._guest_token is None
        assert twitter_guest._client_transaction is None
        assert twitter_guest._client_transaction_unavailable is False


class TestApiBaseHeaders:
    """api_base.py 请求头构造(零网络)"""

    @pytest.fixture
    def base_twitter_api(self) -> type['BaseTwitterAPI']:
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI
        return BaseTwitterAPI

    def test_api_headers_default(self, base_twitter_api: type['BaseTwitterAPI']) -> None:
        headers = base_twitter_api._get_api_headers()
        assert headers['authorization'].startswith('Bearer ')
        assert headers['content-type'] == 'application/json'
        assert headers['origin'] == 'https://x.com'
        assert headers['referer'] == 'https://x.com/'
        assert headers['sec-fetch-dest'] == 'empty'
        assert headers['sec-fetch-mode'] == 'cors'
        assert headers['sec-fetch-site'] == 'same-site'
        assert headers['x-twitter-active-user'] == 'yes'
        assert 'x-guest-token' not in headers

    def test_api_headers_with_guest_token(self, base_twitter_api: type['BaseTwitterAPI']) -> None:
        headers = base_twitter_api._get_api_headers(guest_token='gt_x')
        assert headers['x-guest-token'] == 'gt_x'

    def test_api_headers_without_active_user(self, base_twitter_api: type['BaseTwitterAPI']) -> None:
        # activate 场景不携带 x-twitter-active-user
        headers = base_twitter_api._get_api_headers(with_active_user=False)
        assert 'x-twitter-active-user' not in headers

    def test_transaction_headers_without_transaction(self, base_twitter_api: type['BaseTwitterAPI']) -> None:
        # transaction 不可用时降级为空 headers
        assert base_twitter_api._get_transaction_headers('GET', 'https://x.com/i/api/graphql/qid/Endpoint', None) == {}

    def test_transaction_headers_with_transaction(self, base_twitter_api: type['BaseTwitterAPI']) -> None:
        # transaction 可用时按 method+path(不含 query) 生成 ctid
        class _FakeTransaction:
            @staticmethod
            def generate_transaction_id(method: str, path: str) -> str:
                assert method == 'GET'
                assert path == '/i/api/graphql/qid/Endpoint'  # query 已被剥离
                return 'fake-tid'

        headers = base_twitter_api._get_transaction_headers(
            'GET', 'https://x.com/i/api/graphql/qid/Endpoint?variables=%7B%7D', _FakeTransaction()
        )
        assert headers == {'x-client-transaction-id': 'fake-tid'}


def _decode_tid(tid: str) -> bytes:
    """解码 base64+XOR 编码的 transaction id: 补回 base64 padding 后, 以首字节为随机数异或解码其余字节"""
    decoded = base64.b64decode(tid + '==')
    return bytes(b ^ decoded[0] for b in decoded[1:])

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


_NO_KEY_META_HTML = _make_transaction_html().replace(
    f'<meta name="twitter-site-verification" content="{_TX_KEY}"/>', ''
)
"""合成首页变体: 缺 twitter-site-verification meta(触发 _get_key 抛 "Couldn't get key")"""

_BROKEN_FRAMES_HTML = (
    '<html><head>'
    f'<meta name="twitter-site-verification" content="{_TX_KEY}"/>'
    f"<script>var a = {{'ondemand.s': 'abc123'}};</script>"
    '</head><body>'
    '<svg id="loading-x-anim-0"><g><path/><path d="M123456781 2 3 4 5 6 7 8 9 10 11 12"/></g></svg>'
    '</body></html>'
)
"""合成首页变体: 帧结构残缺(仅 1 帧, 选帧索引越界)"""


class _MappingTxRequester:
    """ClientTransaction 测试用假请求器: 按 URL 映射返回页面并记录请求

    GET 未命中映射时回落 get_fallback(供首页+ondemand.s 两页面的简易场景), POST 未命中一律 AssertionError
    """

    def __init__(self, pages: dict[str, str], *, get_fallback: str | None = None) -> None:
        self._pages = pages
        self._get_fallback = get_fallback
        self.get_urls: list[str] = []
        self.posts: list[tuple[str, Any]] = []

    async def get(self, url: str, **kwargs: Any) -> 'Response':
        self.get_urls.append(url)
        if url in self._pages:
            return _fake_response(self._pages[url])
        if self._get_fallback is not None:
            return _fake_response(self._get_fallback)
        raise AssertionError(f'unexpected GET url in fake requester: {url}')

    async def post(self, url: str, **kwargs: Any) -> 'Response':
        self.posts.append((url, kwargs.get('data')))
        if url not in self._pages:
            raise AssertionError(f'unexpected POST url in fake requester: {url}')
        return _fake_response(self._pages[url])


def _make_tx_requester(home_html: str, ondemand_js: str) -> _MappingTxRequester:
    """ClientTransaction.init 用假请求器: 首页返回合成 HTML, 其余 GET(ondemand.s)返回合成脚本"""
    return _MappingTxRequester({'https://x.com': home_html}, get_fallback=ondemand_js)


class TestTransactionPureFunctions:
    """transaction.py 数值函数测试(与浏览器 Number.toString(16) 行为对齐)"""

    @pytest.fixture
    def transaction(self) -> ModuleType:
        from src.utils.twitter_x_api import transaction
        return transaction

    def test_float_to_hex(self, transaction: ModuleType) -> None:
        # 与 twikit 参考实现行为一致(非浏览器 toString(16)): 无前导零、大写 A-F;
        # '.8' 形态由 _animate 调用方补偿(startswith('.') 时补 0 并 lower)
        assert transaction._float_to_hex(0.0) == ''
        assert transaction._float_to_hex(10.0) == 'A'
        assert transaction._float_to_hex(255.0) == 'FF'
        assert transaction._float_to_hex(0.5) == '.8'
        assert transaction._float_to_hex(1.5) == '1.8'  # 整数位 1, 小数 0.5*16=8

    def test_is_odd(self, transaction: ModuleType) -> None:
        assert transaction._is_odd(1) == -1.0
        assert transaction._is_odd(2) == 0.0

    def test_interpolate_mismatch_raises(self, transaction: ModuleType) -> None:
        with pytest.raises(ValueError, match='Mismatched interpolation'):
            transaction._interpolate([1.0], [1.0, 2.0], 0.5)

    def test_convert_rotation_to_matrix_zero(self, transaction: ModuleType) -> None:
        assert transaction._convert_rotation_to_matrix(0.0) == [1.0, 0.0, 0.0, 1.0]

    def test_cubic_get_value_bounds(self, transaction: ModuleType) -> None:
        cubic = transaction._Cubic([0.25, 0.1, 0.25, 1.0])
        assert cubic.get_value(0.0) == 0.0
        assert cubic.get_value(1.0) == 1.0
        assert 0.0 <= cubic.get_value(0.5) <= 1.0


class TestOnDemandHashExtraction:
    """_extract_on_demand_file_hash 新旧打包格式兼容"""

    @pytest.fixture
    def client_transaction(self) -> type['ClientTransaction']:
        from src.utils.twitter_x_api.transaction import ClientTransaction
        return ClientTransaction

    def test_legacy_format(self, client_transaction: type['ClientTransaction']) -> None:
        assert client_transaction._extract_on_demand_file_hash(_make_transaction_html()) == 'abc123'

    def test_webpack_chunk_format(self, client_transaction: type['ClientTransaction']) -> None:
        html = _make_transaction_html(ondemand_ref=',123:"ondemand.s"') + '<script>var h={,123:"deadbeef"};</script>'
        assert client_transaction._extract_on_demand_file_hash(html) == 'deadbeef'

    def test_no_match_returns_none(self, client_transaction: type['ClientTransaction']) -> None:
        assert client_transaction._extract_on_demand_file_hash('<html><body>nothing</body></html>') is None

    def test_chunk_format_without_hash_returns_none(self, client_transaction: type['ClientTransaction']) -> None:
        # chunk 索引存在但哈希映射表缺失: 返回 None
        html = _make_transaction_html(ondemand_ref=',123:"ondemand.s"')
        assert client_transaction._extract_on_demand_file_hash(html) is None

    def test_chunk_hash_of_other_id_not_matched(self, client_transaction: type['ClientTransaction']) -> None:
        # 哈希映射表中仅有其他 chunk id 的哈希时不误匹配
        html = _make_transaction_html(ondemand_ref=',123:"ondemand.s"') + '<script>var h={,124:"deadbeef"};</script>'
        assert client_transaction._extract_on_demand_file_hash(html) is None


class TestClientTransaction:
    """ClientTransaction 初始化与 transaction id 生成(合成首页, 零网络)"""

    @pytest.fixture
    def client_transaction(self) -> type['ClientTransaction']:
        from src.utils.twitter_x_api.transaction import ClientTransaction
        return ClientTransaction

    async def test_init_and_generate(self, client_transaction: type['ClientTransaction']) -> None:
        ct = client_transaction()
        requester = _make_tx_requester(_make_transaction_html(), _make_ondemand_js())
        await ct.init(requester=requester)

        assert ct.is_initialized is True
        assert 'https://x.com' in requester.get_urls
        assert any('ondemand.s.abc123a.js' in url for url in requester.get_urls)

        tid = ct.generate_transaction_id('GET', '/i/api/graphql/x/UserByScreenName', time_now=1000)
        assert isinstance(tid, str)
        assert tid
        assert '=' not in tid  # base64 padding 已剥离
        assert len(base64.b64decode(tid + '==')) == 54  # 1(random) + 32(key) + 4(time) + 16(hash) + 1(const)

        # 首字节为随机数, 其余字节为 XOR(random) 编码: 解码后 key/time 段确定性可断言
        payload = _decode_tid(tid)
        assert list(payload[:32]) == _TX_KEY_BYTES  # key 段
        assert payload[32:36] == (1000).to_bytes(4, 'little')  # time_now=1000 小端 4 字节
        assert payload[-1] == client_transaction._ADDITIONAL_RANDOM_NUMBER  # 常量尾字节

        # 首字节随 random_num 波动, 不同调用产生不同 id(随机数碰撞除外)
        tids = {ct.generate_transaction_id('GET', '/x', time_now=1000) for _ in range(8)}
        assert len(tids) > 1, 'transaction id 首字节应携带随机数, 多次调用不应全同'

    async def test_generate_with_explicit_zero_time(self, client_transaction: type['ClientTransaction']) -> None:
        # 显式 time_now=0 不被覆盖为当前时间
        ct = client_transaction()
        await ct.init(requester=_make_tx_requester(_make_transaction_html(), _make_ondemand_js()))

        zero_tid = ct.generate_transaction_id('GET', '/x', time_now=0)
        assert _decode_tid(zero_tid)[32:36] == b'\x00\x00\x00\x00'  # key(32) 之后 4 字节时间位为零
        # 不显式传 time_now(即真实当前时间)时时间位非全零, 与 0 时刻区分
        assert _decode_tid(ct.generate_transaction_id('GET', '/x'))[32:36] != b'\x00\x00\x00\x00'

    @pytest.mark.parametrize(
        ('home_html', 'ondemand_js', 'expected_exc', 'match'),
        [
            pytest.param('', '', RuntimeError, None, id='bad_home_page'),  # 空 HTML 解析失败
            pytest.param(
                _NO_KEY_META_HTML, _make_ondemand_js(), RuntimeError, None,
                id='missing_key_meta',  # 首页缺 twitter-site-verification meta
            ),
            pytest.param(_make_transaction_html(), 'no indices here', RuntimeError, 'KEY_BYTE', id='missing_indices'),
            pytest.param(_BROKEN_FRAMES_HTML, _make_ondemand_js(), IndexError, None, id='broken_frames'),
        ],
    )
    async def test_init_failure(
            self, client_transaction: type['ClientTransaction'],
            home_html: str, ondemand_js: str, expected_exc: type[Exception], match: str | None,
    ) -> None:
        # 首页或 ondemand.s 结构残缺时 init 抛错, 由上层 _ensure_client_transaction 降级为不携带 ctid
        ct = client_transaction()
        with pytest.raises(expected_exc, match=match):
            await ct.init(requester=_make_tx_requester(home_html, ondemand_js))

    def test_generate_before_init_raises(self, client_transaction: type['ClientTransaction']) -> None:
        with pytest.raises(RuntimeError, match='not initialized'):
            client_transaction().generate_transaction_id('GET', '/x')


class TestEnsureClientTransaction:
    """api_base.py _ensure_client_transaction 三态(成功缓存/失败置位/重置重试, 零网络)"""

    @pytest.fixture
    def base_twitter_api(self) -> type['BaseTwitterAPI']:
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI
        return BaseTwitterAPI

    @pytest.fixture
    def client_transaction(self) -> type['ClientTransaction']:
        from src.utils.twitter_x_api.transaction import ClientTransaction
        return ClientTransaction

    @pytest.fixture
    def twitter_guest(self) -> type['TwitterGuest']:
        from src.utils.twitter_x_api.guest import TwitterGuest
        return TwitterGuest

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

    async def test_success_and_cached(
            self, base_twitter_api: type['BaseTwitterAPI'], monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        counter: list[int] = []
        self._patch_init_success(monkeypatch, counter)
        monkeypatch.setattr(base_twitter_api, '_client_transaction', None)
        monkeypatch.setattr(base_twitter_api, '_client_transaction_unavailable', False)

        transaction = await base_twitter_api._ensure_client_transaction()

        assert transaction is not None
        assert transaction.is_initialized is True
        assert len(counter) == 1

        # 二次调用复用缓存, 不重复初始化
        assert await base_twitter_api._ensure_client_transaction() is transaction
        assert len(counter) == 1

    async def test_failure_marks_unavailable_and_no_repeat(
            self, base_twitter_api: type['BaseTwitterAPI'], client_transaction: type['ClientTransaction'],
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        counter: list[int] = []

        async def _failing_init(self: 'ClientTransaction', requester: Any) -> None:
            counter.append(1)
            raise RuntimeError('test init failed')

        monkeypatch.setattr(client_transaction, 'init', _failing_init)
        monkeypatch.setattr(base_twitter_api, '_client_transaction', None)
        monkeypatch.setattr(base_twitter_api, '_client_transaction_unavailable', False)

        assert await base_twitter_api._ensure_client_transaction() is None
        assert len(counter) == 1
        assert base_twitter_api._client_transaction_unavailable is True

        # 置位后不再重复尝试
        assert await base_twitter_api._ensure_client_transaction() is None
        assert len(counter) == 1

        # 重置访客状态后允许再次尝试
        base_twitter_api._reset_guest_state()
        assert base_twitter_api._client_transaction_unavailable is False
        assert await base_twitter_api._ensure_client_transaction() is None
        assert len(counter) == 2

    async def test_gql_request_carries_transaction_id_when_available(
            self, base_twitter_api: type['BaseTwitterAPI'], twitter_guest: type['TwitterGuest'],
            monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # transaction 初始化成功时, GQL 请求携带 x-client-transaction-id
        captured: dict[str, Any] = {}
        _patch_offline_request(monkeypatch, get_side_effects=[_user_response()], captured=captured)
        counter: list[int] = []
        self._patch_init_success(monkeypatch, counter)
        # _patch_offline_request 将 transaction 置为不可用, 此处恢复为可初始化
        for target_cls in (base_twitter_api, twitter_guest):
            monkeypatch.setattr(target_cls, '_client_transaction_unavailable', False)

        user = await twitter_guest.get_user_by_screen_name('X')

        assert user.id == '783214'
        assert len(counter) == 1
        assert captured['headers']['x-client-transaction-id']


class TestClientTransactionMigration:
    """ClientTransaction._handle_x_migration 迁移跳转分支(合成页面, 零网络)"""

    @pytest.fixture
    def client_transaction(self) -> type['ClientTransaction']:
        from src.utils.twitter_x_api.transaction import ClientTransaction
        return ClientTransaction

    async def test_meta_refresh_redirect(self, client_transaction: type['ClientTransaction']) -> None:
        # 首页 meta refresh 指向迁移链接: 跟随跳转后在新页面上完成初始化
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

        ct = client_transaction()
        await ct.init(requester=requester)

        assert ct.is_initialized is True
        assert requester.get_urls[0] == 'https://x.com'
        assert migration_url in requester.get_urls

    async def test_migration_form_post(self, client_transaction: type['ClientTransaction']) -> None:
        # 首页含迁移表单: 按表单字段 POST 迁移地址后完成初始化
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

        ct = client_transaction()
        await ct.init(requester=requester)

        assert ct.is_initialized is True
        assert requester.posts == [('https://x.com/x/migrate/?mx=2', {'tok': 'abc123', 'unstable': 'true'})]


class TestConfig:
    """config.py 资源路径配置(零网络)"""

    def test_default_download_folder(self) -> None:
        from src.resource import TemporaryResource
        from src.utils.twitter_x_api.config import twitter_api_config

        folder = twitter_api_config.default_download_folder
        assert isinstance(folder, TemporaryResource)
        assert folder.path.parts[-2:] == ('twitter', 'download')


# 真实请求测试(默认全部跳过, 仅用户主动发起: 设置环境变量 OMEGA_TWITTER_X_LIVE_TEST=1 后运行本文件)
# 依赖 .env.test 的代理配置(OMEGA_REQUESTS_ENABLE_PROXY=true, 127.0.0.1:1081)访问 x.com


@pytest.fixture(scope='class')
async def live_user() -> 'TwitterUser':
    """官方账号 X 的用户对象(TestTwitterGuestLive 全类共享一次取样, 避免各用例重复请求)"""
    from src.utils.twitter_x_api.guest import TwitterGuest

    return await TwitterGuest.get_user_by_screen_name('X')


@requires_live
class TestTwitterGuestLive:
    """TwitterGuest 真实请求验证(访客 API)

    所有真实请求仅经由本类用例发起; 用例自足链式取样, 不依赖执行顺序。
    X 访客 API 限速较严, 每用例前 pacing 2s。

    当前上游行为记录:
    - UserByRestId 端点被 Cloudflare WAF 拦截: 稳定 403 且响应体为 Cloudflare HTML 拦截页, 与请求参数无关
      (twikit 参考实现的相同参数同样被拦); UserByScreenName/UserTweets/TweetResultByRestId/
      UserHighlightsTweets 均不受影响。客户端经 403 自动重试(重置访客会话并重新激活)后仍 403,
      最终抛出 WebSourceException。上游恢复后应将 test_get_user_by_id 改回正向查询断言
    - 访客首页为 X 新版精简 app shell(约 35KB, data-app-env="prod" 的 x-web 模块结构), 不含
      twitter-site-verification meta / loading-x-anim SVG / ondemand.s 脚本引用, ClientTransaction
      无法初始化(twikit 的 x_client_transaction 同样失效); 客户端按设计降级为不携带
      X-Client-Transaction-Id 请求, 其余 live 用例证明该降级下访客 API 可用。上游首页结构恢复后,
      test_client_transaction_availability_probe 自动转为验证初始化成功路径
    - X 对不存在用户返回 200 + data.user=null, 客户端转为 WebSourceException(400); 不存在推文转为
      WebSourceException(404)
    """

    @pytest.fixture(autouse=True)
    async def _pace(self) -> None:
        await asyncio.sleep(2)

    @pytest.fixture
    def twitter_guest(self) -> type['TwitterGuest']:
        from src.utils.twitter_x_api.guest import TwitterGuest
        return TwitterGuest

    @pytest.fixture
    def web_source_exception(self) -> type['WebSourceException']:
        from src.exception import WebSourceException
        return WebSourceException

    async def test_activate(self, twitter_guest: type['TwitterGuest']) -> None:
        token = await twitter_guest.activate()

        assert isinstance(token, str)
        assert token
        # 二次调用复用缓存 token(不重复 activate)
        assert await twitter_guest._ensure_guest_token() == token

    async def test_get_user_by_screen_name(self, live_user: 'TwitterUser') -> None:
        from src.utils.twitter_x_api.model import TwitterUser

        user = live_user
        assert isinstance(user, TwitterUser)
        assert user.screen_name == 'X'
        assert user.id.isdigit()
        assert user.is_blue_verified is True  # 官方账号为蓝标
        assert user.created_at_datetime is not None
        assert user.followers_count >= 0
        assert user.profile_image_url is not None

    async def test_get_user_by_id(
            self, twitter_guest: type['TwitterGuest'], web_source_exception: type['WebSourceException'],
            live_user: 'TwitterUser',
    ) -> None:
        # UserByRestId 当前被 WAF 拦截稳定 403, 客户端重试后仍 403 并抛出(见类 docstring 上游行为记录)
        with pytest.raises(web_source_exception) as exc_info:
            await twitter_guest.get_user_by_id(live_user.id)
        assert exc_info.value.status_code == 403

    async def test_client_transaction_availability_probe(self) -> None:
        # 首页 ClientTransaction 初始化探测: 初始化成功或降级为 None 均为合法结果, 不应抛异常
        # (当前首页 app shell 不含初始化要素, 按设计降级, 见类 docstring 上游行为记录)
        from src.utils.twitter_x_api.api_base import BaseTwitterAPI

        BaseTwitterAPI._reset_guest_state()
        transaction = await BaseTwitterAPI._ensure_client_transaction()
        assert transaction is None or transaction.is_initialized

    async def test_get_user_tweets_and_tweet_by_id(
            self, twitter_guest: type['TwitterGuest'], live_user: 'TwitterUser',
    ) -> None:
        from src.utils.twitter_x_api.model import TwitterTweet

        tweets = await twitter_guest.get_user_tweets(live_user.id, count=10)

        assert tweets, '官方账号 UserTweets 返回空列表'
        assert all(isinstance(x, TwitterTweet) for x in tweets)
        for tweet in tweets:
            assert tweet.id.isdigit()
            assert tweet.user is not None
            assert tweet.user.screen_name
            assert tweet.created_at_datetime is not None
            assert tweet.favorite_count >= 0
            assert tweet.retweet_count >= 0

        detail = await twitter_guest.get_tweet_by_id(tweets[0].id)
        assert detail.id == tweets[0].id
        assert detail.text == tweets[0].text  # 同一推文两次查询文本一致

    async def test_get_user_tweets_media_model(
            self, twitter_guest: type['TwitterGuest'], live_user: 'TwitterUser',
    ) -> None:
        tweets = await twitter_guest.get_user_tweets(live_user.id, count=20)
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

    async def test_get_user_highlights_tweets(
            self, twitter_guest: type['TwitterGuest'], live_user: 'TwitterUser',
    ) -> None:
        from src.utils.twitter_x_api.model import TwitterHighlightTweetsResult

        result = await twitter_guest.get_user_highlights_tweets(live_user.id)

        assert isinstance(result, TwitterHighlightTweetsResult)
        if not result.tweets:
            pytest.skip('官方账号无高光推文样本, 仅验证空结果形状')
        for tweet in result.tweets:
            assert tweet.id.isdigit()
            assert tweet.created_at_datetime is not None
        if result.next_cursor:
            next_page = await twitter_guest.get_user_highlights_tweets(live_user.id, cursor=result.next_cursor)
            assert isinstance(next_page.tweets, list)

    @pytest.mark.parametrize(
        ('query', 'expected_status'),
        [
            pytest.param('user', 400, id='user_not_found'),
            pytest.param('tweet', 404, id='tweet_not_found'),
        ],
    )
    async def test_not_found_raises(
            self, twitter_guest: type['TwitterGuest'], web_source_exception: type['WebSourceException'],
            query: str, expected_status: int,
    ) -> None:
        # 上游对不存在资源的行为(见类 docstring): 不存在用户转 WebSourceException(400), 不存在推文转 404
        coro = (
            twitter_guest.get_user_by_screen_name('omega_miya_no_such_user_9x7z')
            if query == 'user' else
            twitter_guest.get_tweet_by_id('1999999999999999999')
        )
        with pytest.raises(web_source_exception) as exc_info:
            await coro
        assert exc_info.value.status_code == expected_status

    async def test_download_resource(
            self, twitter_guest: type['TwitterGuest'], live_user: 'TwitterUser',
    ) -> None:
        if live_user.profile_image_url is None:
            pytest.skip('样本无头像 URL')
        resource = await twitter_guest.download_resource(str(live_user.profile_image_url))
        assert resource.path.exists()
        assert resource.path.stat().st_size > 0
        resource.path.unlink(missing_ok=True)
