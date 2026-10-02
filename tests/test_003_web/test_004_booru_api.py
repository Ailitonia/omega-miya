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
import importlib
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, ClassVar

import pytest

from tests.test_003_web.helpers import require_env_flag

if TYPE_CHECKING:
    from src.utils.booru_api import DanbooruAPI, GelbooruAPI, KonachanSafeAPI, YandereAPI
    from src.utils.booru_api.moebooru import BaseMoebooruAPI

requires_live = require_env_flag('OMEGA_BOORU_LIVE_TEST')
"""真实请求验证类门禁: 日常运行(含全量套件)一律跳过, 由用户手动设置 OMEGA_BOORU_LIVE_TEST=1 后发起"""


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


_CapturedAPIFactory = Callable[[Any], dict[str, Any]]
"""captured_api 夹具返回的打桩工厂类型(入参为罐装 payload, 返回调用参数捕获 dict)"""


@pytest.fixture
def captured_api(monkeypatch: pytest.MonkeyPatch) -> _CapturedAPIFactory:
    """捕获型 JSON API 打桩: 以罐装 payload 替换 _get_resource_as_json, 返回调用参数捕获 dict"""

    def _capture(payload: Any) -> dict[str, Any]:
        captured: dict[str, Any] = {}
        _capture_json_api(monkeypatch, payload, captured)
        return captured

    return _capture


def make_booru_api_cls(base_cls: type, root_url: str, cred_attrs: dict[str, Any] | None = None) -> type:
    """构造站点 API 基类的打桩局部子类(_get_root_url 指向测试根 URL, 凭据经类属性注入)"""

    class _TestAPI(base_cls):
        @classmethod
        def _get_root_url(cls, *args: Any, **kwargs: Any) -> str:
            return root_url

    for attr, value in (cred_attrs or {}).items():
        setattr(_TestAPI, attr, value)

    return _TestAPI


def make_booru_api(base_cls: type, root_url: str, cred_attrs: dict[str, Any] | None = None, **init_kwargs: Any) -> Any:
    """构造确定性的 booru 测试实例(局部子类, 凭据与 .env.test 隔离)"""
    return make_booru_api_cls(base_cls, root_url, cred_attrs)(**init_kwargs)


def _danbooru_post_payload(**overrides: Any) -> dict[str, Any]:
    """Danbooru Post 最小有效响应 payload(字段集经实测验证)"""
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
    # 匿名访问 /profile.json 返回幽灵用户(id=None, level=0)
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
    """Gelbooru Post 最小有效响应 payload(字段集经实测验证)"""
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
    """Moebooru Post 最小有效响应 payload(字段集经双站点实测验证)"""
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
# 离线单元测试共享基类(站点差异经类属性表达)
# ================================================================== #

@pytest.mark.usefixtures('_booru_api_ready')
class BooruAPIUnitTestBase:
    """booru API 离线单元测试共享基类(罐装响应, 零网络)

    不以 Test 开头, 不被 pytest 收集; 鉴权与实例凭据的站点差异经类属性表达, 各站点子类仅补充站点特有用例。
    """

    _API_BASE_MODULE: ClassVar[str]
    """站点 API 基类所在模块(延迟导入, src.* 依赖 NoneBot 初始化)"""
    _API_BASE_NAME: ClassVar[str]
    """站点 API 基类名"""
    _ROOT_URL: ClassVar[str]
    """打桩根 URL"""
    _CRED_ATTR_MAP: ClassVar[dict[str, str]]
    """凭据构造参数名 -> 类属性名 映射"""
    _AUTH_PROPERTY: ClassVar[str]
    """鉴权属性名(_auth_headers / _auth_params)"""
    _ANON_AUTH: ClassVar[Any]
    """匿名鉴权预期"""
    _CRED_KWARGS: ClassVar[dict[str, str]]
    """全凭据构造参数"""
    _FULL_AUTH: ClassVar[Any]
    """全凭据鉴权预期"""
    _CLASS_CRED_ATTRS: ClassVar[dict[str, str]]
    """类级默认凭据(类属性覆盖表)"""
    _CLASS_FULL_AUTH: ClassVar[Any]
    """类级默认凭据鉴权预期"""
    _INST_CRED_KWARGS: ClassVar[dict[str, str]]
    """实例凭据构造参数(遮蔽类级默认)"""
    _INST_FULL_AUTH: ClassVar[Any]
    """实例凭据鉴权预期"""

    @classmethod
    def _api_base_cls(cls) -> type:
        """延迟导入站点 API 基类"""
        return getattr(importlib.import_module(cls._API_BASE_MODULE), cls._API_BASE_NAME)

    @classmethod
    def _local_api_cls(cls, cred_attrs: dict[str, Any] | None = None) -> type:
        """构造站点基类的打桩局部子类(_get_root_url 指向测试根 URL, 凭据经类属性注入)"""
        return make_booru_api_cls(cls._api_base_cls(), cls._ROOT_URL, cred_attrs)

    @classmethod
    def _make_api(cls, **creds: Any) -> Any:
        """构造确定性测试实例(凭据键为站点构造参数名, 经类属性注入; 其余键透传构造)"""
        cred_attrs = {cls._CRED_ATTR_MAP[key]: value for key, value in creds.items() if key in cls._CRED_ATTR_MAP}
        init_kwargs = {key: value for key, value in creds.items() if key not in cls._CRED_ATTR_MAP}
        return make_booru_api(cls._api_base_cls(), cls._ROOT_URL, cred_attrs, **init_kwargs)

    @classmethod
    def _auth_of(cls, api: Any) -> Any:
        """读取实例鉴权属性(_auth_headers / _auth_params)"""
        return getattr(api, cls._AUTH_PROPERTY)

    # ------------------------------------------------------------------ #
    # 鉴权
    # ------------------------------------------------------------------ #

    def test_auth_anonymous(self) -> None:
        assert self._auth_of(self._make_api()) == self._ANON_AUTH

    def test_auth_full_credentials(self) -> None:
        assert self._auth_of(self._make_api(**self._CRED_KWARGS)) == self._FULL_AUTH

    # ------------------------------------------------------------------ #
    # 实例凭据与类级配置
    # ------------------------------------------------------------------ #

    def test_init_kwargs_shadow_without_class_pollution(self) -> None:
        # 实例凭据经 __init__ 写实例属性, 不污染类级配置
        api_cls = self._local_api_cls()

        authed = api_cls(**self._CRED_KWARGS)
        anon = api_cls()

        assert self._auth_of(authed) == self._FULL_AUTH
        assert self._auth_of(anon) == self._ANON_AUTH, '实例凭据不应污染同类的其他实例'
        for attr in self._CRED_ATTR_MAP.values():
            assert getattr(api_cls, attr) is None, '实例化不应修改类属性'

    def test_instance_credentials_override_class_default(self) -> None:
        api_cls = self._local_api_cls(self._CLASS_CRED_ATTRS)

        inst = api_cls(**self._INST_CRED_KWARGS)
        plain = api_cls()

        assert self._auth_of(inst) == self._INST_FULL_AUTH
        assert self._auth_of(plain) == self._CLASS_FULL_AUTH, '裸实例应使用类级配置默认'


class IndexedShowBooruAPIUnitTestBase(BooruAPIUnitTestBase):
    """post_show 经 index 查询迂回实现的站点(Gelbooru/Moebooru)共享离线用例

    不以 Test 开头, 不被 pytest 收集。
    """

    _EMPTY_INDEX_PAYLOAD: ClassVar[Any]
    """post_show 未命中时上游返回的空 index 响应 payload"""

    # ------------------------------------------------------------------ #
    # post_show 未命中
    # ------------------------------------------------------------------ #

    async def test_post_show_index_error(self, captured_api: _CapturedAPIFactory) -> None:
        # 未命中改抛项目异常体系 WebSourceException(404)
        from src.exception import WebSourceException

        captured_api(self._EMPTY_INDEX_PAYLOAD)

        with pytest.raises(WebSourceException) as exc_info:
            await self._make_api().post_show(1)
        assert exc_info.value.status_code == 404

    # ------------------------------------------------------------------ #
    # 停用端点 fast-fail(具体停用方法表由站点子类参数化)
    # ------------------------------------------------------------------ #

    async def _assert_fast_fail_deactivated(
            self, method: str, kwargs: dict[str, Any], captured: dict[str, Any],
    ) -> None:
        """停用端点核验: 客户端已禁用, 不发请求直接抛出 501 deactivated"""
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await getattr(self._make_api(), method)(**kwargs)

        assert exc_info.value.status_code == 501
        assert 'deactivated' in exc_info.value.message
        assert not captured, 'fast-fail 不应发起任何请求'


# ================================================================== #
# Danbooru 离线单元测试
# ================================================================== #

class TestDanbooruAPIUnit(BooruAPIUnitTestBase):
    """Danbooru API 离线单元测试(罐装响应, 零网络)"""

    _API_BASE_MODULE: ClassVar[str] = 'src.utils.booru_api.danbooru'
    _API_BASE_NAME: ClassVar[str] = 'BaseDanbooruAPI'
    _ROOT_URL: ClassVar[str] = 'https://danbooru.test.local'
    _CRED_ATTR_MAP: ClassVar[dict[str, str]] = {'username': '_username', 'api_key': '_api_key'}
    _AUTH_PROPERTY: ClassVar[str] = '_auth_headers'
    _ANON_AUTH: ClassVar[Any] = None
    _CRED_KWARGS: ClassVar[dict[str, str]] = {'username': 'u', 'api_key': 'k'}
    _FULL_AUTH: ClassVar[Any] = {'Authorization': f'Basic {base64.b64encode(b'u:k').decode()}'}
    _CLASS_CRED_ATTRS: ClassVar[dict[str, str]] = {'_username': 'class_u', '_api_key': 'class_k'}
    _CLASS_FULL_AUTH: ClassVar[Any] = {'Authorization': f'Basic {base64.b64encode(b'class_u:class_k').decode()}'}
    _INST_CRED_KWARGS: ClassVar[dict[str, str]] = {'username': 'inst_u', 'api_key': 'inst_k'}
    _INST_FULL_AUTH: ClassVar[Any] = {'Authorization': f'Basic {base64.b64encode(b'inst_u:inst_k').decode()}'}

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
        # 驱动(aiohttp/yarl)查询编码不接受 bool, 序列化为 true/false
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

    def test_auth_headers_partial_credentials(self) -> None:
        # 仅 username 缺 api_key 时不生成鉴权头
        assert self._make_api(username='u')._auth_headers is None

    def test_default_headers_anonymous(self) -> None:
        assert self._make_api()._get_default_headers() == {'User-Agent': 'omega-miya/2.0 (user omega-miya)'}

    def test_default_headers_with_username(self) -> None:
        headers = self._make_api(username='u')._get_default_headers()

        assert headers == {'User-Agent': 'omega-miya/2.0 (user u)'}

    async def test_get_resource_as_json_merges_headers(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api([])

        await self._make_api(username='u', api_key='k').get_resource_as_json(
            'https://danbooru.test.local/x.json', params={'a': 1}
        )

        assert captured['headers']['Authorization'] == f'Basic {base64.b64encode(b'u:k').decode()}'
        assert captured['headers']['User-Agent'] == 'omega-miya/2.0 (user u)'
        # 鉴权不经 URL 查询参数(仅请求头)
        assert captured['params'] == {'a': 1}

    async def test_get_resource_as_json_instance_ua(self, captured_api: _CapturedAPIFactory) -> None:
        # 实例凭据遮蔽类级配置时, UA 使用实例用户名
        captured = captured_api([])

        await self._local_api_cls(self._CLASS_CRED_ATTRS)(**self._INST_CRED_KWARGS).get_resource_as_json(
            'https://danbooru.test.local/x.json'
        )

        assert captured['headers']['User-Agent'] == 'omega-miya/2.0 (user inst_u)'

    # ------------------------------------------------------------------ #
    # 端点参数组装与响应解析
    # ------------------------------------------------------------------ #

    async def test_posts_index_params(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api([])

        await self._make_api().posts_index(
            tags='touhou', md5='abc', random=True, page='b99', limit=10, search_name='x'
        )

        assert captured['url'] == 'https://danbooru.test.local/posts.json'
        assert captured['params'] == {
            'page': 'b99', 'limit': 10, 'tags': 'touhou', 'md5': 'abc', 'random': 'true', 'search[name]': 'x'
        }

    async def test_posts_index_parse_list(self, captured_api: _CapturedAPIFactory) -> None:
        from src.utils.booru_api.models.danbooru import Post

        captured_api([_danbooru_post_payload(), _danbooru_post_payload(id=2)])

        posts = await self._make_api().posts_index(limit=2)

        assert [x.id for x in posts] == [1, 2]
        assert all(isinstance(x, Post) for x in posts)

    async def test_posts_index_md5_dict_wrapped(self, captured_api: _CapturedAPIFactory) -> None:
        # md5 精确匹配时上游返回单个 post 对象而非数组, 客户端包装为列表
        captured_api(_danbooru_post_payload())

        posts = await self._make_api().posts_index(md5='d41d8cd98f00b204e9800998ecf8427e')

        assert len(posts) == 1
        assert posts[0].id == 1

    async def test_comments_index_group_by_default(self, captured_api: _CapturedAPIFactory) -> None:
        # ApiComments 文档要求 group_by 必须为 comment, 否则上游返回 posts
        captured = captured_api([])

        await self._make_api().comments_index(limit=2)

        assert captured['params']['group_by'] == 'comment'

    async def test_comments_index_group_by_override(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api([])

        await self._make_api().comments_index(**{'group_by': 'post'})

        assert captured['params']['group_by'] == 'post'

    async def test_artist_show_url(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_danbooru_artist_payload())

        artist = await self._make_api().artist_show(1)

        assert captured['url'] == 'https://danbooru.test.local/artists/1.json'
        assert artist.id == 1

    async def test_wiki_show_title_url(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_DANBOORU_WIKI_PAYLOAD)

        await self._make_api().wiki_show('help:home')

        assert captured['url'] == 'https://danbooru.test.local/wiki_pages/help:home.json'

    async def test_post_show_artist_commentary_url(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_DANBOORU_ARTIST_COMMENTARY_PAYLOAD)

        await self._make_api().post_show_artist_commentary(1)

        assert captured['url'] == 'https://danbooru.test.local/posts/1/artist_commentary.json'

    async def test_dmail_show_key_param(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_DANBOORU_DMAIL_PAYLOAD)

        await self._make_api().dmail_show(1, key='secret')

        assert captured['params'] == {'key': 'secret'}

    async def test_dmail_show_without_key(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_DANBOORU_DMAIL_PAYLOAD)

        await self._make_api().dmail_show(1)

        assert captured['params'] is None

    async def test_explore_searches_parse(self, captured_api: _CapturedAPIFactory) -> None:
        # 响应形状: [[搜索词, 计数], ...] 二元组数组, 元素为 tuple[str, float]
        captured_api([['touhou', 1.5], ['original', 2.0]])

        results = await self._make_api().explore_searches_posts()

        assert results == [('touhou', 1.5), ('original', 2.0)]

    async def test_user_profile_ghost_parse(self, captured_api: _CapturedAPIFactory) -> None:
        captured_api(_DANBOORU_GHOST_USER_PAYLOAD)

        user = await self._make_api().user_profile()

        assert user.id is None
        assert user.level == 0

    async def test_dead_endpoint_error_passthrough(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 上游已移除端点(explore/curated, 返回 404)的错误透传
        from src.exception import WebSourceException

        _reject_json_api(monkeypatch, 404)

        with pytest.raises(WebSourceException) as exc_info:
            await self._make_api().explore_curated_posts()
        assert exc_info.value.status_code == 404

    async def test_invalid_payload_validation_error(self, captured_api: _CapturedAPIFactory) -> None:
        from pydantic import ValidationError

        captured_api([{'id': 1}])  # 缺必填字段的坏 payload

        with pytest.raises(ValidationError):
            await self._make_api().posts_index(limit=1)

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
        # 上游响应该字段可能为字符串 "None", 经预校验归一为 None
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
        # models 包根按站点前缀再导出全部模型
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

class TestGelbooruAPIUnit(IndexedShowBooruAPIUnitTestBase):
    """Gelbooru API 离线单元测试(罐装响应, 零网络)"""

    _API_BASE_MODULE: ClassVar[str] = 'src.utils.booru_api.gelbooru'
    _API_BASE_NAME: ClassVar[str] = 'BaseGelbooruAPI'
    _ROOT_URL: ClassVar[str] = 'https://gelbooru.test.local'
    _CRED_ATTR_MAP: ClassVar[dict[str, str]] = {'user_id': '_user_id', 'api_key': '_api_key'}
    _AUTH_PROPERTY: ClassVar[str] = '_auth_params'
    _ANON_AUTH: ClassVar[Any] = {}
    _CRED_KWARGS: ClassVar[dict[str, str]] = {'user_id': 'u', 'api_key': 'k'}
    _FULL_AUTH: ClassVar[Any] = {'api_key': 'k', 'user_id': 'u'}
    _CLASS_CRED_ATTRS: ClassVar[dict[str, str]] = {'_user_id': 'class_u', '_api_key': 'class_k'}
    _CLASS_FULL_AUTH: ClassVar[Any] = {'api_key': 'class_k', 'user_id': 'class_u'}
    _INST_CRED_KWARGS: ClassVar[dict[str, str]] = {'user_id': 'inst_u', 'api_key': 'inst_k'}
    _INST_FULL_AUTH: ClassVar[Any] = {'api_key': 'inst_k', 'user_id': 'inst_u'}
    _EMPTY_INDEX_PAYLOAD: ClassVar[Any] = _GELBOORU_EMPTY_INDEX_PAYLOAD

    # ------------------------------------------------------------------ #
    # 鉴权参数
    # ------------------------------------------------------------------ #

    async def test_auth_params_merged_without_mutation(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api({})
        caller_params = {'tags': 'touhou'}

        await self._make_api(user_id='u', api_key='k').get_resource_as_json(
            'https://gelbooru.test.local/index.php', params=caller_params
        )

        assert caller_params == {'tags': 'touhou'}, '调用方传入的 params 不应被原地修改'
        assert captured['params'] == {'tags': 'touhou', 'api_key': 'k', 'user_id': 'u'}

    # ------------------------------------------------------------------ #
    # 错误响应处理(dapi 返回 {"success": false, "message": ...} 形态)
    # ------------------------------------------------------------------ #

    async def test_error_response_bool_false(self, captured_api: _CapturedAPIFactory) -> None:
        from src.exception import WebSourceException

        captured_api({'success': False, 'message': 'search down'})

        with pytest.raises(WebSourceException) as exc_info:
            await self._make_api().posts_index(limit=1)
        assert 'search down' in exc_info.value.message
        assert exc_info.value.status_code == 200, '上游 success=false 时 HTTP 状态实际为 200, 不应虚构 5xx'

    async def test_error_response_str_false(self, captured_api: _CapturedAPIFactory) -> None:
        from src.exception import WebSourceException

        captured_api({'success': 'false', 'message': 'search down'})

        with pytest.raises(WebSourceException) as exc_info:
            await self._make_api().posts_index(limit=1)
        assert exc_info.value.status_code == 200, '上游 success=false 时 HTTP 状态实际为 200, 不应虚构 5xx'

    async def test_success_key_missing_no_raise(self, captured_api: _CapturedAPIFactory) -> None:
        captured_api({'data': 1})

        result = await self._make_api().get_resource_as_json('https://gelbooru.test.local/index.php')

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

    async def test_posts_index_params(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_gelbooru_posts_data_payload())

        await self._make_api().posts_index(limit=10, page=3, tags='touhou', cid=7, id_=2)

        assert captured['url'] == 'https://gelbooru.test.local/index.php'
        assert captured['params'] == {
            'page': 'dapi', 's': 'post', 'q': 'index', 'json': '1',
            'limit': '10', 'pid': '2', 'tags': 'touhou', 'cid': '7', 'id': '2',
        }

    async def test_posts_index_parse(self, captured_api: _CapturedAPIFactory) -> None:
        captured_api(_gelbooru_posts_data_payload())

        data = await self._make_api().posts_index(limit=1)

        assert data.attributes.count == 1
        assert data.post[0].id == 1
        assert data.post_ids == [1]

    async def test_posts_index_empty_key_omitted(self, captured_api: _CapturedAPIFactory) -> None:
        # 空结果时 dapi 省略数组键, 模型默认空列表
        captured_api(_GELBOORU_EMPTY_INDEX_PAYLOAD)

        data = await self._make_api().posts_index(tags='not_exist')

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

    async def test_post_show_first(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_gelbooru_posts_data_payload())

        post = await self._make_api().post_show(1)

        assert post.id == 1
        assert captured['params']['id'] == '1'

    async def test_tags_index_params(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_GELBOORU_EMPTY_INDEX_PAYLOAD)

        await self._make_api().tags_index(
            limit=10, id_=1, after_id=2, name='n', names='a b', name_pattern='%a%', order='DESC', orderby='count'
        )

        assert captured['params'] == {
            'page': 'dapi', 's': 'tag', 'q': 'index', 'json': '1',
            'limit': '10', 'id': '1', 'after_id': '2', 'name': 'n', 'names': 'a b',
            'name_pattern': '%a%', 'order': 'DESC', 'orderby': 'count',
        }

    async def test_users_index_params(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_GELBOORU_EMPTY_INDEX_PAYLOAD)

        await self._make_api().users_index(limit=5, page=2, name='n', name_pattern='%n%')

        assert captured['params'] == {
            'page': 'dapi', 's': 'user', 'q': 'index', 'json': '1',
            'limit': '5', 'pid': '1', 'name': 'n', 'name_pattern': '%n%',
        }

    # ------------------------------------------------------------------ #
    # 停用端点 fast-fail
    # ------------------------------------------------------------------ #

    # posts_index_deleted 对 JSON 客户端不可用(仅返回 XML);
    # comments_index 已被上游停用(返回纯文本 Disabled due to abuse.)
    @pytest.mark.parametrize(('method', 'kwargs'), [
        ('posts_index_deleted', {'last_id': 100}),
        ('comments_index', {'post_id': 9}),
    ])
    async def test_fast_fail_deactivated(
            self, method: str, kwargs: dict[str, Any], captured_api: _CapturedAPIFactory,
    ) -> None:
        await self._assert_fast_fail_deactivated(method, kwargs, captured_api({}))


# ================================================================== #
# Moebooru 离线单元测试
# ================================================================== #

class TestMoebooruAPIUnit(IndexedShowBooruAPIUnitTestBase):
    """Moebooru API 离线单元测试(罐装响应, 零网络)"""

    _API_BASE_MODULE: ClassVar[str] = 'src.utils.booru_api.moebooru'
    _API_BASE_NAME: ClassVar[str] = 'BaseMoebooruAPI'
    _ROOT_URL: ClassVar[str] = 'https://moebooru.test.local'
    _CRED_ATTR_MAP: ClassVar[dict[str, str]] = {'login_name': '_login', 'password_hash': '_password_hash'}
    _AUTH_PROPERTY: ClassVar[str] = '_auth_params'
    _ANON_AUTH: ClassVar[Any] = {}
    _CRED_KWARGS: ClassVar[dict[str, str]] = {'login_name': 'u', 'password_hash': 'h'}
    _FULL_AUTH: ClassVar[Any] = {'login': 'u', 'password_hash': 'h'}
    _CLASS_CRED_ATTRS: ClassVar[dict[str, str]] = {'_login': 'class_u', '_password_hash': 'class_h'}
    _CLASS_FULL_AUTH: ClassVar[Any] = {'login': 'class_u', 'password_hash': 'class_h'}
    _INST_CRED_KWARGS: ClassVar[dict[str, str]] = {'login_name': 'inst_u', 'password_hash': 'inst_h'}
    _INST_FULL_AUTH: ClassVar[Any] = {'login': 'inst_u', 'password_hash': 'inst_h'}
    _EMPTY_INDEX_PAYLOAD: ClassVar[Any] = []

    # ------------------------------------------------------------------ #
    # legacy_endpoint URL 选择
    # ------------------------------------------------------------------ #

    _ENDPOINT_URL_CASES: ClassVar[tuple[tuple[str, dict[str, Any], str], ...]] = (
        ('posts_index', {'limit': 1}, '/post.json'),
        ('tags_index', {'limit': 1}, '/tag.json'),
        ('wikis_index', {'limit': 1}, '/wiki.json'),
        ('note_post_show', {'post_id': 1}, '/note.json'),
        ('users_index', {}, '/user.json'),
        ('forums_index', {}, '/forum.json'),
        ('pools_index', {}, '/pool.json'),
    )

    @pytest.mark.parametrize('legacy', [False, True], ids=['current', 'legacy'])
    async def test_endpoint_urls(self, legacy: bool, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api([])
        api = self._make_api(legacy_endpoint=legacy)

        for method, kwargs, path in self._ENDPOINT_URL_CASES:
            await getattr(api, method)(**kwargs)
            expected_path = path.replace('.json', '/index.json') if legacy else path
            assert captured['url'] == f'{self._ROOT_URL}{expected_path}'

    # ------------------------------------------------------------------ #
    # 端点参数组装与响应解析
    # ------------------------------------------------------------------ #

    async def test_post_show_via_tags_id(self, captured_api: _CapturedAPIFactory) -> None:
        # 上游无 JSON show 路由, 客户端经 tags=id: 迂回实现(见 moebooru#144)
        captured = captured_api([_moebooru_post_payload()])

        post = await self._make_api().post_show(1)

        assert post.id == 1
        assert captured['params'] == {'tags': 'id:1'}

    async def test_comment_show_url(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_MOEBOORU_COMMENT_PAYLOAD)

        await self._make_api().comment_show(1)

        assert captured['url'] == 'https://moebooru.test.local/comment/show.json/1'

    # /wiki/show 的 json/xml 格式均返回 406, 客户端已禁用: 不发请求直接抛出
    @pytest.mark.parametrize(('method', 'kwargs'), [('wiki_show', {'title': 'touhou', 'version': 1})])
    async def test_fast_fail_deactivated(
            self, method: str, kwargs: dict[str, Any], captured_api: _CapturedAPIFactory,
    ) -> None:
        await self._assert_fast_fail_deactivated(method, kwargs, captured_api({}))

    async def test_pool_posts_show_params(self, captured_api: _CapturedAPIFactory) -> None:
        captured = captured_api(_MOEBOORU_POOL_PAYLOAD)

        await self._make_api().pool_posts_show(3, page=2)

        assert captured['url'] == 'https://moebooru.test.local/pool/show.json'
        assert captured['params'] == {'id': '3', 'page': '2'}

    def test_tags_related_parse(self) -> None:
        # 响应形状: {查询标签: [[相关标签名, 计数], ...]}, 上游计数为字符串, 归一为 int
        from src.utils.booru_api.models.moebooru import TagsRelated

        related = TagsRelated.model_validate({'touhou': [['touhou', '100'], ['cirno', '50']]})

        assert related.root['touhou'][0] == ('touhou', 100)
        assert related.root['touhou'][1] == ('cirno', 50)

    def test_favorited_users_split(self) -> None:
        # 上游为逗号分隔用户名字符串, 模型拆分为列表
        from src.utils.booru_api.models.moebooru import FavoritedUsers

        assert FavoritedUsers.model_validate({'favorited_users': 'a,b,c'}).favorited_users == ['a', 'b', 'c']
        assert FavoritedUsers.model_validate({'favorited_users': ''}).favorited_users == []

    def test_note_history_parse(self) -> None:
        # 响应中无 id/note_id 字段
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
    """凭据缺失时跳过用例(versions/dmails 端点匿名访问返回 403, uploads 匿名返回空列表)"""
    if not has_credentials:
        pytest.skip('未配置 Danbooru 凭据, 该端点匿名不可达(403 或空数据)')


async def _request_or_skip(request: Callable[[], Awaitable[Any]], desc: str) -> Any:
    """执行一次 API 请求, 上游 5xx(可能为数据库超时等瞬态错误)时重试一次; 仍不可用时转为 skip

    skip 原因中带上游状态码与错误响应内容(versions 端点对普通(Member)账户仍返回 403, 需更高账户等级;
    uploads 端点登录态曾返回 500)
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


async def _assert_index_show_round_trip(
        api: Any, index_method: str, show_method: str, index_kwargs: dict[str, Any],
) -> None:
    """链式往返核验: 经 index 取样首条记录, 再经 show 按 id 取回, 应得同一对象"""
    first = (await getattr(api, index_method)(**index_kwargs))[0]

    obj = await getattr(api, show_method)(first.id)

    assert obj.id == first.id


class BooruAPILiveTestBase:
    """booru 真实请求测试共享基类(不以 Test 开头, 不被 pytest 收集)"""

    @pytest.fixture(autouse=True)
    async def _pace(self) -> None:
        """booru 站点读限速(Danbooru 文档: 突发 10/s, 持续 ~1/s; Gelbooru/Moebooru 匿名亦有限速), 每个用例前 pacing"""
        await asyncio.sleep(1)


@requires_live
class TestDanbooruAPI(BooruAPILiveTestBase):
    """Danbooru 主站 API 真实请求验证(凭据经 .env.test 配置 danbooru_username/danbooru_api_key)

    上游行为记录(2026-09): versions/dmails 匿名 403(versions 对 Member 账户仍 403, 需更高等级);
    uploads 匿名 200 但空列表; /profile.json 匿名 200 幽灵用户(id=None, level=0);
    /explore/posts/curated.json 与 /artists/banned.json 上游已移除(404)
    """

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
        # md5 查询上游返回单个 post 对象而非数组, 客户端已兼容包装为列表
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
        # 上游主站已移除该端点(返回 404, wiki 路由表记载未更新), 客户端保留该方法仅为兼容其他 Danbooru 实例
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
        # 响应形状: [[搜索词, 计数], ...] 二元组数组, 元素为 tuple[str, float]
        results = await danbooru_api.explore_searches_posts()

        assert isinstance(results, list)
        assert all(isinstance(x, tuple) and isinstance(x[0], str) and isinstance(x[1], float) for x in results)

    async def test_explore_missed_searches_posts(self, danbooru_api: 'DanbooruAPI') -> None:
        # 响应形状: [[搜索词, 未命中计数], ...] 二元组数组, 元素为 tuple[str, float]
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
        # 上游主站已移除该端点(返回 404, wiki 路由表记载未更新), 客户端保留该方法仅为兼容其他 Danbooru 实例;
        # 主站等效能力: artists_index(search_is_banned=True)
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await danbooru_api.artists_index_banned(limit=2)
        assert exc_info.value.status_code == 404

    # ------------------------------------------------------------------ #
    # Artist Commentaries API
    # ------------------------------------------------------------------ #

    async def test_artist_commentaries_index(self, danbooru_api: 'DanbooruAPI') -> None:
        commentaries = await danbooru_api.artist_commentaries_index(limit=2)

        assert commentaries, 'artist_commentaries_index 返回空列表'

    # ------------------------------------------------------------------ #
    # Notes API
    # ------------------------------------------------------------------ #

    async def test_notes_index(self, danbooru_api: 'DanbooruAPI') -> None:
        notes = await danbooru_api.notes_index(limit=2)

        assert notes, 'notes_index 返回空列表'

    # ------------------------------------------------------------------ #
    # Pools API
    # ------------------------------------------------------------------ #

    async def test_pools_index(self, danbooru_api: 'DanbooruAPI') -> None:
        pools = await danbooru_api.pools_index(limit=2)

        assert pools, 'pools_index 返回空列表'
        assert all(x.category in ('series', 'collection') for x in pools)

    # ------------------------------------------------------------------ #
    # Wiki Pages API
    # ------------------------------------------------------------------ #

    async def test_wikis_index(self, danbooru_api: 'DanbooruAPI') -> None:
        wikis = await danbooru_api.wikis_index(limit=2)

        assert wikis, 'wikis_index 返回空列表'

    async def test_wiki_show_by_title(self, danbooru_api: 'DanbooruAPI') -> None:
        first = (await danbooru_api.wikis_index(limit=1))[0]

        wiki = await danbooru_api.wiki_show(first.title)

        assert wiki.title == first.title

    # ------------------------------------------------------------------ #
    # Versions API
    # 匿名访问返回 403; 普通(Member)账户登录后仍 403, 需更高账户等级, 无权时转为 skip
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize('index_method', [
        'artist_versions_index',
        'artist_commentary_versions_index',
        'note_versions_index',
        'pool_versions_index',
        'post_versions_index',
        'wiki_page_versions_index',
    ])
    async def test_versions_index(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool, index_method: str,
    ) -> None:
        _require_credentials(danbooru_has_credentials)

        versions = await _request_or_skip(
            lambda: getattr(danbooru_api, index_method)(limit=2), index_method.removesuffix('_index')
        )

        assert versions, f'{index_method} 返回空列表'

    @pytest.mark.parametrize(('index_method', 'show_method'), [
        ('artist_versions_index', 'artist_version_show'),
        ('artist_commentary_versions_index', 'artist_commentary_version_show'),
        ('note_versions_index', 'note_version_show'),
        ('wiki_page_versions_index', 'wiki_page_version_show'),
    ])
    async def test_version_show(
            self, danbooru_api: 'DanbooruAPI', danbooru_has_credentials: bool, index_method: str, show_method: str,
    ) -> None:
        _require_credentials(danbooru_has_credentials)
        first = (await _request_or_skip(
            lambda: getattr(danbooru_api, index_method)(limit=1), index_method.removesuffix('_index')
        ))[0]

        version = await getattr(danbooru_api, show_method)(first.id)

        assert version.id == first.id

    # ------------------------------------------------------------------ #
    # Comments API
    # ------------------------------------------------------------------ #

    async def test_comments_index(self, danbooru_api: 'DanbooruAPI') -> None:
        # 客户端已默认注入 group_by=comment, 否则上游返回 posts 而非 comments
        comments = await danbooru_api.comments_index(limit=2)

        assert comments, 'comments_index 返回空列表'

    # ------------------------------------------------------------------ #
    # Dmails API (匿名访问返回 403, 需登录态)
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

    async def test_forum_topics_index(self, danbooru_api: 'DanbooruAPI') -> None:
        topics = await danbooru_api.forum_topics_index(limit=2)

        assert topics, 'forum_topics_index 返回空列表'

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

    async def test_tag_aliases_index(self, danbooru_api: 'DanbooruAPI') -> None:
        aliases = await danbooru_api.tag_aliases_index(limit=2)

        assert aliases, 'tag_aliases_index 返回空列表'
        assert all(x.status in ('active', 'deleted', 'retired') for x in aliases)

    async def test_tag_implications_index(self, danbooru_api: 'DanbooruAPI') -> None:
        implications = await danbooru_api.tag_implications_index(limit=2)

        assert implications, 'tag_implications_index 返回空列表'
        assert all(x.status in ('active', 'deleted', 'retired') for x in implications)

    # ------------------------------------------------------------------ #
    # Uploads API (匿名访问返回 200 但为空列表; 登录态曾返回上游 500)
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
            # 匿名访问返回 200 幽灵用户
            assert user.id is None
            assert user.level == 0

    # ------------------------------------------------------------------ #
    # index -> show 链式往返(index 取样首条, show 按 id 取回应为同一对象)
    # ------------------------------------------------------------------ #

    @pytest.mark.parametrize(('index_method', 'show_method'), [
        ('posts_index', 'post_show'),
        ('artists_index', 'artist_show'),
        ('artist_commentaries_index', 'artist_commentary_show'),
        ('notes_index', 'note_show'),
        ('pools_index', 'pool_show'),
        ('wikis_index', 'wiki_show'),
        ('comments_index', 'comment_show'),
        ('forum_posts_index', 'forum_post_show'),
        ('forum_topics_index', 'forum_topic_show'),
        ('tags_index', 'tag_show'),
        ('tag_aliases_index', 'tag_alias_show'),
        ('tag_implications_index', 'tag_implication_show'),
        ('users_index', 'user_show'),
    ])
    async def test_index_show_round_trip(
            self, danbooru_api: 'DanbooruAPI', index_method: str, show_method: str,
    ) -> None:
        await _assert_index_show_round_trip(danbooru_api, index_method, show_method, {'limit': 1})


@pytest.fixture(scope='session')
async def gelbooru_api(nonebug_init: None) -> 'GelbooruAPI':
    """GelbooruAPI 实例(匿名, 或按 .env.test 已配置凭据), 以 nonebug_init 为 NoneBot 初始化屏障"""
    from src.utils.booru_api import GelbooruAPI

    return GelbooruAPI()


@requires_live
class TestGelbooruAPI(BooruAPILiveTestBase):
    """Gelbooru 主站 API 真实请求验证(匿名访问; 响应模型未见于 dapi 文档, 全部实测验证)

    空结果时 dapi 可能省略数组键(模型默认空列表)。
    """

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
        # 从真实 post 取标签作样本(tags_index 首项为最新标签, 可能是零引用边缘数据, name 查询曾未命中)
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
        # 从 users_index 链式取样(post.owner 可能是上传时的历史用户名, 用户改名后查询不命中)
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


class MoebooruAPITestBase(BooruAPILiveTestBase):
    """Moebooru API 共享测试逻辑(双站点对照: konachan.net / yande.re)

    不以 Test 开头, 不被 pytest 收集; 用例经子类的 moebooru_api fixture 分别打到两个站点,
    双站点结果对照可区分「单站点怪癖」与「模型通用问题」。注意 Moebooru 分级体系为 s/q/e。
    """

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

    # 上游无 JSON show 路由, post_show 经 tags=id: 迂回实现(见 moebooru#144); pool_posts_show 同形链式核验
    @pytest.mark.parametrize(('index_method', 'show_method', 'index_kwargs'), [
        ('posts_index', 'post_show', {'limit': 1}),
        ('pools_index', 'pool_posts_show', {}),
    ])
    async def test_index_show_round_trip(
            self, moebooru_api: 'BaseMoebooruAPI', index_method: str, show_method: str, index_kwargs: dict[str, Any],
    ) -> None:
        await _assert_index_show_round_trip(moebooru_api, index_method, show_method, index_kwargs)

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

        # 响应形状: {查询标签: [[相关标签名, 计数], ...]}
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

    # ------------------------------------------------------------------ #
    # Favorites API
    # ------------------------------------------------------------------ #

    async def test_favorite_list_users(self, moebooru_api: 'BaseMoebooruAPI') -> None:
        popular = await moebooru_api.posts_show_popular_recent()
        if not popular:
            pytest.skip('popular_recent 为空, 无法链式验证')

        favorited = await moebooru_api.favorite_list_users(popular[0].id)

        # 上游为逗号分隔用户名字符串, 模型拆分为列表
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
