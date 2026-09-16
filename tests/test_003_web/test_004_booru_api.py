"""
@Author         : Ailitonia
@Date           : 2026/9/16 19:41
@FileName       : test_004_booru_api
@Project        : omega-miya
@Description    : booru api 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import base64
import os
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, ClassVar

import pytest

if TYPE_CHECKING:
    from src.utils.booru_api import DanbooruAPI, GelbooruAPI, KonachanSafeAPI, YandereAPI
    from src.utils.booru_api.danbooru import BaseDanbooruAPI
    from src.utils.booru_api.gelbooru import BaseGelbooruAPI
    from src.utils.booru_api.moebooru import BaseMoebooruAPI

_BOORU_LIVE_ENV = 'OMEGA_BOORU_LIVE_TEST'
"""真实请求测试开关环境变量: 置 1 时启用(仅用户主动发起)"""

requires_live = pytest.mark.skipif(
    os.environ.get(_BOORU_LIVE_ENV) != '1',
    reason=f'真实请求测试默认禁用, 需用户主动发起: 设置环境变量 {_BOORU_LIVE_ENV}=1',
)


# ================================================================== #
# 离线单元测试公共设施(罐装响应, 零网络, 默认运行)
# ================================================================== #

@pytest.fixture(scope='session')
def _booru_api_ready(nonebug_init: None) -> None:
    """src.utils.booru_api 导入期依赖 NoneBot 初始化(get_plugin_config), 离线用例的统一屏障"""


def _capture_json_api(monkeypatch: pytest.MonkeyPatch, payload: Any, captured: dict[str, Any]) -> None:
    """将 BaseCommonAPI._get_resource_as_json 替换为捕获型假实现(零网络)

    :param payload: 假实现返回的罐装数据
    :param captured: 回写调用参数(cls/url/params/headers 等)的 dict
    """
    from src.utils.omega_common_api import BaseCommonAPI

    async def _fake(cls: type, url: str, params: Any = None, **kwargs: Any) -> Any:
        captured.update({'cls': cls, 'url': url, 'params': params, **kwargs})
        return payload

    monkeypatch.setattr(BaseCommonAPI, '_get_resource_as_json', classmethod(_fake))


def _reject_json_api(monkeypatch: pytest.MonkeyPatch, status_code: int) -> None:
    """将 BaseCommonAPI._get_resource_as_json 替换为抛 WebSourceException 的假实现"""
    from src.exception import WebSourceException
    from src.utils.omega_common_api import BaseCommonAPI

    async def _fake(cls: type, url: str, params: Any = None, **kwargs: Any) -> Any:
        raise WebSourceException(status_code, f'test error {status_code}')

    monkeypatch.setattr(BaseCommonAPI, '_get_resource_as_json', classmethod(_fake))


def _make_danbooru_api(*, username: str | None = None, api_key: str | None = None) -> 'BaseDanbooruAPI':
    """构造确定性的 Danbooru 测试实例(局部子类, 凭据与 .env.test 隔离)"""
    from src.utils.booru_api.danbooru import BaseDanbooruAPI

    class _TestDanbooruAPI(BaseDanbooruAPI):
        _username: ClassVar[str | None] = username
        _api_key: ClassVar[str | None] = api_key

        @classmethod
        def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
            return 'https://danbooru.test.local'

    return _TestDanbooruAPI()


def _make_gelbooru_api(*, user_id: str | None = None, api_key: str | None = None) -> 'BaseGelbooruAPI':
    """构造确定性的 Gelbooru 测试实例(局部子类, 凭据与 .env.test 隔离)"""
    from src.utils.booru_api.gelbooru import BaseGelbooruAPI

    class _TestGelbooruAPI(BaseGelbooruAPI):
        _user_id: ClassVar[str | None] = user_id
        _api_key: ClassVar[str | None] = api_key

        @classmethod
        def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
            return 'https://gelbooru.test.local'

    return _TestGelbooruAPI()


def _make_moebooru_api(
        *,
        login_name: str | None = None,
        password_hash: str | None = None,
        legacy_endpoint: bool = False,
) -> 'BaseMoebooruAPI':
    """构造确定性的 Moebooru 测试实例(局部子类, 凭据与 .env.test 隔离)"""
    from src.utils.booru_api.moebooru import BaseMoebooruAPI

    class _TestMoebooruAPI(BaseMoebooruAPI):
        _login: ClassVar[str | None] = login_name
        _password_hash: ClassVar[str | None] = password_hash

        @classmethod
        def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
            return 'https://moebooru.test.local'

    return _TestMoebooruAPI(legacy_endpoint=legacy_endpoint)


def _danbooru_post_payload(**overrides: Any) -> dict[str, Any]:
    """Danbooru Post 最小有效响应 payload(字段集经 2026-09 实测验证)"""
    payload: dict[str, Any] = {
        'id': 1, 'uploader_id': 1, 'approver_id': None,
        'is_banned': False, 'is_deleted': False, 'is_flagged': False, 'is_pending': False,
        'tag_string': 'touhou', 'tag_string_general': 'touhou', 'tag_string_artist': '',
        'tag_string_copyright': 'touhou', 'tag_string_character': '', 'tag_string_meta': '',
        'tag_count_general': 1, 'tag_count_artist': 0, 'tag_count_copyright': 1,
        'tag_count_character': 0, 'tag_count_meta': 0,
        'rating': 'g', 'parent_id': None, 'has_children': False, 'has_active_children': False,
        'has_visible_children': False, 'has_large': True, 'image_width': 800, 'image_height': 600,
        'source': 'https://example.com', 'md5': 'd41d8cd98f00b204e9800998ecf8427e',
        'file_url': 'https://danbooru.test.local/1.jpg', 'file_ext': 'jpg', 'file_size': 1000,
        'score': 0, 'up_score': 0, 'down_score': 0, 'fav_count': 0,
        'last_comment_bumped_at': None, 'last_noted_at': None,
        'media_asset': {
            'id': 1, 'file_ext': 'jpg', 'file_size': 1000, 'image_width': 800, 'image_height': 600,
            'status': 'active', 'is_public': True, 'pixel_hash': 'abc',
            'created_at': '2024-01-01T00:00:00.000Z', 'updated_at': '2024-01-01T00:00:00.000Z',
        },
        'created_at': '2024-01-01T00:00:00.000Z', 'updated_at': '2024-01-01T00:00:00.000Z',
    }
    payload.update(overrides)
    return payload


def _danbooru_artist_payload(**overrides: Any) -> dict[str, Any]:
    """Danbooru Artist 最小有效响应 payload"""
    payload: dict[str, Any] = {
        'id': 1, 'name': 'test_artist', 'group_name': '', 'other_names': [],
        'is_banned': False, 'is_deleted': False,
        'created_at': '2024-01-01T00:00:00.000Z', 'updated_at': '2024-01-01T00:00:00.000Z',
    }
    payload.update(overrides)
    return payload


_DANBOORU_GHOST_USER_PAYLOAD: dict[str, Any] = {
    # 2026-09 实测: 匿名访问 /profile.json 返回幽灵用户(id=None, level=0)
    'id': None, 'name': 'Ghost', 'level': 0, 'inviter_id': None,
    'post_update_count': 0, 'note_update_count': 0, 'post_upload_count': 0, 'is_banned': False,
}
"""Danbooru 匿名幽灵用户响应 payload"""

_DANBOORU_WIKI_PAYLOAD: dict[str, Any] = {
    'id': 1, 'title': 'help:home', 'body': '', 'other_names': [], 'is_deleted': False, 'is_locked': False,
    'created_at': '2024-01-01T00:00:00.000Z', 'updated_at': '2024-01-01T00:00:00.000Z',
}
"""Danbooru Wiki 最小有效响应 payload"""

_DANBOORU_ARTIST_COMMENTARY_PAYLOAD: dict[str, Any] = {
    'id': 1, 'post_id': 1, 'original_title': '', 'original_description': '',
    'translated_title': '', 'translated_description': '',
    'created_at': '2024-01-01T00:00:00.000Z', 'updated_at': '2024-01-01T00:00:00.000Z',
}
"""Danbooru ArtistCommentary 最小有效响应 payload"""

_DANBOORU_DMAIL_PAYLOAD: dict[str, Any] = {
    'id': 1, 'owner_id': 1, 'to_id': 2, 'from_id': 3, 'title': 't', 'body': 'b',
    'is_read': False, 'is_deleted': False, 'key': 'k',
    'created_at': '2024-01-01T00:00:00.000Z', 'updated_at': '2024-01-01T00:00:00.000Z',
}
"""Danbooru Dmail 最小有效响应 payload"""

_GELBOORU_EMPTY_INDEX_PAYLOAD: dict[str, Any] = {'@attributes': {'limit': 100, 'offset': 0, 'count': 0}}
"""Gelbooru 空结果包装响应 payload(省略数组键)"""

_MOEBOORU_COMMENT_PAYLOAD: dict[str, Any] = {'id': 1, 'post_id': 1, 'creator': 'u', 'body': 'b'}
"""Moebooru Comment 最小有效响应 payload"""

_MOEBOORU_POOL_PAYLOAD: dict[str, Any] = {'id': 3, 'name': 'p', 'user_id': 1, 'is_public': True, 'post_count': 0}
"""Moebooru Pool 最小有效响应 payload"""


def _gelbooru_post_payload(**overrides: Any) -> dict[str, Any]:
    """Gelbooru Post 最小有效响应 payload(字段集经 2026-09 实测验证)"""
    payload: dict[str, Any] = {
        'id': 1, 'owner': 'tester', 'creator_id': 1, 'title': '', 'tags': 'touhou',
        'rating': 'general', 'score': 0, 'change': 12345, 'directory': 'ab', 'image': 'ab.jpg',
        'md5': 'd41d8cd98f00b204e9800998ecf8427e', 'source': 'https://example.com',
        'width': 800, 'height': 600, 'preview_width': 150, 'preview_height': 112,
        'sample_height': 800, 'sample_width': 600, 'parent_id': 0, 'sample': 1,
        'has_children': False, 'has_comments': False, 'has_notes': False, 'status': 'active',
        'post_locked': 0, 'created_at': 'Thu Aug 13 22:00:00 +0000 2024',
    }
    payload.update(overrides)
    return payload


def _gelbooru_posts_data_payload(**overrides: Any) -> dict[str, Any]:
    """Gelbooru PostsData 包装响应 payload(@attributes + post 数组)"""
    payload: dict[str, Any] = {
        '@attributes': {'limit': 100, 'offset': 0, 'count': 1},
        'post': [_gelbooru_post_payload()],
    }
    payload.update(overrides)
    return payload


def _moebooru_post_payload(**overrides: Any) -> dict[str, Any]:
    """Moebooru Post 最小有效响应 payload(字段集经 2026-09 双站点实测验证)"""
    payload: dict[str, Any] = {
        'id': 1, 'author': 'tester', 'tags': 'touhou', 'rating': 's', 'change': 12345,
        'source': 'https://example.com', 'score': 0, 'md5': 'd41d8cd98f00b204e9800998ecf8427e',
        'width': 800, 'height': 600, 'preview_width': 150, 'preview_height': 112,
        'sample_height': 800, 'sample_width': 600, 'file_size': 1000, 'has_children': False,
        'status': 'active',
    }
    payload.update(overrides)
    return payload


# ================================================================== #
# Danbooru 离线单元测试
# ================================================================== #

@pytest.mark.usefixtures('_booru_api_ready')
class TestDanbooruAPIUnit:
    """Danbooru API 离线单元测试(罐装响应, 零网络)"""

    # ------------------------------------------------------------------ #
    # generate_common_search_params 边界
    # ------------------------------------------------------------------ #

    def test_search_params_empty(self) -> None:
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        assert BaseDanbooruAPI.generate_common_search_params() == {}

    def test_search_params_page_limit(self) -> None:
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        assert BaseDanbooruAPI.generate_common_search_params(page=2, limit=10) == {'page': 2, 'limit': 10}

    def test_search_params_cursor_page(self) -> None:
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        assert BaseDanbooruAPI.generate_common_search_params(page='b999') == {'page': 'b999'}

    def test_search_params_search_mapping(self) -> None:
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        result = BaseDanbooruAPI.generate_common_search_params(search_name='x', search_id=3)

        assert result == {'search[name]': 'x', 'search[id]': 3}

    def test_search_params_none_skipped(self) -> None:
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        assert BaseDanbooruAPI.generate_common_search_params(search_name=None, tags=None) == {}

    def test_search_params_bool_serialized(self) -> None:
        # 2026-09 实测修复: 驱动(aiohttp/yarl)查询编码不接受 bool, 序列化为 true/false
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        result = BaseDanbooruAPI.generate_common_search_params(random=True, search_safe=False)

        assert result == {'random': 'true', 'search[safe]': 'false'}

    def test_search_params_chained_key_passthrough(self) -> None:
        # posts 端点链式搜索键 search[post][FIELD] 不以 search_ 开头, 原样透传
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        result = BaseDanbooruAPI.generate_common_search_params(**{'search[post][rating]': 's'})

        assert result == {'search[post][rating]': 's'}

    # ------------------------------------------------------------------ #
    # 鉴权与请求头
    # ------------------------------------------------------------------ #

    def test_auth_headers_anonymous(self) -> None:
        assert _make_danbooru_api()._auth_headers is None

    def test_auth_headers_partial_credentials(self) -> None:
        # 仅 username 缺 api_key 时不生成鉴权头
        assert _make_danbooru_api(username='u')._auth_headers is None

    def test_auth_headers_basic(self) -> None:
        # 鉴权为 HTTP Basic Auth 头, 避免 api_key 随 URL 进入日志
        headers = _make_danbooru_api(username='u', api_key='k')._auth_headers

        assert headers == {'Authorization': f'Basic {base64.b64encode(b'u:k').decode()}'}

    def test_default_headers_anonymous(self) -> None:
        assert _make_danbooru_api()._get_default_headers() == {'User-Agent': 'omega-miya/2.0 (user omega-miya)'}

    def test_default_headers_with_username(self) -> None:
        headers = _make_danbooru_api(username='u')._get_default_headers()

        assert headers == {'User-Agent': 'omega-miya/2.0 (user u)'}

    async def test_get_resource_as_json_merges_headers(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, [], captured)

        await _make_danbooru_api(username='u', api_key='k').get_resource_as_json(
            'https://danbooru.test.local/x.json', params={'a': 1}
        )

        assert captured['headers']['Authorization'] == f'Basic {base64.b64encode(b'u:k').decode()}'
        assert captured['headers']['User-Agent'] == 'omega-miya/2.0 (user u)'
        # 鉴权不经 URL 查询参数(仅请求头)
        assert captured['params'] == {'a': 1}

    def test_init_kwargs_shadow_without_class_pollution(self) -> None:
        # 实例凭据经 __init__ 写实例属性, 不污染类级配置
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        class _TestAPI(BaseDanbooruAPI):
            @classmethod
            def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
                return 'https://danbooru.test.local'

        authed = _TestAPI(username='u', api_key='k')
        anon = _TestAPI()

        assert authed._auth_headers == {'Authorization': f'Basic {base64.b64encode(b'u:k').decode()}'}
        assert anon._auth_headers is None, '实例凭据不应污染同类的其他实例'
        assert _TestAPI._username is None, '实例化不应修改类属性'

    def test_instance_credentials_override_class_default(self) -> None:
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        class _TestAPI(BaseDanbooruAPI):
            _username = 'class_u'
            _api_key = 'class_k'

            @classmethod
            def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
                return 'https://danbooru.test.local'

        inst = _TestAPI(username='inst_u', api_key='inst_k')
        plain = _TestAPI()

        assert inst._auth_headers == {'Authorization': f'Basic {base64.b64encode(b'inst_u:inst_k').decode()}'}
        assert plain._auth_headers == {'Authorization': f'Basic {base64.b64encode(b'class_u:class_k').decode()}'}, \
            '裸实例应使用类级配置默认'

    async def test_get_resource_as_json_instance_ua(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 实例凭据遮蔽类级配置时, UA 使用实例用户名
        from src.utils.booru_api.danbooru import BaseDanbooruAPI

        class _TestAPI(BaseDanbooruAPI):
            _username = 'class_u'
            _api_key = 'class_k'

            @classmethod
            def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
                return 'https://danbooru.test.local'

        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, [], captured)

        await _TestAPI(username='inst_u', api_key='inst_k').get_resource_as_json('https://danbooru.test.local/x.json')

        assert captured['headers']['User-Agent'] == 'omega-miya/2.0 (user inst_u)'

    # ------------------------------------------------------------------ #
    # 端点参数组装与响应解析
    # ------------------------------------------------------------------ #

    async def test_posts_index_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, [], captured)

        await _make_danbooru_api().posts_index(
            tags='touhou', md5='abc', random=True, page='b99', limit=10, search_name='x'
        )

        assert captured['url'] == 'https://danbooru.test.local/posts.json'
        assert captured['params'] == {
            'page': 'b99', 'limit': 10, 'tags': 'touhou', 'md5': 'abc', 'random': 'true', 'search[name]': 'x'
        }

    async def test_posts_index_parse_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.booru_api.models.danbooru import Post

        _capture_json_api(monkeypatch, [_danbooru_post_payload(), _danbooru_post_payload(id=2)], {})

        posts = await _make_danbooru_api().posts_index(limit=2)

        assert [x.id for x in posts] == [1, 2]
        assert all(isinstance(x, Post) for x in posts)

    async def test_posts_index_md5_dict_wrapped(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # 2026-09 实测: md5 精确匹配时上游返回单个 post 对象而非数组, 客户端包装为列表
        _capture_json_api(monkeypatch, _danbooru_post_payload(), {})

        posts = await _make_danbooru_api().posts_index(md5='d41d8cd98f00b204e9800998ecf8427e')

        assert len(posts) == 1
        assert posts[0].id == 1

    async def test_comments_index_group_by_default(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # ApiComments 文档要求 group_by 必须为 comment, 否则上游返回 posts(2026-09 实测)
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, [], captured)

        await _make_danbooru_api().comments_index(limit=2)

        assert captured['params']['group_by'] == 'comment'

    async def test_comments_index_group_by_override(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, [], captured)

        await _make_danbooru_api().comments_index(**{'group_by': 'post'})

        assert captured['params']['group_by'] == 'post'

    async def test_artist_show_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _danbooru_artist_payload(), captured)

        artist = await _make_danbooru_api().artist_show(1)

        assert captured['url'] == 'https://danbooru.test.local/artists/1.json'
        assert artist.id == 1

    async def test_wiki_show_title_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _DANBOORU_WIKI_PAYLOAD, captured)

        await _make_danbooru_api().wiki_show('help:home')

        assert captured['url'] == 'https://danbooru.test.local/wiki_pages/help:home.json'

    async def test_post_show_artist_commentary_url(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _DANBOORU_ARTIST_COMMENTARY_PAYLOAD, captured)

        await _make_danbooru_api().post_show_artist_commentary(1)

        assert captured['url'] == 'https://danbooru.test.local/posts/1/artist_commentary.json'

    async def test_dmail_show_key_param(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _DANBOORU_DMAIL_PAYLOAD, captured)

        await _make_danbooru_api().dmail_show(1, key='secret')

        assert captured['params'] == {'key': 'secret'}

    async def test_dmail_show_without_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _DANBOORU_DMAIL_PAYLOAD, captured)

        await _make_danbooru_api().dmail_show(1)

        assert captured['params'] is None

    async def test_explore_searches_parse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 2026-09 实测形状: [[搜索词, 计数], ...] 二元组数组, 元素为 tuple[str, float]
        _capture_json_api(monkeypatch, [['touhou', 1.5], ['original', 2.0]], {})

        results = await _make_danbooru_api().explore_searches_posts()

        assert results == [('touhou', 1.5), ('original', 2.0)]

    async def test_user_profile_ghost_parse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _capture_json_api(monkeypatch, _DANBOORU_GHOST_USER_PAYLOAD, {})

        user = await _make_danbooru_api().user_profile()

        assert user.id is None
        assert user.level == 0

    async def test_dead_endpoint_error_passthrough(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # 上游已移除端点(explore/curated, 2026-09 实测 404)的错误透传
        from src.exception import WebSourceException

        _reject_json_api(monkeypatch, 404)

        with pytest.raises(WebSourceException) as exc_info:
            await _make_danbooru_api().explore_curated_posts()
        assert exc_info.value.status_code == 404

    async def test_invalid_payload_validation_error(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from pydantic import ValidationError

        _capture_json_api(monkeypatch, [{'id': 1}], {})  # 缺必填字段的坏 payload

        with pytest.raises(ValidationError):
            await _make_danbooru_api().posts_index(limit=1)

    def test_post_media_asset_variant_selectors(self) -> None:
        # variants 为判别联合, variant_type_* 属性按类型选取, 未命中返回 None
        from src.utils.booru_api.models.danbooru import (
            PostMediaAsset,
            PostVariantType180,
            PostVariantTypeSample,
        )

        payload: dict[str, Any] = {
            'id': 1, 'file_ext': 'jpg', 'file_size': 1000, 'image_width': 800, 'image_height': 600,
            'status': 'active', 'is_public': True, 'pixel_hash': 'abc',
            'created_at': '2024-01-01T00:00:00.000Z', 'updated_at': '2024-01-01T00:00:00.000Z',
            'variants': [
                {
                    'type': '180x180', 'url': 'https://example.com/180.jpg',
                    'width': 180, 'height': 180, 'file_ext': 'jpg',
                },
                {
                    'type': 'sample', 'url': 'https://example.com/sample.jpg',
                    'width': 400, 'height': 300, 'file_ext': 'jpg',
                },
            ],
        }

        asset = PostMediaAsset.model_validate(payload)

        assert isinstance(asset.variant_type_180, PostVariantType180)
        assert isinstance(asset.variant_type_sample, PostVariantTypeSample)
        assert asset.variant_type_360 is None
        assert asset.variant_type_720 is None
        assert asset.variant_type_full is None
        assert asset.variant_type_original is None

        none_variants = PostMediaAsset.model_validate({**payload, 'variants': None})
        assert none_variants.variant_type_180 is None

    def test_forum_topic_min_level_normalized(self) -> None:
        # Actual response may have the string "None", normalized to None via pre-validation
        from src.utils.booru_api.models.danbooru import ForumTopic

        payload: dict[str, Any] = {
            'id': 1, 'title': 't', 'category_id': 0, 'response_count': 1, 'min_level': 'None',
            'is_deleted': False, 'is_sticky': False, 'is_locked': False,
            'creator_id': 1, 'updater_id': 1,
            'created_at': '2024-01-01T00:00:00.000Z', 'updated_at': '2024-01-01T00:00:00.000Z',
        }

        assert ForumTopic.model_validate(payload).min_level is None
        assert ForumTopic.model_validate({**payload, 'min_level': 10}).min_level == 10

    def test_models_package_reexports(self) -> None:
        # models package root re-exports export by site prefix
        from src.utils.booru_api import models

        for name in (
                'GelbooruPost', 'GelbooruTag', 'GelbooruUser', 'GelbooruComment', 'GelbooruPostRating',
                'MoebooruNoteHistory', 'MoebooruTagsRelated', 'MoebooruFavoritedUsers',
        ):
            assert hasattr(models, name), f'models package should re-export {name}'
            assert name in models.__all__


# ================================================================== #
# Gelbooru 离线单元测试
# ================================================================== #

@pytest.mark.usefixtures('_booru_api_ready')
class TestGelbooruAPIUnit:
    """Gelbooru API 离线单元测试(罐装响应, 零网络)"""

    # ------------------------------------------------------------------ #
    # 鉴权参数
    # ------------------------------------------------------------------ #

    def test_auth_params_anonymous(self) -> None:
        assert _make_gelbooru_api()._auth_params == {}

    def test_auth_params_full(self) -> None:
        assert _make_gelbooru_api(user_id='u', api_key='k')._auth_params == {'api_key': 'k', 'user_id': 'u'}

    async def test_auth_params_merged_without_mutation(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, {}, captured)
        caller_params = {'tags': 'touhou'}

        await _make_gelbooru_api(user_id='u', api_key='k').get_resource_as_json(
            'https://gelbooru.test.local/index.php', params=caller_params
        )

        assert caller_params == {'tags': 'touhou'}, '调用方传入的 params 不应被原地修改'
        assert captured['params'] == {'tags': 'touhou', 'api_key': 'k', 'user_id': 'u'}

    def test_init_kwargs_shadow_without_class_pollution(self) -> None:
        # 实例凭据经 __init__ 写实例属性, 不污染类级配置
        from src.utils.booru_api.gelbooru import BaseGelbooruAPI

        class _TestAPI(BaseGelbooruAPI):
            @classmethod
            def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
                return 'https://gelbooru.test.local'

        authed = _TestAPI(user_id='u', api_key='k')
        anon = _TestAPI()

        assert authed._auth_params == {'api_key': 'k', 'user_id': 'u'}
        assert anon._auth_params == {}, '实例凭据不应污染同类的其他实例'
        assert _TestAPI._user_id is None, '实例化不应修改类属性'

    def test_instance_credentials_override_class_default(self) -> None:
        from src.utils.booru_api.gelbooru import BaseGelbooruAPI

        class _TestAPI(BaseGelbooruAPI):
            _user_id = 'class_u'
            _api_key = 'class_k'

            @classmethod
            def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
                return 'https://gelbooru.test.local'

        inst = _TestAPI(user_id='inst_u', api_key='inst_k')
        plain = _TestAPI()

        assert inst._auth_params == {'api_key': 'inst_k', 'user_id': 'inst_u'}
        assert plain._auth_params == {'api_key': 'class_k', 'user_id': 'class_u'}, '裸实例应使用类级配置默认'

    # ------------------------------------------------------------------ #
    # 错误响应处理(dapi 返回 {"success": false, "message": ...} 形态)
    # ------------------------------------------------------------------ #

    async def test_error_response_bool_false(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from src.exception import WebSourceException

        _capture_json_api(monkeypatch, {'success': False, 'message': 'search down'}, {})

        with pytest.raises(WebSourceException) as exc_info:
            await _make_gelbooru_api().posts_index(limit=1)
        assert 'search down' in exc_info.value.message
        assert exc_info.value.status_code == 200, '上游 success=false 时 HTTP 状态实际为 200, 不应虚构 5xx'

    async def test_error_response_str_false(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from src.exception import WebSourceException

        _capture_json_api(monkeypatch, {'success': 'false', 'message': 'search down'}, {})

        with pytest.raises(WebSourceException) as exc_info:
            await _make_gelbooru_api().posts_index(limit=1)
        assert exc_info.value.status_code == 200, '上游 success=false 时 HTTP 状态实际为 200, 不应虚构 5xx'

    async def test_success_key_missing_no_raise(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        _capture_json_api(monkeypatch, {'data': 1}, {})

        result = await _make_gelbooru_api().get_resource_as_json('https://gelbooru.test.local/index.php')

        assert result == {'data': 1}

    # ------------------------------------------------------------------ #
    # 分页转换边界
    # ------------------------------------------------------------------ #

    def test_convert_page_to_pid_boundary(self) -> None:
        from src.utils.booru_api.gelbooru import BaseGelbooruAPI

        assert BaseGelbooruAPI._convert_page_to_pid(1) == 0
        assert BaseGelbooruAPI._convert_page_to_pid(5) == 4
        assert BaseGelbooruAPI._convert_page_to_pid(0) == 0, 'page<=0 静默归 0'
        assert BaseGelbooruAPI._convert_page_to_pid(-3) == 0, 'page<=0 静默归 0'

    # ------------------------------------------------------------------ #
    # 端点参数组装与响应解析
    # ------------------------------------------------------------------ #

    async def test_posts_index_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _gelbooru_posts_data_payload(), captured)

        await _make_gelbooru_api().posts_index(limit=10, page=3, tags='touhou', cid=7, id_=2)

        assert captured['url'] == 'https://gelbooru.test.local/index.php'
        assert captured['params'] == {
            'page': 'dapi', 's': 'post', 'q': 'index', 'json': '1',
            'limit': '10', 'pid': '2', 'tags': 'touhou', 'cid': '7', 'id': '2',
        }

    async def test_posts_index_parse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _capture_json_api(monkeypatch, _gelbooru_posts_data_payload(), {})

        data = await _make_gelbooru_api().posts_index(limit=1)

        assert data.attributes.count == 1
        assert data.post[0].id == 1
        assert data.post_ids == [1]

    async def test_posts_index_empty_key_omitted(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # 空结果时 dapi 省略数组键(2026-09 实测), 模型默认空列表
        _capture_json_api(monkeypatch, {'@attributes': {'limit': 100, 'offset': 0, 'count': 0}}, {})

        data = await _make_gelbooru_api().posts_index(tags='not_exist')

        assert data.post == []
        assert data.attributes.count == 0

    def test_post_md5_hash_alias(self) -> None:
        # dapi 文档未记载响应字段, 不同实现存在 md5/hash 两种命名, 兼容解析
        from src.utils.booru_api.models.gelbooru import Post

        assert Post.model_validate(_gelbooru_post_payload()).md5 == 'd41d8cd98f00b204e9800998ecf8427e'

        payload = _gelbooru_post_payload()
        payload['hash'] = payload.pop('md5')
        assert Post.model_validate(payload).md5 == 'd41d8cd98f00b204e9800998ecf8427e'

    def test_post_nullable_fields_tolerated(self) -> None:
        # dapi 部分实现对无可值字段返回空串, 归一为 None; 0 为上游真实的"无"标记, 保留为 0
        from src.utils.booru_api.models.gelbooru import Post

        assert Post.model_validate(_gelbooru_post_payload()).parent_id == 0
        assert Post.model_validate(_gelbooru_post_payload()).creator_id == 1

        assert Post.model_validate(_gelbooru_post_payload(parent_id='')).parent_id is None
        assert Post.model_validate(_gelbooru_post_payload(parent_id=None)).parent_id is None
        assert Post.model_validate(_gelbooru_post_payload(creator_id='')).creator_id is None
        assert Post.model_validate(_gelbooru_post_payload(creator_id=None)).creator_id is None

    def test_user_username_name_alias(self) -> None:
        # dapi 文档未记载响应字段, 不同实现存在 username/name 两种命名, 兼容解析
        from src.utils.booru_api.models.gelbooru import User

        assert User.model_validate({'id': 1, 'username': 'u1', 'active': 0}).username == 'u1'
        assert User.model_validate({'id': 1, 'name': 'u2', 'active': 0}).username == 'u2'

    async def test_post_show_index_error(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # 未命中改抛项目异常体系 WebSourceException(404)
        from src.exception import WebSourceException

        _capture_json_api(monkeypatch, {'@attributes': {'limit': 100, 'offset': 0, 'count': 0}}, {})

        with pytest.raises(WebSourceException) as exc_info:
            await _make_gelbooru_api().post_show(1)
        assert exc_info.value.status_code == 404

    async def test_post_show_first(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _gelbooru_posts_data_payload(), captured)

        post = await _make_gelbooru_api().post_show(1)

        assert post.id == 1
        assert captured['params']['id'] == '1'

    async def test_tags_index_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _GELBOORU_EMPTY_INDEX_PAYLOAD, captured)

        await _make_gelbooru_api().tags_index(
            limit=10, id_=1, after_id=2, name='n', names='a b', name_pattern='%a%', order='DESC', orderby='count'
        )

        assert captured['params'] == {
            'page': 'dapi', 's': 'tag', 'q': 'index', 'json': '1',
            'limit': '10', 'id': '1', 'after_id': '2', 'name': 'n', 'names': 'a b',
            'name_pattern': '%a%', 'order': 'DESC', 'orderby': 'count',
        }

    async def test_users_index_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _GELBOORU_EMPTY_INDEX_PAYLOAD, captured)

        await _make_gelbooru_api().users_index(limit=5, page=2, name='n', name_pattern='%n%')

        assert captured['params'] == {
            'page': 'dapi', 's': 'user', 'q': 'index', 'json': '1',
            'limit': '5', 'pid': '1', 'name': 'n', 'name_pattern': '%n%',
        }

    async def test_posts_index_deleted_fast_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 端点对 JSON 客户端不可用(仅返回 XML, 2026-09 实测), 客户端已禁用: 不发请求直接抛出
        from src.exception import WebSourceException

        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, {}, captured)

        with pytest.raises(WebSourceException) as exc_info:
            await _make_gelbooru_api().posts_index_deleted(last_id=100)

        assert exc_info.value.status_code == 501
        assert 'deactivated' in exc_info.value.message
        assert not captured, 'fast-fail 不应发起任何请求'

    async def test_comments_index_fast_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 端点已被上游停用(返回纯文本 Disabled due to abuse., 2026-09 实测), 客户端已禁用: 不发请求直接抛出
        from src.exception import WebSourceException

        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, {}, captured)

        with pytest.raises(WebSourceException) as exc_info:
            await _make_gelbooru_api().comments_index(post_id=9)

        assert exc_info.value.status_code == 501
        assert 'deactivated' in exc_info.value.message
        assert not captured, 'fast-fail 不应发起任何请求'


# ================================================================== #
# Moebooru 离线单元测试
# ================================================================== #

@pytest.mark.usefixtures('_booru_api_ready')
class TestMoebooruAPIUnit:
    """Moebooru API 离线单元测试(罐装响应, 零网络)"""

    # ------------------------------------------------------------------ #
    # 鉴权参数
    # ------------------------------------------------------------------ #

    def test_auth_params_anonymous(self) -> None:
        assert _make_moebooru_api()._auth_params == {}

    def test_auth_params_full(self) -> None:
        assert _make_moebooru_api(login_name='u', password_hash='h')._auth_params == {
            'login': 'u', 'password_hash': 'h'
        }

    def test_init_kwargs_shadow_without_class_pollution(self) -> None:
        # 实例凭据经 __init__ 写实例属性, 不污染类级配置
        from src.utils.booru_api.moebooru import BaseMoebooruAPI

        class _TestAPI(BaseMoebooruAPI):
            @classmethod
            def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
                return 'https://moebooru.test.local'

        authed = _TestAPI(login_name='u', password_hash='h')
        anon = _TestAPI()

        assert authed._auth_params == {'login': 'u', 'password_hash': 'h'}
        assert anon._auth_params == {}, '实例凭据不应污染同类的其他实例'
        assert _TestAPI._login is None, '实例化不应修改类属性'

    def test_instance_credentials_override_class_default(self) -> None:
        from src.utils.booru_api.moebooru import BaseMoebooruAPI

        class _TestAPI(BaseMoebooruAPI):
            _login = 'class_u'
            _password_hash = 'class_h'

            @classmethod
            def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
                return 'https://moebooru.test.local'

        inst = _TestAPI(login_name='inst_u', password_hash='inst_h')
        plain = _TestAPI()

        assert inst._auth_params == {'login': 'inst_u', 'password_hash': 'inst_h'}
        assert plain._auth_params == {'login': 'class_u', 'password_hash': 'class_h'}, '裸实例应使用类级配置默认'

    # ------------------------------------------------------------------ #
    # legacy_endpoint URL 选择
    # ------------------------------------------------------------------ #

    async def test_current_endpoint_urls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, [], captured)
        api = _make_moebooru_api()

        await api.posts_index(limit=1)
        assert captured['url'] == 'https://moebooru.test.local/post.json'
        await api.tags_index(limit=1)
        assert captured['url'] == 'https://moebooru.test.local/tag.json'
        await api.wikis_index(limit=1)
        assert captured['url'] == 'https://moebooru.test.local/wiki.json'
        await api.note_post_show(1)
        assert captured['url'] == 'https://moebooru.test.local/note.json'
        await api.users_index()
        assert captured['url'] == 'https://moebooru.test.local/user.json'
        await api.forums_index()
        assert captured['url'] == 'https://moebooru.test.local/forum.json'
        await api.pools_index()
        assert captured['url'] == 'https://moebooru.test.local/pool.json'

    async def test_legacy_endpoint_urls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, [], captured)
        api = _make_moebooru_api(legacy_endpoint=True)

        await api.posts_index(limit=1)
        assert captured['url'] == 'https://moebooru.test.local/post/index.json'
        await api.tags_index(limit=1)
        assert captured['url'] == 'https://moebooru.test.local/tag/index.json'
        await api.wikis_index(limit=1)
        assert captured['url'] == 'https://moebooru.test.local/wiki/index.json'
        await api.note_post_show(1)
        assert captured['url'] == 'https://moebooru.test.local/note/index.json'
        await api.users_index()
        assert captured['url'] == 'https://moebooru.test.local/user/index.json'
        await api.forums_index()
        assert captured['url'] == 'https://moebooru.test.local/forum/index.json'
        await api.pools_index()
        assert captured['url'] == 'https://moebooru.test.local/pool/index.json'

    # ------------------------------------------------------------------ #
    # 端点参数组装与响应解析
    # ------------------------------------------------------------------ #

    async def test_post_show_via_tags_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 上游无 JSON show 路由, 客户端经 tags=id: 迂回实现(见 moebooru#144)
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, [_moebooru_post_payload()], captured)

        post = await _make_moebooru_api().post_show(1)

        assert post.id == 1
        assert captured['params'] == {'tags': 'id:1'}

    async def test_post_show_index_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 未命中改抛项目异常体系 WebSourceException(404)
        from src.exception import WebSourceException

        _capture_json_api(monkeypatch, [], {})

        with pytest.raises(WebSourceException) as exc_info:
            await _make_moebooru_api().post_show(1)
        assert exc_info.value.status_code == 404

    async def test_comment_show_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _MOEBOORU_COMMENT_PAYLOAD, captured)

        await _make_moebooru_api().comment_show(1)

        assert captured['url'] == 'https://moebooru.test.local/comment/show.json/1'

    async def test_wiki_show_fast_fail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # /wiki/show 的 json/xml 格式均返回 406(2026-09 双站点实测), 客户端已禁用: 不发请求直接抛出
        from src.exception import WebSourceException

        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, {}, captured)

        with pytest.raises(WebSourceException) as exc_info:
            await _make_moebooru_api().wiki_show('touhou', version=1)

        assert exc_info.value.status_code == 501
        assert 'deactivated' in exc_info.value.message
        assert not captured, 'fast-fail 不应发起任何请求'

    async def test_pool_posts_show_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, _MOEBOORU_POOL_PAYLOAD, captured)

        await _make_moebooru_api().pool_posts_show(3, page=2)

        assert captured['url'] == 'https://moebooru.test.local/pool/show.json'
        assert captured['params'] == {'id': '3', 'page': '2'}

    def test_tags_related_parse(self) -> None:
        # 2026-09 双站点实测形状: {查询标签: [[相关标签名, 计数], ...]}, 上游计数为字符串, 归一为 int
        from src.utils.booru_api.models.moebooru import TagsRelated

        related = TagsRelated.model_validate({'touhou': [['touhou', '100'], ['cirno', '50']]})

        assert related.root['touhou'][0] == ('touhou', 100)
        assert related.root['touhou'][1] == ('cirno', 50)

    def test_favorited_users_split(self) -> None:
        # 2026-09 双站点实测: 上游为逗号分隔用户名字符串, 模型拆分为列表
        from src.utils.booru_api.models.moebooru import FavoritedUsers

        assert FavoritedUsers.model_validate({'favorited_users': 'a,b,c'}).favorited_users == ['a', 'b', 'c']
        assert FavoritedUsers.model_validate({'favorited_users': ''}).favorited_users == []

    def test_note_history_parse(self) -> None:
        # 2026-09 双站点实测: 响应中无 id/note_id 字段
        from src.utils.booru_api.models.moebooru import NoteHistory

        history = NoteHistory.model_validate({
            'post_id': 1, 'x': 10, 'y': 20, 'width': 100, 'height': 50, 'is_active': True,
            'creator_id': 1, 'body': 'note', 'version': 2,
            'created_at': '2026-09-11T19:42:20.204Z', 'updated_at': '2026-09-11T19:42:20.204Z',
        })

        assert history.post_id == 1
        assert history.version == 2

    def test_artist_urls_split(self) -> None:
        # 响应中该字段可能为空格分隔字符串(Danbooru 1.x 兼容形态)或数组, 统一为列表
        from src.utils.booru_api.models.moebooru import Artist

        assert Artist.model_validate({'id': 1, 'name': 'a', 'urls': 'https://a.com https://b.com'}).urls == [
            'https://a.com', 'https://b.com'
        ]
        assert Artist.model_validate({'id': 1, 'name': 'a', 'urls': ['https://a.com']}).urls == ['https://a.com']

    # ------------------------------------------------------------------ #
    # 站点子类配置
    # ------------------------------------------------------------------ #

    def test_konachan_main_ua_and_root_url(self) -> None:
        # Konachan 主站有 Cloudflare 盾, 使用浏览器 UA 规避
        from src.utils.booru_api import KonachanAPI

        assert 'Firefox' in KonachanAPI._get_default_headers()['User-Agent']
        assert KonachanAPI._get_root_url() == 'https://konachan.com'

    def test_konachan_safe_ua(self) -> None:
        # Konachan 主站有 Cloudflare 盾, 使用浏览器 UA 规避
        from src.utils.booru_api import KonachanSafeAPI

        assert 'Firefox' in KonachanSafeAPI._get_default_headers()['User-Agent']

    def test_site_root_urls(self) -> None:
        from src.utils.booru_api import KonachanSafeAPI, YandereAPI

        assert KonachanSafeAPI._get_root_url() == 'https://konachan.net'
        assert YandereAPI._get_root_url() == 'https://yande.re'

    def test_yandere_default_ua(self) -> None:
        from src.utils.booru_api import YandereAPI

        assert YandereAPI._get_default_headers() == {'User-Agent': 'omega-miya/2.0 (user omega-miya)'}


# ================================================================== #
# 真实请求测试(默认全部跳过, 仅用户主动发起: 设置环境变量 OMEGA_BOORU_LIVE_TEST=1 后运行本文件)
# ================================================================== #

@pytest.fixture(scope='session')
async def danbooru_api(nonebug_init: None) -> 'DanbooruAPI':
    """DanbooruAPI 实例(凭据经 .env.test 配置), 以 nonebug_init 为 NoneBot 初始化屏障"""
    from src.utils.booru_api import DanbooruAPI

    return DanbooruAPI()


@pytest.fixture(scope='session')
def danbooru_has_credentials(nonebug_init: None) -> bool:
    """.env.test 是否配置了 Danbooru 凭据(匿名运行时相关用例跳过)"""
    from src.utils.booru_api.config import booru_api_config

    return booru_api_config.danbooru_username is not None and booru_api_config.danbooru_api_key is not None


def _require_credentials(has_credentials: bool) -> None:
    """凭据缺失时跳过用例(2026-09 实测: versions/dmails 端点匿名访问返回 403, uploads 匿名返回空列表)"""
    if not has_credentials:
        pytest.skip('未配置 Danbooru 凭据, 该端点匿名不可达(403 或空数据)')


async def _request_or_skip(request: Callable[[], Awaitable[Any]], desc: str) -> Any:
    """执行一次 API 请求, 上游 5xx(可能为数据库超时等瞬态错误)时重试一次; 仍不可用时转为 skip

    skip 原因中带上游状态码与错误响应内容(2026-09 实测: versions 端点对普通(Member)账户仍返回 403,
    需更高账户等级; uploads 端点登录态曾返回 500)
    """
    from src.exception import WebSourceException

    try:
        return await request()
    except WebSourceException as e:
        if e.status_code < 500:
            pytest.skip(f'{desc}: 当前账户等级无权访问 ({e.status_code}: {e.content})')

    await asyncio.sleep(2)
    try:
        return await request()
    except WebSourceException as e:
        pytest.skip(f'{desc}: 上游服务不可用 ({e.status_code}: {e.content})')


@requires_live
class TestDanbooruAPI:
    """Danbooru 主站 API 真实请求验证

    凭据经 .env.test 配置(danbooru_username/danbooru_api_key)。2026-09 实测:
    - versions/dmails 端点匿名访问返回 403, 需登录态; 其中 versions 端点对普通(Member)账户仍 403, 需更高账户等级
    - uploads 匿名访问返回 200 但为空列表
    - /profile.json 匿名访问返回 200 幽灵用户(id=None, level=0)
    - /explore/posts/curated.json 与 /artists/banned.json 上游主站已移除(404)
    """

    @pytest.fixture(autouse=True)
    async def _pace(self) -> None:
        """Danbooru 全站读限速(文档: 突发 10/s, 持续 ~1/s), 每个用例前 pacing"""
        await asyncio.sleep(1)

    # ------------------------------------------------------------------ #
    # Posts API
    # ------------------------------------------------------------------ #

    async def test_posts_index(self, danbooru_api: 'DanbooruAPI') -> None:
        from src.utils.booru_api.models.danbooru import Post

        posts = await danbooru_api.posts_index(limit=2)

        assert posts, 'posts_index 返回空列表'
        assert all(isinstance(x, Post) for x in posts)
        assert all(x.rating in ('g', 's', 'q', 'e', None) for x in posts)

    async def test_posts_index_tags(self, danbooru_api: 'DanbooruAPI') -> None:
        posts = await danbooru_api.posts_index(tags='rating:g', limit=2)

        assert posts, 'posts_index(tags=rating:g) 返回空列表'
        assert all(x.rating == 'g' for x in posts)

    async def test_posts_index_cursor_pagination(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.posts_index(limit=1))[0]

        prev_page = await danbooru_api.posts_index(page=f'b{first.id}', limit=2)

        assert prev_page, 'posts_index(page=b<id>) 返回空列表'
        assert all(x.id < first.id for x in prev_page), 'b<id> 游标分页应返回 id 更小的记录'

    async def test_posts_index_md5(self, danbooru_api: 'DanbooruAPI') -> None:
        # 2026-09 实测: md5 查询上游返回单个 post 对象而非数组, 客户端已兼容包装为列表
        sample = next((x for x in await danbooru_api.posts_index(limit=5) if x.md5), None)
        if sample is None:
            pytest.skip('前序样本均无可公开访问的 md5(Gold+ 限制)')

        result = await danbooru_api.posts_index(md5=sample.md5)

        assert len(result) == 1, 'md5 精确匹配应返回唯一记录'
        assert result[0].md5 == sample.md5

    async def test_posts_index_random(self, danbooru_api: 'DanbooruAPI') -> None:
        posts = await danbooru_api.posts_index(random=True, limit=2)

        assert posts, 'posts_index(random=True) 返回空列表'

    async def test_post_random(self, danbooru_api: 'DanbooruAPI') -> None:
        from src.utils.booru_api.models.danbooru import Post

        post = await danbooru_api.post_random()

        assert isinstance(post, Post)

    async def test_post_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.posts_index(limit=1))[0]

        post = await danbooru_api.post_show(first.id)

        assert post.id == first.id

    async def test_post_show_artist_commentary(self, danbooru_api: 'DanbooruAPI') -> None:
        commentaries = await danbooru_api.artist_commentaries_index(limit=1)
        if not commentaries:
            pytest.skip('artist_commentaries_index 为空, 无法链式验证')

        commentary = await danbooru_api.post_show_artist_commentary(commentaries[0].post_id)

        assert commentary.post_id == commentaries[0].post_id

    async def test_explore_popular_posts(self, danbooru_api: 'DanbooruAPI') -> None:
        from src.utils.booru_api.models.danbooru import Post

        posts = await danbooru_api.explore_popular_posts()

        assert isinstance(posts, list)
        assert all(isinstance(x, Post) for x in posts)

    async def test_explore_curated_posts(self, danbooru_api: 'DanbooruAPI') -> None:
        # 上游主站已移除该端点(2026-09 实测 404, wiki 路由表记载未更新), 客户端保留该方法仅为兼容其他 Danbooru 实例
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await danbooru_api.explore_curated_posts()
        assert exc_info.value.status_code == 404

    async def test_explore_viewed_posts(self, danbooru_api: 'DanbooruAPI') -> None:
        from src.utils.booru_api.models.danbooru import Post

        posts = await danbooru_api.explore_viewed_posts()

        assert isinstance(posts, list)
        assert all(isinstance(x, Post) for x in posts)

    async def test_explore_searches_posts(self, danbooru_api: 'DanbooruAPI') -> None:
        # 2026-09 实测响应形状: [[搜索词, 计数], ...] 二元组数组, 元素为 tuple[str, float]
        results = await danbooru_api.explore_searches_posts()

        assert isinstance(results, list)
        assert all(isinstance(x, tuple) and isinstance(x[0], str) and isinstance(x[1], float) for x in results)

    async def test_explore_missed_searches_posts(self, danbooru_api: 'DanbooruAPI') -> None:
        # 2026-09 实测响应形状: [[搜索词, 未命中计数], ...] 二元组数组, 元素为 tuple[str, float]
        results = await danbooru_api.explore_missed_searches_posts()

        assert isinstance(results, list)
        assert all(isinstance(x, tuple) and isinstance(x[0], str) and isinstance(x[1], float) for x in results)

    # ------------------------------------------------------------------ #
    # Artists API
    # ------------------------------------------------------------------ #

    async def test_artists_index(self, danbooru_api: 'DanbooruAPI') -> None:
        artists = await danbooru_api.artists_index(limit=2)

        assert artists, 'artists_index 返回空列表'

    async def test_artists_index_banned(self, danbooru_api: 'DanbooruAPI') -> None:
        # 上游主站已移除该端点(2026-09 实测 404, wiki 路由表记载未更新), 客户端保留该方法仅为兼容其他 Danbooru 实例;
        # 主站等效能力: artists_index(search_is_banned=True)
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await danbooru_api.artists_index_banned(limit=2)
        assert exc_info.value.status_code == 404

    async def test_artist_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.artists_index(limit=1))[0]

        artist = await danbooru_api.artist_show(first.id)

        assert artist.id == first.id

    # ------------------------------------------------------------------ #
    # Artist Commentaries API
    # ------------------------------------------------------------------ #

    async def test_artist_commentaries_index(self, danbooru_api: 'DanbooruAPI') -> None:
        commentaries = await danbooru_api.artist_commentaries_index(limit=2)

        assert commentaries, 'artist_commentaries_index 返回空列表'

    async def test_artist_commentary_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.artist_commentaries_index(limit=1))[0]

        commentary = await danbooru_api.artist_commentary_show(first.id)

        assert commentary.id == first.id

    # ------------------------------------------------------------------ #
    # Notes API
    # ------------------------------------------------------------------ #

    async def test_notes_index(self, danbooru_api: 'DanbooruAPI') -> None:
        notes = await danbooru_api.notes_index(limit=2)

        assert notes, 'notes_index 返回空列表'

    async def test_note_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.notes_index(limit=1))[0]

        note = await danbooru_api.note_show(first.id)

        assert note.id == first.id

    # ------------------------------------------------------------------ #
    # Pools API
    # ------------------------------------------------------------------ #

    async def test_pools_index(self, danbooru_api: 'DanbooruAPI') -> None:
        pools = await danbooru_api.pools_index(limit=2)

        assert pools, 'pools_index 返回空列表'
        assert all(x.category in ('series', 'collection') for x in pools)

    async def test_pool_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.pools_index(limit=1))[0]

        pool = await danbooru_api.pool_show(first.id)

        assert pool.id == first.id

    # ------------------------------------------------------------------ #
    # Wiki Pages API
    # ------------------------------------------------------------------ #

    async def test_wikis_index(self, danbooru_api: 'DanbooruAPI') -> None:
        wikis = await danbooru_api.wikis_index(limit=2)

        assert wikis, 'wikis_index 返回空列表'

    async def test_wiki_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.wikis_index(limit=1))[0]

        wiki = await danbooru_api.wiki_show(first.id)

        assert wiki.id == first.id

    async def test_wiki_show_by_title(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.wikis_index(limit=1))[0]

        wiki = await danbooru_api.wiki_show(first.title)

        assert wiki.title == first.title

    # ------------------------------------------------------------------ #
    # Versions API
    # 2026-09 实测: 匿名访问返回 403; 普通(Member)账户登录后仍 403, 需更高账户等级, 无权时转为 skip
    # ------------------------------------------------------------------ #

    async def test_artist_versions_index(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)

        versions = await _request_or_skip(lambda: danbooru_api.artist_versions_index(limit=2), 'artist_versions')

        assert versions, 'artist_versions_index 返回空列表'

    async def test_artist_version_show(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)
        first = (await _request_or_skip(lambda: danbooru_api.artist_versions_index(limit=1), 'artist_versions'))[0]

        version = await danbooru_api.artist_version_show(first.id)

        assert version.id == first.id

    async def test_artist_commentary_versions_index(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)

        versions = await _request_or_skip(
            lambda: danbooru_api.artist_commentary_versions_index(limit=2), 'artist_commentary_versions'
        )

        assert versions, 'artist_commentary_versions_index 返回空列表'

    async def test_artist_commentary_version_show(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)
        first = (await _request_or_skip(
            lambda: danbooru_api.artist_commentary_versions_index(limit=1), 'artist_commentary_versions'
        ))[0]

        version = await danbooru_api.artist_commentary_version_show(first.id)

        assert version.id == first.id

    async def test_note_versions_index(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)

        versions = await _request_or_skip(lambda: danbooru_api.note_versions_index(limit=2), 'note_versions')

        assert versions, 'note_versions_index 返回空列表'

    async def test_note_version_show(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)
        first = (await _request_or_skip(lambda: danbooru_api.note_versions_index(limit=1), 'note_versions'))[0]

        version = await danbooru_api.note_version_show(first.id)

        assert version.id == first.id

    async def test_pool_versions_index(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)

        versions = await _request_or_skip(lambda: danbooru_api.pool_versions_index(limit=2), 'pool_versions')

        assert versions, 'pool_versions_index 返回空列表'

    async def test_post_versions_index(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)

        versions = await _request_or_skip(lambda: danbooru_api.post_versions_index(limit=2), 'post_versions')

        assert versions, 'post_versions_index 返回空列表'

    async def test_wiki_page_versions_index(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)

        versions = await _request_or_skip(
            lambda: danbooru_api.wiki_page_versions_index(limit=2), 'wiki_page_versions'
        )

        assert versions, 'wiki_page_versions_index 返回空列表'

    async def test_wiki_page_version_show(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)
        first = (await _request_or_skip(
            lambda: danbooru_api.wiki_page_versions_index(limit=1), 'wiki_page_versions'
        ))[0]

        version = await danbooru_api.wiki_page_version_show(first.id)

        assert version.id == first.id

    # ------------------------------------------------------------------ #
    # Comments API
    # ------------------------------------------------------------------ #

    async def test_comments_index(self, danbooru_api: 'DanbooruAPI') -> None:
        # 2026-09 实测: 客户端已默认注入 group_by=comment, 否则上游返回 posts 而非 comments
        comments = await danbooru_api.comments_index(limit=2)

        assert comments, 'comments_index 返回空列表'

    async def test_comment_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.comments_index(limit=1))[0]

        comment = await danbooru_api.comment_show(first.id)

        assert comment.id == first.id

    # ------------------------------------------------------------------ #
    # Dmails API (匿名访问返回 403, 需登录态, 2026-09 实测)
    # ------------------------------------------------------------------ #

    async def test_dmails_index(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)

        dmails = await danbooru_api.dmails_index(limit=2)

        assert isinstance(dmails, list)

    async def test_dmail_show(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)
        dmails = await danbooru_api.dmails_index(limit=1)
        if not dmails:
            pytest.skip('当前账号无 dmail, 无法链式验证 dmail_show')

        dmail = await danbooru_api.dmail_show(dmails[0].id)
        assert dmail.id == dmails[0].id

        # 附带验证文档记载的 key 参数(凭 key 可查看他人 dmail)
        dmail_with_key = await danbooru_api.dmail_show(dmails[0].id, key=dmails[0].key)
        assert dmail_with_key.id == dmails[0].id

    # ------------------------------------------------------------------ #
    # Forum API
    # ------------------------------------------------------------------ #

    async def test_forum_posts_index(self, danbooru_api: 'DanbooruAPI') -> None:
        posts = await danbooru_api.forum_posts_index(limit=2)

        assert posts, 'forum_posts_index 返回空列表'

    async def test_forum_post_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.forum_posts_index(limit=1))[0]

        post = await danbooru_api.forum_post_show(first.id)

        assert post.id == first.id

    async def test_forum_topics_index(self, danbooru_api: 'DanbooruAPI') -> None:
        topics = await danbooru_api.forum_topics_index(limit=2)

        assert topics, 'forum_topics_index 返回空列表'

    async def test_forum_topic_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.forum_topics_index(limit=1))[0]

        topic = await danbooru_api.forum_topic_show(first.id)

        assert topic.id == first.id

    # ------------------------------------------------------------------ #
    # Post Appeals / Post Flags API
    # ------------------------------------------------------------------ #

    async def test_post_appeals_index(self, danbooru_api: 'DanbooruAPI') -> None:
        appeals = await danbooru_api.post_appeals_index(limit=2)

        assert isinstance(appeals, list)

    async def test_post_appeal_show(self, danbooru_api: 'DanbooruAPI') -> None:
        appeals = await danbooru_api.post_appeals_index(limit=1)
        if not appeals:
            pytest.skip('post_appeals_index 为空, 无法链式验证')

        appeal = await danbooru_api.post_appeal_show(appeals[0].id)

        assert appeal.id == appeals[0].id

    async def test_post_flags_index(self, danbooru_api: 'DanbooruAPI') -> None:
        flags = await danbooru_api.post_flags_index(limit=2)

        assert isinstance(flags, list)

    async def test_post_flag_show(self, danbooru_api: 'DanbooruAPI') -> None:
        flags = await danbooru_api.post_flags_index(limit=1)
        if not flags:
            pytest.skip('post_flags_index 为空, 无法链式验证')

        flag = await danbooru_api.post_flag_show(flags[0].id)

        assert flag.id == flags[0].id

    # ------------------------------------------------------------------ #
    # Tags API
    # ------------------------------------------------------------------ #

    async def test_tags_index(self, danbooru_api: 'DanbooruAPI') -> None:
        from src.utils.booru_api.models.danbooru import TagCategory

        tags = await danbooru_api.tags_index(limit=2)

        assert tags, 'tags_index 返回空列表'
        assert all(isinstance(x.category, TagCategory) for x in tags)

    async def test_tag_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.tags_index(limit=1))[0]

        tag = await danbooru_api.tag_show(first.id)

        assert tag.id == first.id

    async def test_tag_aliases_index(self, danbooru_api: 'DanbooruAPI') -> None:
        aliases = await danbooru_api.tag_aliases_index(limit=2)

        assert aliases, 'tag_aliases_index 返回空列表'
        assert all(x.status in ('active', 'deleted', 'retired') for x in aliases)

    async def test_tag_alias_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.tag_aliases_index(limit=1))[0]

        alias = await danbooru_api.tag_alias_show(first.id)

        assert alias.id == first.id

    async def test_tag_implications_index(self, danbooru_api: 'DanbooruAPI') -> None:
        implications = await danbooru_api.tag_implications_index(limit=2)

        assert implications, 'tag_implications_index 返回空列表'
        assert all(x.status in ('active', 'deleted', 'retired') for x in implications)

    async def test_tag_implication_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.tag_implications_index(limit=1))[0]

        implication = await danbooru_api.tag_implication_show(first.id)

        assert implication.id == first.id

    # ------------------------------------------------------------------ #
    # Uploads API (匿名访问返回 200 但为空列表; 登录态曾返回上游 500, 2026-09 实测)
    # ------------------------------------------------------------------ #

    async def test_uploads_index(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)

        uploads = await _request_or_skip(lambda: danbooru_api.uploads_index(limit=2), 'uploads')

        assert isinstance(uploads, list)

    async def test_upload_show(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        _require_credentials(danbooru_has_credentials)
        uploads = await _request_or_skip(lambda: danbooru_api.uploads_index(limit=1), 'uploads')
        if not uploads:
            pytest.skip('当前账号无上传记录, 无法链式验证 upload_show')

        upload = await danbooru_api.upload_show(uploads[0].id)

        assert upload.id == uploads[0].id

    # ------------------------------------------------------------------ #
    # Users API
    # ------------------------------------------------------------------ #

    async def test_users_index(self, danbooru_api: 'DanbooruAPI') -> None:
        users = await danbooru_api.users_index(limit=2)

        assert users, 'users_index 返回空列表'

    async def test_user_show(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.users_index(limit=1))[0]

        user = await danbooru_api.user_show(first.id)

        assert user.id == first.id

    async def test_user_profile(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool,
    ) -> None:
        from src.utils.booru_api.models.danbooru import User

        user = await danbooru_api.user_profile()

        assert isinstance(user, User)
        if danbooru_has_credentials:
            from src.utils.booru_api.config import booru_api_config

            assert user.id is not None, '登录态下 /profile.json 应返回真实用户'
            assert user.name == booru_api_config.danbooru_username
            assert user.level != 0
        else:
            # 匿名访问返回 200 幽灵用户 (2026-09 实测)
            assert user.id is None
            assert user.level == 0


@pytest.fixture(scope='session')
async def gelbooru_api(nonebug_init: None) -> 'GelbooruAPI':
    """GelbooruAPI 实例(匿名, 或按 .env.test 已配置凭据), 以 nonebug_init 为 NoneBot 初始化屏障"""
    from src.utils.booru_api import GelbooruAPI

    return GelbooruAPI()


@requires_live
class TestGelbooruAPI:
    """Gelbooru 主站 API 真实请求验证(匿名访问)

    响应模型未见于 dapi 文档记载, 全部为实测验证; 空结果时 dapi 可能省略数组键(模型默认空列表)。
    """

    @pytest.fixture(autouse=True)
    async def _pace(self) -> None:
        """Gelbooru 匿名限速(文档: 会不定期要求鉴权并限速), 每个用例前 pacing"""
        await asyncio.sleep(1)

    # ------------------------------------------------------------------ #
    # Posts API
    # ------------------------------------------------------------------ #

    async def test_posts_index(self, gelbooru_api: 'GelbooruAPI') -> None:
        data = await gelbooru_api.posts_index(limit=2)

        assert data.post, 'posts_index 返回空列表'
        assert all(isinstance(x.id, int) for x in data.post)
        assert isinstance(data.attributes.limit, int)
        assert isinstance(data.attributes.offset, int)
        assert isinstance(data.attributes.count, int)

    async def test_posts_index_tags(self, gelbooru_api: 'GelbooruAPI') -> None:
        from src.utils.booru_api.models.gelbooru import PostRating

        data = await gelbooru_api.posts_index(tags='rating:general', limit=2)

        assert data.post, 'posts_index(tags=rating:general) 返回空列表'
        assert all(x.rating is PostRating.general for x in data.post)

    async def test_posts_index_pagination(self, gelbooru_api: 'GelbooruAPI') -> None:
        # 验证 1 基页码 -> dapi 0 基 pid 的转换生效
        page_1 = await gelbooru_api.posts_index(limit=2, page=1)
        page_2 = await gelbooru_api.posts_index(limit=2, page=2)

        assert page_1.post, 'page=1 返回空列表'
        assert page_2.post, 'page=2 返回空列表'
        assert page_1.post[0].id != page_2.post[0].id

    async def test_posts_index_cid(self, gelbooru_api: 'GelbooruAPI') -> None:
        sample = (await gelbooru_api.posts_index(limit=1)).post[0]

        data = await gelbooru_api.posts_index(cid=sample.change)

        assert data.post, 'posts_index(cid=...) 返回空列表'

    async def test_post_show(self, gelbooru_api: 'GelbooruAPI') -> None:
        sample = (await gelbooru_api.posts_index(limit=1)).post[0]

        post = await gelbooru_api.post_show(sample.id)

        assert post.id == sample.id

    async def test_post_show_not_found(self, gelbooru_api: 'GelbooruAPI') -> None:
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await gelbooru_api.post_show(2 ** 40)
        assert exc_info.value.status_code == 404

    async def test_posts_index_empty_result(self, gelbooru_api: 'GelbooruAPI') -> None:
        # 覆盖空结果时 dapi 省略数组键的默认值路径
        data = await gelbooru_api.posts_index(tags='this_tag_should_not_exist_omega_miya_test', limit=2)

        assert data.post == []
        assert data.attributes.count == 0

    # ------------------------------------------------------------------ #
    # Tags API
    # ------------------------------------------------------------------ #

    async def test_tags_index(self, gelbooru_api: 'GelbooruAPI') -> None:
        data = await gelbooru_api.tags_index(limit=2)

        assert data.tag, 'tags_index 返回空列表'

    async def test_tags_index_name(self, gelbooru_api: 'GelbooruAPI') -> None:
        # 从真实 post 取标签作样本(tags_index 首项为最新标签, 可能是零引用边缘数据, 2026-09 实测 name 查询未命中)
        sample_name = (await gelbooru_api.posts_index(limit=1)).post[0].tags.split()[0]

        data = await gelbooru_api.tags_index(name=sample_name)

        assert any(x.name == sample_name for x in data.tag), 'name 精确查询未命中'

    async def test_tags_index_name_pattern(self, gelbooru_api: 'GelbooruAPI') -> None:
        sample_name = (await gelbooru_api.posts_index(limit=1)).post[0].tags.split()[0]

        data = await gelbooru_api.tags_index(name_pattern=sample_name, limit=100)

        assert any(x.name == sample_name for x in data.tag), 'name_pattern 查询未命中原样本'

    async def test_tags_index_orderby_count(self, gelbooru_api: 'GelbooruAPI') -> None:
        data = await gelbooru_api.tags_index(orderby='count', order='DESC', limit=10)

        counts = [x.count for x in data.tag]
        assert counts == sorted(counts, reverse=True), 'orderby=count&order=DESC 应按 count 降序'

    # ------------------------------------------------------------------ #
    # Users API
    # ------------------------------------------------------------------ #

    async def test_users_index(self, gelbooru_api: 'GelbooruAPI') -> None:
        data = await gelbooru_api.users_index(limit=2)

        assert data.user, 'users_index 返回空列表'

    async def test_users_index_name(self, gelbooru_api: 'GelbooruAPI') -> None:
        # 从 users_index 链式取样(post.owner 可能是上传时的历史用户名, 用户改名后查询不命中, 2026-09 实测)
        sample = (await gelbooru_api.users_index(limit=1)).user[0]

        data = await gelbooru_api.users_index(name=sample.username)

        assert any(x.username == sample.username for x in data.user), 'name 精确查询未命中'

    # ------------------------------------------------------------------ #
    # 媒体下载(覆盖非 JSON 路径)
    # ------------------------------------------------------------------ #

    async def test_post_preview_download(self, gelbooru_api: 'GelbooruAPI') -> None:
        sample = (await gelbooru_api.posts_index(limit=1)).post[0]
        if sample.preview_url is None:
            pytest.skip('样本无 preview_url')

        content = await gelbooru_api.get_resource_as_bytes(sample.preview_url)

        assert isinstance(content, bytes)
        assert len(content) > 0, '下载内容为空'


class MoebooruAPITestBase:
    """Moebooru API 共享测试逻辑(双站点对照: konachan.net / yande.re)

    不以 Test 开头, 不被 pytest 收集; 用例经子类的 moebooru_api fixture 分别打到两个站点,
    双站点结果对照可区分「单站点怪癖」与「模型通用问题」。注意 Moebooru 分级体系为 s/q/e。
    """

    @pytest.fixture(autouse=True)
    async def _pace(self) -> None:
        """Moebooru 站点匿名限速, 每个用例前 pacing"""
        await asyncio.sleep(1)

    # ------------------------------------------------------------------ #
    # Posts API
    # ------------------------------------------------------------------ #

    async def test_posts_index(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        posts = await moebooru_api.posts_index(limit=2)

        assert posts, 'posts_index 返回空列表'
        assert all(isinstance(x.id, int) for x in posts)
        assert all(x.rating in ('s', 'q', 'e') for x in posts), 'moebooru 分级体系为 s/q/e'

    async def test_posts_index_tags(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        posts = await moebooru_api.posts_index(tags='rating:s', limit=2)

        assert posts, 'posts_index(tags=rating:s) 返回空列表'
        assert all(x.rating == 's' for x in posts)

    async def test_posts_index_pagination(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        page_1 = await moebooru_api.posts_index(limit=2, page=1)
        page_2 = await moebooru_api.posts_index(limit=2, page=2)

        assert page_1, 'page=1 返回空列表'
        assert page_2, 'page=2 返回空列表'
        assert page_1[0].id != page_2[0].id

    async def test_posts_show_popular_by_day(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        posts = await moebooru_api.posts_show_popular_by_day()

        assert isinstance(posts, list)

    async def test_posts_show_popular_by_week(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        posts = await moebooru_api.posts_show_popular_by_week()

        assert isinstance(posts, list)

    async def test_posts_show_popular_by_month(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        posts = await moebooru_api.posts_show_popular_by_month()

        assert isinstance(posts, list)

    async def test_posts_show_popular_recent(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        posts = await moebooru_api.posts_show_popular_recent()

        assert isinstance(posts, list)

    async def test_post_show(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        # 上游无 JSON show 路由, 客户端经 tags=id: 迂回实现(见 moebooru#144)
        sample = (await moebooru_api.posts_index(limit=1))[0]

        post = await moebooru_api.post_show(sample.id)

        assert post.id == sample.id

    async def test_post_show_not_found(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await moebooru_api.post_show(2 ** 40)
        assert exc_info.value.status_code == 404

    async def test_post_show_similar(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        sample = (await moebooru_api.posts_index(limit=1))[0]

        similar = await moebooru_api.post_show_similar(sample.id)

        assert isinstance(similar.success, bool)
        assert isinstance(similar.posts, list)

    # ------------------------------------------------------------------ #
    # Tags API
    # ------------------------------------------------------------------ #

    async def test_tags_index(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        tags = await moebooru_api.tags_index(limit=2)

        assert tags, 'tags_index 返回空列表'

    async def test_tags_index_order_count(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        tags = await moebooru_api.tags_index(order='count', limit=10)

        counts = [x.count for x in tags]
        assert counts == sorted(counts, reverse=True), 'order=count 应按 count 降序'

    async def test_tags_index_name(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        # 样本取自真实 post 的标签(保证存在且可搜索)
        sample_name = (await moebooru_api.posts_index(limit=1))[0].tags.split()[0]

        tags = await moebooru_api.tags_index(name=sample_name)

        assert any(x.name == sample_name for x in tags), 'name 精确查询未命中'

    async def test_tags_related(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        sample_name = (await moebooru_api.posts_index(limit=1))[0].tags.split()[0]

        related = await moebooru_api.tags_related(sample_name)

        # 2026-09 双站点实测形状: {查询标签: [[相关标签名, 计数], ...]}
        assert sample_name in related.root, '响应缺少查询标签键'
        assert related.root[sample_name], '相关标签列表为空'
        assert all(isinstance(name, str) and isinstance(count, int) for name, count in related.root[sample_name])

    # ------------------------------------------------------------------ #
    # Artists API
    # ------------------------------------------------------------------ #

    async def test_artists_index(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        artists = await moebooru_api.artists_index()

        assert artists, 'artists_index 返回空列表'

    # ------------------------------------------------------------------ #
    # Comments API
    # ------------------------------------------------------------------ #

    async def test_comment_show(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        # 上游 1.13 已移除 comment/index, 无 index 可链式取样; 探针 id=1, 不存在即 skip 留证
        comment = await _request_or_skip(lambda: moebooru_api.comment_show(1), 'comment_show#1')

        assert comment.id == 1

    # ------------------------------------------------------------------ #
    # Wiki API
    # ------------------------------------------------------------------ #

    async def test_wikis_index(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        wikis = await moebooru_api.wikis_index(limit=2)

        assert wikis, 'wikis_index 返回空列表'

    # ------------------------------------------------------------------ #
    # Notes API
    # ------------------------------------------------------------------ #

    async def test_notes_history(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        from src.utils.booru_api.models.moebooru import NoteHistory

        history = await moebooru_api.notes_history(limit=5)

        assert history, 'notes_history 返回空列表'
        assert all(isinstance(x, NoteHistory) for x in history)

    async def test_note_post_show(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        history = await moebooru_api.notes_history(limit=5)
        if not history:
            pytest.skip('notes_history 为空, 无法链式验证')
        post_id = history[0].post_id

        notes = await moebooru_api.note_post_show(post_id)

        assert notes, 'note_post_show 返回空列表'
        assert all(x.post_id == post_id for x in notes)

    async def test_notes_search(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        notes = await moebooru_api.notes_search('the')

        assert isinstance(notes, list)

    # ------------------------------------------------------------------ #
    # Users API
    # ------------------------------------------------------------------ #

    async def test_users_index(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        users = await moebooru_api.users_index()

        assert users, 'users_index 返回空列表'

    async def test_users_index_name(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        # 样本自 users_index 自取(避免改名后历史用户名不命中)
        sample = (await moebooru_api.users_index())[0]

        users = await moebooru_api.users_index(name=sample.name)

        assert any(x.name == sample.name for x in users), 'name 精确查询未命中'

    # ------------------------------------------------------------------ #
    # Forum API
    # ------------------------------------------------------------------ #

    async def test_forums_index(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        forums = await moebooru_api.forums_index()

        assert isinstance(forums, list)

    # ------------------------------------------------------------------ #
    # Pools API
    # ------------------------------------------------------------------ #

    async def test_pools_index(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        pools = await moebooru_api.pools_index()

        assert pools, 'pools_index 返回空列表'

    async def test_pool_posts_show(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        sample = (await moebooru_api.pools_index())[0]

        pool = await moebooru_api.pool_posts_show(sample.id)

        assert pool.id == sample.id

    # ------------------------------------------------------------------ #
    # Favorites API
    # ------------------------------------------------------------------ #

    async def test_favorite_list_users(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        popular = await moebooru_api.posts_show_popular_recent()
        if not popular:
            pytest.skip('popular_recent 为空, 无法链式验证')

        favorited = await moebooru_api.favorite_list_users(popular[0].id)

        # 2026-09 双站点实测: 上游为逗号分隔用户名字符串, 模型拆分为列表
        assert isinstance(favorited.favorited_users, list)
        assert all(isinstance(x, str) for x in favorited.favorited_users)


@requires_live
class TestKonachanSafeAPI(MoebooruAPITestBase):
    """https://konachan.net (Konachan 全年龄镜像站) 真实请求验证"""

    @pytest.fixture
    def moebooru_api(self, nonebug_init: None) -> 'KonachanSafeAPI':
        from src.utils.booru_api import KonachanSafeAPI

        return KonachanSafeAPI()


@requires_live
class TestYandereAPI(MoebooruAPITestBase):
    """https://yande.re 真实请求验证"""

    @pytest.fixture
    def moebooru_api(self, nonebug_init: None) -> 'YandereAPI':
        from src.utils.booru_api import YandereAPI

        return YandereAPI()
