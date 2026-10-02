"""
@Author         : Ailitonia
@Date           : 2026/9/12 22:50
@FileName       : test_002_omega_common_api
@Project        : omega-miya
@Description    : omega_common_api(BaseCommonAPI)单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from multidict import CIMultiDict
from nonebot.drivers import Cookies

from tests.test_003_web.helpers import (
    _DOWNLOAD_PAYLOAD,
    _LINES_EXPECTED,
    _STREAM_PAYLOAD,
    capture_driver_request,
    capture_driver_stream_request,
    line_chunks_stream,
    make_cookie_jar,
    make_response,
    make_test_folder,
    new_request_token,
)

if TYPE_CHECKING:
    from src.resource import AnyResource
    from src.utils.omega_common_api import BaseCommonAPI


@pytest.fixture(scope='module')
def api_impl() -> 'type[BaseCommonAPI]':
    """BaseCommonAPI 具体实现(默认 headers 固定, 默认 cookies 为空)"""
    from src.utils.omega_common_api import BaseCommonAPI

    class _CommonAPIImpl(BaseCommonAPI):
        @classmethod
        def _get_root_url(cls, *args, **kwargs) -> str:
            return ''

        @classmethod
        def _get_default_headers(cls) -> dict[str, str]:
            return {'x-test-api': 'omega'}

        @classmethod
        def _get_default_cookies(cls) -> None:
            return None

    return _CommonAPIImpl


@pytest.fixture
def save_folder(tmp_path: Path) -> 'AnyResource':
    """下载保存目录(临时文件夹资源)"""
    return make_test_folder(tmp_path)


class TestModuleContract:
    """模块导出契约测试"""

    def test_package_all_exports(self):
        import src.utils.omega_common_api

        assert src.utils.omega_common_api.__all__ == ['BaseCommonAPI']

    def test_api_base_module_all_exports(self):
        import src.utils.omega_common_api.api_base

        assert src.utils.omega_common_api.api_base.__all__ == ['BaseCommonAPI']

    def test_types_module_all_exports(self):
        import src.utils.omega_common_api.types

        assert src.utils.omega_common_api.types.__all__ == [
            'ContentTypes',
            'Cookies',
            'CookieTypes',
            'DataTypes',
            'FilesTypes',
            'HeaderTypes',
            'HTTPClientSession',
            'QueryTypes',
            'Request',
            'Response',
            'Timeout',
            'TimeoutTypes',
            'WebSocket',
        ]


class TestAbstractBase:
    """抽象基类约束测试"""

    def test_base_class_not_instantiable(self):
        from src.utils.omega_common_api import BaseCommonAPI

        with pytest.raises(TypeError):
            BaseCommonAPI()

    def test_incomplete_subclass_not_instantiable(self):
        from src.utils.omega_common_api import BaseCommonAPI

        class _Incomplete(BaseCommonAPI):
            @classmethod
            def _get_root_url(cls, *args, **kwargs) -> str:
                return ''

        with pytest.raises(TypeError):
            _Incomplete()

    def test_abstract_methods_raise_not_implemented(self):
        from src.utils.omega_common_api import BaseCommonAPI

        with pytest.raises(NotImplementedError):
            BaseCommonAPI._get_root_url()
        with pytest.raises(NotImplementedError):
            BaseCommonAPI._get_default_headers()
        with pytest.raises(NotImplementedError):
            BaseCommonAPI._get_default_cookies()

    def test_repr_is_class_name(self, api_impl: 'type[BaseCommonAPI]'):
        assert repr(api_impl()) == '_CommonAPIImpl'


class TestExtraSetCookiesFromResponse:
    """响应头 set-cookie 解析测试"""

    @pytest.mark.parametrize(
        ('headers', 'expected'),
        [
            pytest.param({'set-cookie': 'a=1; Path=/; HttpOnly'}, {'a': '1'}, id='single_cookie_with_attributes'),
            pytest.param(
                CIMultiDict([('set-cookie', 'a=1; Path=/'), ('Set-Cookie', 'b=2; Path=/')]),
                {'a': '1', 'b': '2'},
                id='multiple_set_cookie_headers',
            ),
            pytest.param({'set-cookie': 'token=v1=v2; Path=/'}, {'token': 'v1=v2'}, id='cookie_value_with_equals'),
            pytest.param({'set-cookie': 'invalid; Path=/'}, {}, id='cookie_without_equals_skipped'),
            pytest.param({'set-cookie': 'a=; Path=/'}, {'a': ''}, id='cookie_empty_value_kept'),
            pytest.param(
                CIMultiDict([('set-cookie', 'a=1; Path=/'), ('set-cookie2', 'b=2; Path=/')]),
                {'a': '1'},
                id='similar_header_not_matched',
            ),
            pytest.param(None, {}, id='no_cookie_header'),
        ],
    )
    def test_extra_set_cookies_from_response(
            self, headers: Any, expected: dict[str, str], api_impl: 'type[BaseCommonAPI]',
    ):
        assert api_impl._extra_set_cookies_from_response(make_response(headers=headers)) == expected

    async def test_from_real_response(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_get(url=f'{test_server.base_url}/set_cookie')

        assert api_impl._extra_set_cookies_from_response(response) == {'session': 'abc', 'token': 'v1=v2'}


class TestIterCookiesItem:
    """cookies 迭代器测试"""

    @pytest.mark.parametrize(
        ('cookies', 'expected'),
        [
            pytest.param(None, [], id='none_cookies'),
            pytest.param({'a': '1', 'b': None}, [('a', '1'), ('b', '')], id='dict_cookies'),
            pytest.param([('a', '1'), ('b', '2')], [('a', '1'), ('b', '2')], id='list_cookies'),
            pytest.param(Cookies({'a': '1'}), [('a', '1')], id='nonebot_cookies'),
            pytest.param(make_cookie_jar('a', '1'), [('a', '1')], id='cookie_jar'),
        ],
    )
    def test_iter_cookies_item(
            self, cookies: Any, expected: list[tuple[str, str]], api_impl: 'type[BaseCommonAPI]',
    ):
        assert list(api_impl._iter_cookies_item(cookies)) == expected

    def test_unsupported_type_rejected_on_iteration(self, api_impl: 'type[BaseCommonAPI]'):
        """生成器惰性求值, TypeError 在迭代(而非调用)时抛出"""
        with pytest.raises(TypeError, match='Unsupported cookies type'):
            list(api_impl._iter_cookies_item(123))


class TestIterHeadersItem:
    """headers 迭代器测试"""

    @pytest.mark.parametrize(
        ('headers', 'expected'),
        [
            pytest.param(None, [], id='none_headers'),
            pytest.param({'a': '1', 'b': None}, [('a', '1'), ('b', '')], id='dict_headers'),
            pytest.param([('a', '1')], [('a', '1')], id='list_headers'),
            pytest.param(
                CIMultiDict([('X-A', '1'), ('x-a', '2')]),
                [('X-A', '1'), ('x-a', '2')],
                id='multidict_headers',
            ),
        ],
    )
    def test_iter_headers_item(
            self, headers: Any, expected: list[tuple[str, str]], api_impl: 'type[BaseCommonAPI]',
    ):
        assert list(api_impl._iter_headers_item(headers)) == expected

    def test_unsupported_type_rejected_on_iteration(self, api_impl: 'type[BaseCommonAPI]'):
        with pytest.raises(TypeError, match='Unsupported headers type'):
            list(api_impl._iter_headers_item(123))


class TestInitOmegaRequests:
    """_init_omega_requests 实例装配测试(no_headers=True 时空 headers 经 OmegaRequests 归一为 None)"""

    @pytest.mark.parametrize(
        ('kwargs', 'expected_timeout', 'expected_headers', 'expected_cookies'),
        [
            pytest.param({}, None, {'x-test-api': 'omega'}, None, id='default'),
            pytest.param(
                {'timeout': 10, 'headers': {'a': 'b'}, 'cookies': {'c': 'd'}},
                10, {'a': 'b'}, {'c': 'd'},
                id='custom',
            ),
            pytest.param({'no_headers': True}, None, None, None, id='no_headers'),
            pytest.param(
                {'headers': {'a': 'b'}, 'no_headers': True},
                None, None, None,
                id='no_headers_overrides_explicit_headers',
            ),
            pytest.param(
                {'cookies': {'c': 'd'}, 'no_cookies': True},
                None, {'x-test-api': 'omega'}, None,
                id='no_cookies',
            ),
        ],
    )
    def test_init_omega_requests(
            self, kwargs: dict[str, Any], expected_timeout: int | None,
            expected_headers: dict[str, str] | None, expected_cookies: dict[str, str] | None,
            api_impl: 'type[BaseCommonAPI]',
    ):
        from src.utils.omega_requests import OmegaRequests

        requests = api_impl._init_omega_requests(**kwargs)

        if expected_timeout is None:
            expected_timeout = OmegaRequests.get_default_timeout()

        assert isinstance(requests, OmegaRequests)
        assert requests.timeout == expected_timeout
        assert requests.headers == expected_headers
        assert requests.cookies == expected_cookies


class TestRequestMethods:
    """请求方法集成测试"""

    async def test_request_get(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_get(url=f'{test_server.base_url}/get', params={'a': '1'})

        assert response.status_code == 200
        data = api_impl._parse_content_as_json(response)
        assert ['a', '1'] in data['params']
        assert data['headers']['x-test-api'] == 'omega'

    @pytest.mark.parametrize(
        ('method', 'status_code', 'kwargs'),
        [
            pytest.param('_request_get', 404, {}, id='get'),
            pytest.param('_request_delete', 500, {}, id='delete'),
            pytest.param('_request_post', 500, {'content': b'x'}, id='post'),
            pytest.param('_request_put', 500, {'content': b'x'}, id='put'),
        ],
    )
    async def test_request_error_status(
            self, method: str, status_code: int, kwargs: dict[str, Any],
            api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        from src.exception import WebSourceException

        url = f'{test_server.base_url}/status/{status_code}'

        with pytest.raises(WebSourceException) as exc_info:
            await getattr(api_impl, method)(url=url, **kwargs)

        assert exc_info.value.status_code == status_code
        assert exc_info.value.content == f'status {status_code}'.encode()
        assert url in exc_info.value.message

    @pytest.mark.parametrize(
        ('status_codes', 'accepted'),
        [
            pytest.param([201, 206], True, id='other_2xx_status_accepted'),
            pytest.param([301], False, id='redirect_status_rejected'),
        ],
    )
    async def test_status_code_handling(
            self, status_codes: list[int], accepted: bool,
            api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        """201/206 等其他 2xx 状态码同样视为成功, 3xx 等非 2xx 状态码仍视为失败"""
        from src.exception import WebSourceException

        for status_code in status_codes:
            if accepted:
                response = await api_impl._request_get(url=f'{test_server.base_url}/status/{status_code}')
                assert response.status_code == status_code
            else:
                with pytest.raises(WebSourceException) as exc_info:
                    await api_impl._request_get(url=f'{test_server.base_url}/status/{status_code}')

                assert exc_info.value.status_code == status_code

    async def test_request_post_json(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_post(url=f'{test_server.base_url}/post_json', json={'k': 'v'})

        assert api_impl._parse_content_as_json(response) == {'echo': {'k': 'v'}}

    async def test_request_post_content(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_post(url=f'{test_server.base_url}/post', content=b'\x00\x01raw')

        assert api_impl._parse_content_as_bytes(response) == b'\x00\x01raw'

    async def test_request_post_data(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_post(url=f'{test_server.base_url}/post', data={'k': 'v'})

        assert api_impl._parse_content_as_bytes(response) == b'k=v'

    async def test_request_put(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_put(url=f'{test_server.base_url}/put', content=b'data')

        assert api_impl._parse_content_as_json(response) == {'ok': True, 'method': 'PUT'}

    async def test_request_delete(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_delete(url=f'{test_server.base_url}/delete')

        assert api_impl._parse_content_as_json(response) == {'ok': True, 'method': 'DELETE'}

    async def test_custom_headers_replace_default(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_get(url=f'{test_server.base_url}/get', headers={'x-custom': '1'})

        data = api_impl._parse_content_as_json(response)
        assert data['headers']['x-custom'] == '1'
        assert 'x-test-api' not in data['headers']

    async def test_no_headers(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_get(url=f'{test_server.base_url}/get', no_headers=True)

        data = api_impl._parse_content_as_json(response)
        assert 'x-test-api' not in data['headers']
        assert 'user-agent' in data['headers']  # aiohttp 自动补全

    async def test_custom_cookies(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_get(url=f'{test_server.base_url}/get', cookies={'session': 'abc'})

        data = api_impl._parse_content_as_json(response)
        assert 'session=abc' in data['headers']['cookie']

    async def test_get_resource_as_json(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        data = await api_impl._get_resource_as_json(url=f'{test_server.base_url}/get', params={'k': 'v'})

        assert ['k', 'v'] in data['params']

    async def test_get_resource_as_bytes(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        content = await api_impl._get_resource_as_bytes(url=f'{test_server.base_url}/download')

        assert content == _DOWNLOAD_PAYLOAD

    async def test_get_resource_as_text(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        text = await api_impl._get_resource_as_text(url=f'{test_server.base_url}/get')

        assert 'headers' in text

    async def test_post_acquire_as_json(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        data = await api_impl._post_acquire_as_json(url=f'{test_server.base_url}/post_json', json={'a': 1})

        assert data == {'echo': {'a': 1}}


class TestStreamMethods:
    """流式方法集成测试"""

    @pytest.mark.parametrize(
        ('method', 'kwargs'),
        [
            pytest.param('_stream_request_get', {}, id='get'),
            pytest.param('_stream_request_post', {'content': b'x'}, id='post'),
        ],
    )
    async def test_stream_request(
            self, method: str, kwargs: dict[str, Any],
            api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        responses = [x async for x in getattr(api_impl, method)(url=f'{test_server.base_url}/stream', **kwargs)]

        assert b''.join(x.content for x in responses) == _STREAM_PAYLOAD

    @pytest.mark.parametrize(
        ('method', 'kwargs'),
        [
            pytest.param('_stream_request_get', {}, id='get'),
            pytest.param('_stream_request_post', {'content': b'x'}, id='post'),
        ],
    )
    async def test_stream_error_status_rejected(
            self, method: str, kwargs: dict[str, Any],
            api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        from src.exception import WebSourceException

        async def _collect():
            return [x async for x in getattr(api_impl, method)(url=f'{test_server.base_url}/status/500', **kwargs)]

        with pytest.raises(WebSourceException) as exc_info:
            await _collect()

        assert exc_info.value.status_code == 500

    async def test_stream_other_2xx_accepted(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        """流式请求同样接受 200 以外的 2xx 状态码"""
        responses = [x async for x in api_impl._stream_request_get(url=f'{test_server.base_url}/status/206')]

        assert responses
        assert all(x.status_code == 206 for x in responses)
        assert b''.join(x.content for x in responses) == b'status 206'

    async def test_stream_empty_error_yields_nothing(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        """空响应体的错误响应在流式请求中不产生分块, 状态码校验无从执行"""
        responses = [x async for x in api_impl._stream_request_get(url=f'{test_server.base_url}/status_empty/404')]

        assert responses == []

    @pytest.mark.parametrize(
        ('method', 'kwargs'),
        [
            pytest.param('_stream_get_resource_iter_lines', {}, id='get'),
            pytest.param('_stream_post_acquire_iter_lines', {'content': b'x'}, id='post'),
        ],
    )
    async def test_stream_acquire_iter_lines(
            self, method: str, kwargs: dict[str, Any],
            api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        lines = [x async for x in getattr(api_impl, method)(url=f'{test_server.base_url}/lines', **kwargs)]

        assert lines == _LINES_EXPECTED


class TestDownloadResource:
    """_download_resource 集成测试"""

    async def test_download_keep_origin_file_name(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
            tmp_path: Path, save_folder: 'AnyResource',
    ):
        file = await api_impl._download_resource(save_folder, f'{test_server.base_url}/download_file/pic.jpg')

        assert file.path == tmp_path / 'pic.jpg'
        assert file.path.read_bytes() == _DOWNLOAD_PAYLOAD

    async def test_download_custom_file_name(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
            tmp_path: Path, save_folder: 'AnyResource',
    ):
        file = await api_impl._download_resource(
            save_folder,
            f'{test_server.base_url}/download_file/pic.jpg',
            custom_file_name='custom.bin',
        )

        assert file.path == tmp_path / 'custom.bin'

    async def test_download_hash_file_name(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, save_folder: 'AnyResource',
    ):
        """哈希文件名前缀应为 API 类名而非元类名 ABCMeta"""
        from src.utils.omega_requests import OmegaRequests

        url = f'{test_server.base_url}/download_file/pic.jpg'

        file = await api_impl._download_resource(save_folder, url, hash_file_name=True)

        assert file.name == OmegaRequests.hash_url_file_name('_CommonAPIImpl', url=url)
        assert file.name.startswith('_CommonAPIImpl_')
        assert not file.name.startswith('ABCMeta_')
        assert file.path.read_bytes() == _DOWNLOAD_PAYLOAD

    async def test_download_empty_file_name_fallback_hash(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
            tmp_path: Path, save_folder: 'AnyResource',
    ):
        """URL 无文件名(空路径)时回退哈希文件名, 不再因写入目录而崩溃"""
        from src.utils.omega_requests import OmegaRequests

        url = f'{test_server.base_url}/'

        file = await api_impl._download_resource(save_folder, url)

        assert file.name == OmegaRequests.hash_url_file_name('_CommonAPIImpl', url=url)
        assert file.path.parent == tmp_path
        assert file.path.read_bytes() == _DOWNLOAD_PAYLOAD

    async def test_download_custom_file_name_traversal_stripped(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
            tmp_path: Path, save_folder: 'AnyResource',
    ):
        """自定义文件名剥离路径层级, 防止逃逸下载目录"""
        file = await api_impl._download_resource(
            save_folder,
            f'{test_server.base_url}/download_file/pic.jpg',
            custom_file_name='../evil.bin',
        )

        assert file.name == 'evil.bin'
        assert file.path.parent == tmp_path

    async def test_download_invalid_chars_sanitized(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, save_folder: 'AnyResource',
    ):
        """Windows 非法字符替换为下划线"""
        file = await api_impl._download_resource(
            save_folder,
            f'{test_server.base_url}/download_file/pic.jpg',
            custom_file_name='bad<>name.bin',
        )

        assert file.name == 'bad__name.bin'

    async def test_download_subdir(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
            tmp_path: Path, save_folder: 'AnyResource',
    ):
        file = await api_impl._download_resource(
            save_folder,
            f'{test_server.base_url}/download_file/pic.jpg',
            subdir='sub',
        )

        assert file.path == tmp_path / 'sub' / 'pic.jpg'

    async def test_download_ignore_exist_file(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
            tmp_path: Path, save_folder: 'AnyResource',
    ):
        tmp_path.joinpath('exist.bin').write_bytes(b'existing')

        file = await api_impl._download_resource(
            save_folder,
            f'{test_server.base_url}/download_file/exist.bin',
            ignore_exist_file=True,
        )

        assert file.path.read_bytes() == b'existing'

    async def test_download_error_status(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, save_folder: 'AnyResource',
    ):
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await api_impl._download_resource(save_folder, f'{test_server.base_url}/status/404')

        assert exc_info.value.status_code == 404

    async def test_download_stream_mode(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
            tmp_path: Path, save_folder: 'AnyResource',
    ):
        file = await api_impl._download_resource(
            save_folder,
            f'{test_server.base_url}/download_file/stream_pic.jpg',
            stream_download=True,
        )

        assert file.path.read_bytes() == _DOWNLOAD_PAYLOAD
        assert not tmp_path.joinpath('stream_pic.jpg.DOWNLOADING_TMP').exists()


class TestParseWrappers:
    """内容解析委托方法测试"""

    @pytest.mark.parametrize(
        ('method', 'content', 'expected'),
        [
            pytest.param('_parse_content_as_bytes', b'abc', b'abc', id='parse_content_as_bytes'),
            pytest.param('_parse_content_as_json', b'{"a": 1}', {'a': 1}, id='parse_content_as_json'),
            pytest.param('_parse_content_as_text', b'abc', 'abc', id='parse_content_as_text'),
        ],
    )
    def test_parse_content_wrapper(
            self, method: str, content: bytes, expected: Any, api_impl: 'type[BaseCommonAPI]',
    ):
        assert getattr(api_impl, method)(make_response(content)) == expected

    async def test_iter_content_as_lines(self, api_impl: 'type[BaseCommonAPI]'):
        lines = [
            x async for x in api_impl._iter_content_as_lines(line_chunks_stream([b'line1\r', b'\nline2\r']))
        ]

        assert lines == ['line1', 'line2']


class TestDefaultDelegations:
    """OmegaRequests 默认配置委托方法测试"""

    @pytest.mark.parametrize(
        ('api_methods', 'requests_method'),
        [
            pytest.param(
                ['_get_default_timeout', '_get_omega_requests_default_timeout'], 'get_default_timeout',
                id='default_timeout_delegation',
            ),
            pytest.param(
                ['_get_omega_requests_default_headers'], 'get_default_headers',
                id='default_headers_delegation',
            ),
        ],
    )
    def test_default_delegation(
            self, api_methods: list[str], requests_method: str, api_impl: 'type[BaseCommonAPI]',
    ):
        from src.utils.omega_requests import OmegaRequests

        expected = getattr(OmegaRequests, requests_method)()
        for api_method in api_methods:
            assert getattr(api_impl, api_method)() == expected


class TestAutoRedirects:
    """auto_redirects 参数透传与重定向行为测试

    覆盖分两层: 本类验证 BaseCommonAPI 包装层的参数透传与重定向处理, 驱动层重定向行为由 test_001 覆盖
    """

    @pytest.mark.parametrize(
        ('method', 'stream', 'expected'),
        [
            pytest.param('_request_get', False, True, id='request_get_default_true'),
            pytest.param('_request_get', False, False, id='request_get_explicit_false'),
            pytest.param('_request_delete', False, False, id='request_delete'),
            pytest.param('_request_post', False, False, id='request_post'),
            pytest.param('_request_put', False, False, id='request_put'),
            pytest.param('_get_resource_as_json', False, False, id='get_resource_as_json'),
            pytest.param('_get_resource_as_bytes', False, False, id='get_resource_as_bytes'),
            pytest.param('_get_resource_as_text', False, False, id='get_resource_as_text'),
            pytest.param('_post_acquire_as_json', False, False, id='post_acquire_as_json'),
            pytest.param('_stream_request_get', True, False, id='stream_request_get'),
            pytest.param('_stream_request_post', True, False, id='stream_request_post'),
            pytest.param('_stream_get_resource_iter_lines', True, False, id='stream_get_resource_iter_lines'),
            pytest.param('_stream_post_acquire_iter_lines', True, False, id='stream_post_acquire_iter_lines'),
        ],
    )
    async def test_auto_redirects_passthrough(
            self, method: str, stream: bool, expected: bool,
            api_impl: 'type[BaseCommonAPI]', monkeypatch: pytest.MonkeyPatch,
    ):
        """默认 True 与显式 False 均应透传至底层 Request setup"""
        kwargs = {} if expected else {'auto_redirects': False}
        if stream:
            captured = capture_driver_stream_request(monkeypatch, stream_payload=b'a\n')
            lines = [x async for x in getattr(api_impl, method)(url='http://127.0.0.1/', **kwargs)]
            if method.endswith('iter_lines'):
                assert lines == ['a']
        else:
            captured = capture_driver_request(monkeypatch)
            await getattr(api_impl, method)(url='http://127.0.0.1/', **kwargs)

        assert len(captured) == 1
        assert captured[0].auto_redirects is expected

    async def test_request_get_follows_redirect_by_default(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        token = new_request_token()

        response = await api_impl._request_get(
            url=f'{test_server.base_url}/redirect/302', params={'target': f'/redirect_target/{token}'}
        )

        assert response.status_code == 200
        assert api_impl._parse_content_as_json(response) == {'ok': True, 'token': token}
        assert test_server.state.counters[f'redirect_target:{token}'] == 1

    @pytest.mark.parametrize(
        'method',
        ['_request_get', '_request_delete', '_request_post', '_request_put', '_get_resource_as_json'],
    )
    async def test_request_methods_no_follow_redirect_rejected(
            self, method: str, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        """不跟随重定向时 3xx 不属于 2xx, 应抛出 WebSourceException 且不触达重定向目标"""
        from src.exception import WebSourceException

        token = new_request_token()

        with pytest.raises(WebSourceException) as exc_info:
            await getattr(api_impl, method)(
                url=f'{test_server.base_url}/redirect/302',
                params={'target': f'/redirect_target/{token}'},
                auto_redirects=False,
            )

        assert exc_info.value.status_code == 302
        assert test_server.state.counters[f'redirect_target:{token}'] == 0

    async def test_get_resource_as_json_follows_redirect(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        token = new_request_token()

        data = await api_impl._get_resource_as_json(
            url=f'{test_server.base_url}/redirect/302', params={'target': f'/redirect_target/{token}'}
        )

        assert data == {'ok': True, 'token': token}

    async def test_get_resource_as_bytes_follows_redirect(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        content = await api_impl._get_resource_as_bytes(
            url=f'{test_server.base_url}/redirect/302', params={'target': '/download'}
        )

        assert content == _DOWNLOAD_PAYLOAD

    async def test_get_resource_as_text_follows_redirect(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        text = await api_impl._get_resource_as_text(
            url=f'{test_server.base_url}/redirect/302', params={'target': '/get'}
        )

        assert 'headers' in text

    async def test_post_acquire_as_json_follows_307_redirect(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        """307 保持方法与请求体, echo 目标应收到原始 JSON"""
        data = await api_impl._post_acquire_as_json(
            url=f'{test_server.base_url}/redirect/307', params={'target': '/post_json'}, json={'a': 1}
        )

        assert data == {'echo': {'a': 1}}

    async def test_stream_request_get_follows_redirect(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        responses = [
            x async for x in api_impl._stream_request_get(
                url=f'{test_server.base_url}/redirect/302', params={'target': '/stream'}
            )
        ]

        assert b''.join(x.content for x in responses) == _STREAM_PAYLOAD

    @pytest.mark.parametrize('method', ['_stream_request_get', '_stream_request_post'])
    async def test_stream_request_no_follow_redirect_rejected(
            self, method: str, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        """不跟随重定向时 302 分块触发状态码校验, 抛出 WebSourceException"""
        from src.exception import WebSourceException

        async def _collect():
            return [
                x async for x in getattr(api_impl, method)(
                    url=f'{test_server.base_url}/redirect/302', auto_redirects=False
                )
            ]

        with pytest.raises(WebSourceException) as exc_info:
            await _collect()

        assert exc_info.value.status_code == 302

    @pytest.mark.parametrize(
        ('method', 'redirect_code', 'kwargs'),
        [
            pytest.param('_stream_get_resource_iter_lines', 302, {}, id='get'),
            pytest.param('_stream_post_acquire_iter_lines', 307, {'content': b'x'}, id='post_307'),
        ],
    )
    async def test_iter_lines_wrappers_follow_redirect(
            self, method: str, redirect_code: int, kwargs: dict[str, Any],
            api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        lines = [
            x async for x in getattr(api_impl, method)(
                url=f'{test_server.base_url}/redirect/{redirect_code}',
                params={'target': '/lines'},
                **kwargs,
            )
        ]

        assert lines == _LINES_EXPECTED
