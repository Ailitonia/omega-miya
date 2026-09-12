"""
@Author         : Ailitonia
@Date           : 2026/9/12 22:50
@FileName       : test_002_omega_common_api
@Project        : omega-miya
@Description    : omega_common_api(BaseCommonAPI)单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from http.cookiejar import Cookie, CookieJar
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from multidict import CIMultiDict

from tests.test_003_web.helpers import _DOWNLOAD_PAYLOAD, _LINES_EXPECTED, _STREAM_PAYLOAD, line_chunks_stream

if TYPE_CHECKING:
    from src.utils.omega_common_api import BaseCommonAPI


def _make_response(content: Any = None, headers: Any = None):
    """构造合成 nonebot Response"""
    from nonebot.drivers import Response

    return Response(200, headers=headers, content=content)


def _make_cookie_jar(name: str, value: str) -> CookieJar:
    """构造含单个 cookie 的 http.cookiejar.CookieJar"""
    jar = CookieJar()
    jar.set_cookie(Cookie(
        version=0, name=name, value=value,
        port=None, port_specified=False, domain='example.com', domain_specified=False, domain_initial_dot=False,
        path='/', path_specified=True, secure=False, expires=None, discard=True,
        comment=None, comment_url=None, rest={}, rfc2109=False,
    ))
    return jar


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

    def test_single_cookie_with_attributes(self, api_impl: 'type[BaseCommonAPI]'):
        response = _make_response(headers={'set-cookie': 'a=1; Path=/; HttpOnly'})

        assert api_impl._extra_set_cookies_from_response(response) == {'a': '1'}

    def test_multiple_set_cookie_headers(self, api_impl: 'type[BaseCommonAPI]'):
        headers = CIMultiDict([('set-cookie', 'a=1; Path=/'), ('Set-Cookie', 'b=2; Path=/')])

        assert api_impl._extra_set_cookies_from_response(_make_response(headers=headers)) == {'a': '1', 'b': '2'}

    def test_cookie_value_with_equals(self, api_impl: 'type[BaseCommonAPI]'):
        response = _make_response(headers={'set-cookie': 'token=v1=v2; Path=/'})

        assert api_impl._extra_set_cookies_from_response(response) == {'token': 'v1=v2'}

    def test_cookie_without_equals_skipped(self, api_impl: 'type[BaseCommonAPI]'):
        response = _make_response(headers={'set-cookie': 'invalid; Path=/'})

        assert api_impl._extra_set_cookies_from_response(response) == {}

    def test_cookie_empty_value_kept(self, api_impl: 'type[BaseCommonAPI]'):
        response = _make_response(headers={'set-cookie': 'a=; Path=/'})

        assert api_impl._extra_set_cookies_from_response(response) == {'a': ''}

    def test_similar_header_not_matched(self, api_impl: 'type[BaseCommonAPI]'):
        headers = CIMultiDict([('set-cookie', 'a=1; Path=/'), ('set-cookie2', 'b=2; Path=/')])

        assert api_impl._extra_set_cookies_from_response(_make_response(headers=headers)) == {'a': '1'}

    def test_no_cookie_header(self, api_impl: 'type[BaseCommonAPI]'):
        assert api_impl._extra_set_cookies_from_response(_make_response()) == {}

    async def test_from_real_response(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_get(url=f'{test_server.base_url}/set_cookie')

        assert api_impl._extra_set_cookies_from_response(response) == {'session': 'abc', 'token': 'v1=v2'}


class TestIterCookiesItem:
    """cookies 迭代器测试"""

    def test_none_cookies(self, api_impl: 'type[BaseCommonAPI]'):
        assert list(api_impl._iter_cookies_item(None)) == []

    def test_dict_cookies(self, api_impl: 'type[BaseCommonAPI]'):
        assert list(api_impl._iter_cookies_item({'a': '1', 'b': None})) == [('a', '1'), ('b', '')]

    def test_list_cookies(self, api_impl: 'type[BaseCommonAPI]'):
        assert list(api_impl._iter_cookies_item([('a', '1'), ('b', '2')])) == [('a', '1'), ('b', '2')]

    def test_nonebot_cookies(self, api_impl: 'type[BaseCommonAPI]'):
        from nonebot.internal.driver import Cookies

        assert list(api_impl._iter_cookies_item(Cookies({'a': '1'}))) == [('a', '1')]

    def test_cookie_jar(self, api_impl: 'type[BaseCommonAPI]'):
        assert list(api_impl._iter_cookies_item(_make_cookie_jar('a', '1'))) == [('a', '1')]

    def test_unsupported_type_rejected_on_iteration(self, api_impl: 'type[BaseCommonAPI]'):
        """生成器惰性求值, TypeError 在迭代(而非调用)时抛出"""
        with pytest.raises(TypeError, match='Unsupported cookies type'):
            list(api_impl._iter_cookies_item(123))


class TestIterHeadersItem:
    """headers 迭代器测试"""

    def test_none_headers(self, api_impl: 'type[BaseCommonAPI]'):
        assert list(api_impl._iter_headers_item(None)) == []

    def test_dict_headers(self, api_impl: 'type[BaseCommonAPI]'):
        assert list(api_impl._iter_headers_item({'a': '1', 'b': None})) == [('a', '1'), ('b', '')]

    def test_list_headers(self, api_impl: 'type[BaseCommonAPI]'):
        assert list(api_impl._iter_headers_item([('a', '1')])) == [('a', '1')]

    def test_multidict_headers(self, api_impl: 'type[BaseCommonAPI]'):
        headers = CIMultiDict([('X-A', '1'), ('x-a', '2')])

        assert list(api_impl._iter_headers_item(headers)) == [('X-A', '1'), ('x-a', '2')]

    def test_unsupported_type_rejected_on_iteration(self, api_impl: 'type[BaseCommonAPI]'):
        with pytest.raises(TypeError, match='Unsupported headers type'):
            list(api_impl._iter_headers_item(123))


class TestInitOmegaRequests:
    """_init_omega_requests 实例装配测试"""

    def test_default(self, api_impl: 'type[BaseCommonAPI]'):
        from src.utils.omega_requests import OmegaRequests

        requests = api_impl._init_omega_requests()

        assert isinstance(requests, OmegaRequests)
        assert requests.timeout == OmegaRequests.get_default_timeout()
        assert requests.headers == {'x-test-api': 'omega'}
        assert requests.cookies is None

    def test_custom(self, api_impl: 'type[BaseCommonAPI]'):
        requests = api_impl._init_omega_requests(timeout=10, headers={'a': 'b'}, cookies={'c': 'd'})

        assert requests.timeout == 10
        assert requests.headers == {'a': 'b'}
        assert requests.cookies == {'c': 'd'}

    def test_no_headers(self, api_impl: 'type[BaseCommonAPI]'):
        """no_headers=True 时空 headers 经 OmegaRequests 归一为 None(发送时不携带默认头)"""
        requests = api_impl._init_omega_requests(no_headers=True)

        assert requests.headers is None

    def test_no_headers_overrides_explicit_headers(self, api_impl: 'type[BaseCommonAPI]'):
        requests = api_impl._init_omega_requests(headers={'a': 'b'}, no_headers=True)

        assert requests.headers is None

    def test_no_cookies(self, api_impl: 'type[BaseCommonAPI]'):
        requests = api_impl._init_omega_requests(cookies={'c': 'd'}, no_cookies=True)

        assert requests.cookies is None


class TestRequestMethods:
    """请求方法集成测试"""

    async def test_request_get(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        response = await api_impl._request_get(url=f'{test_server.base_url}/get', params={'a': '1'})

        assert response.status_code == 200
        data = api_impl._parse_content_as_json(response)
        assert ['a', '1'] in data['params']
        assert data['headers']['x-test-api'] == 'omega'

    async def test_request_get_error_status(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await api_impl._request_get(url=f'{test_server.base_url}/status/404')

        assert exc_info.value.status_code == 404
        assert exc_info.value.content == b'status 404'
        assert f'{test_server.base_url}/status/404' in exc_info.value.message

    async def test_other_2xx_status_accepted(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        """201/206 等其他 2xx 状态码同样视为成功"""
        response_201 = await api_impl._request_get(url=f'{test_server.base_url}/status/201')
        assert response_201.status_code == 201

        response_206 = await api_impl._request_get(url=f'{test_server.base_url}/status/206')
        assert response_206.status_code == 206

    async def test_redirect_status_rejected(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        """3xx 等非 2xx 状态码仍视为失败"""
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await api_impl._request_get(url=f'{test_server.base_url}/status/301')

        assert exc_info.value.status_code == 301

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

    async def test_request_delete_error_status(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await api_impl._request_delete(url=f'{test_server.base_url}/status/500')

        assert exc_info.value.status_code == 500

    async def test_request_post_error_status(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await api_impl._request_post(url=f'{test_server.base_url}/status/500', content=b'x')

        assert exc_info.value.status_code == 500

    async def test_request_put_error_status(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await api_impl._request_put(url=f'{test_server.base_url}/status/500', content=b'x')

        assert exc_info.value.status_code == 500

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

    async def test_stream_request_get(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        responses = [x async for x in api_impl._stream_request_get(url=f'{test_server.base_url}/stream')]

        assert b''.join(x.content for x in responses) == _STREAM_PAYLOAD

    async def test_stream_request_post(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        responses = [
            x async for x in api_impl._stream_request_post(url=f'{test_server.base_url}/stream', content=b'x')
        ]

        assert b''.join(x.content for x in responses) == _STREAM_PAYLOAD

    async def test_stream_error_status_rejected(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        from src.exception import WebSourceException

        async def _collect():
            return [x async for x in api_impl._stream_request_get(url=f'{test_server.base_url}/status/500')]

        with pytest.raises(WebSourceException) as exc_info:
            await _collect()

        assert exc_info.value.status_code == 500

    async def test_stream_post_error_status_rejected(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        from src.exception import WebSourceException

        async def _collect():
            return [
                x async for x in api_impl._stream_request_post(url=f'{test_server.base_url}/status/500', content=b'x')
            ]

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

    async def test_stream_get_resource_iter_lines(self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace):
        lines = [x async for x in api_impl._stream_get_resource_iter_lines(url=f'{test_server.base_url}/lines')]

        assert lines == _LINES_EXPECTED

    async def test_stream_post_acquire_iter_lines(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace,
    ):
        lines = [
            x async for x in api_impl._stream_post_acquire_iter_lines(
                url=f'{test_server.base_url}/lines', content=b'x'
            )
        ]

        assert lines == _LINES_EXPECTED


class TestDownloadResource:
    """_download_resource 集成测试"""

    @staticmethod
    def _save_folder(tmp_path: Path):
        from src.resource import AnyResource

        return AnyResource(tmp_path)

    async def test_download_keep_origin_file_name(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        file = await api_impl._download_resource(
            self._save_folder(tmp_path), f'{test_server.base_url}/download_file/pic.jpg'
        )

        assert file.path == tmp_path / 'pic.jpg'
        assert file.path.read_bytes() == _DOWNLOAD_PAYLOAD

    async def test_download_custom_file_name(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        file = await api_impl._download_resource(
            self._save_folder(tmp_path),
            f'{test_server.base_url}/download_file/pic.jpg',
            custom_file_name='custom.bin',
        )

        assert file.path == tmp_path / 'custom.bin'

    async def test_download_hash_file_name(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        """哈希文件名前缀应为 API 类名而非元类名 ABCMeta"""
        from src.utils.omega_requests import OmegaRequests

        url = f'{test_server.base_url}/download_file/pic.jpg'

        file = await api_impl._download_resource(self._save_folder(tmp_path), url, hash_file_name=True)

        assert file.name == OmegaRequests.hash_url_file_name('_CommonAPIImpl', url=url)
        assert file.name.startswith('_CommonAPIImpl_')
        assert not file.name.startswith('ABCMeta_')
        assert file.path.read_bytes() == _DOWNLOAD_PAYLOAD

    async def test_download_empty_file_name_fallback_hash(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        """URL 无文件名(空路径)时回退哈希文件名, 不再因写入目录而崩溃"""
        from src.utils.omega_requests import OmegaRequests

        url = f'{test_server.base_url}/'

        file = await api_impl._download_resource(self._save_folder(tmp_path), url)

        assert file.name == OmegaRequests.hash_url_file_name('_CommonAPIImpl', url=url)
        assert file.path.parent == tmp_path
        assert file.path.read_bytes() == _DOWNLOAD_PAYLOAD

    async def test_download_custom_file_name_traversal_stripped(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        """自定义文件名剥离路径层级, 防止逃逸下载目录"""
        file = await api_impl._download_resource(
            self._save_folder(tmp_path),
            f'{test_server.base_url}/download_file/pic.jpg',
            custom_file_name='../evil.bin',
        )

        assert file.name == 'evil.bin'
        assert file.path.parent == tmp_path

    async def test_download_invalid_chars_sanitized(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        """Windows 非法字符替换为下划线"""
        file = await api_impl._download_resource(
            self._save_folder(tmp_path),
            f'{test_server.base_url}/download_file/pic.jpg',
            custom_file_name='bad<>name.bin',
        )

        assert file.name == 'bad__name.bin'

    async def test_download_subdir(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        file = await api_impl._download_resource(
            self._save_folder(tmp_path),
            f'{test_server.base_url}/download_file/pic.jpg',
            subdir='sub',
        )

        assert file.path == tmp_path / 'sub' / 'pic.jpg'

    async def test_download_ignore_exist_file(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        tmp_path.joinpath('exist.bin').write_bytes(b'existing')

        file = await api_impl._download_resource(
            self._save_folder(tmp_path),
            f'{test_server.base_url}/download_file/exist.bin',
            ignore_exist_file=True,
        )

        assert file.path.read_bytes() == b'existing'

    async def test_download_error_status(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        from src.exception import WebSourceException

        with pytest.raises(WebSourceException) as exc_info:
            await api_impl._download_resource(self._save_folder(tmp_path), f'{test_server.base_url}/status/404')

        assert exc_info.value.status_code == 404

    async def test_download_stream_mode(
            self, api_impl: 'type[BaseCommonAPI]', test_server: SimpleNamespace, tmp_path: Path,
    ):
        file = await api_impl._download_resource(
            self._save_folder(tmp_path),
            f'{test_server.base_url}/download_file/stream_pic.jpg',
            stream_download=True,
        )

        assert file.path.read_bytes() == _DOWNLOAD_PAYLOAD
        assert not tmp_path.joinpath('stream_pic.jpg.DOWNLOADING_TMP').exists()


class TestParseWrappers:
    """内容解析委托方法测试"""

    def test_parse_content_as_bytes(self, api_impl: 'type[BaseCommonAPI]'):
        assert api_impl._parse_content_as_bytes(_make_response(b'abc')) == b'abc'

    def test_parse_content_as_json(self, api_impl: 'type[BaseCommonAPI]'):
        assert api_impl._parse_content_as_json(_make_response(b'{"a": 1}')) == {'a': 1}

    def test_parse_content_as_text(self, api_impl: 'type[BaseCommonAPI]'):
        assert api_impl._parse_content_as_text(_make_response(b'abc')) == 'abc'

    async def test_iter_content_as_lines(self, api_impl: 'type[BaseCommonAPI]'):
        lines = [
            x async for x in api_impl._iter_content_as_lines(line_chunks_stream([b'line1\r', b'\nline2\r']))
        ]

        assert lines == ['line1', 'line2']


class TestDefaultDelegations:
    """OmegaRequests 默认配置委托方法测试"""

    def test_default_timeout_delegation(self, api_impl: 'type[BaseCommonAPI]'):
        from src.utils.omega_requests import OmegaRequests

        assert api_impl._get_default_timeout() == OmegaRequests.get_default_timeout()
        assert api_impl._get_omega_requests_default_timeout() == OmegaRequests.get_default_timeout()

    def test_default_headers_delegation(self, api_impl: 'type[BaseCommonAPI]'):
        from src.utils.omega_requests import OmegaRequests

        assert api_impl._get_omega_requests_default_headers() == OmegaRequests.get_default_headers()
