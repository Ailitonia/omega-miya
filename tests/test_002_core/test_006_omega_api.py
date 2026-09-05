"""
@Author         : Ailitonia
@Date           : 2026/9/4 21:50
@FileName       : test_006_omega_api
@Project        : omega-miya
@Description    : omega_api 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import time
from collections.abc import AsyncGenerator, Callable, Generator, Mapping
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr, ValidationError
from starlette.datastructures import QueryParams
from starlette.routing import Mount

if TYPE_CHECKING:
    from src.service.omega_api import OmegaAPI

_TEST_TIMESTAMP = 1700000000
"""测试用固定时间戳"""


def _get_master_key() -> str:
    from src.service.omega_api.config import api_config

    return api_config.omega_api_master_key.get_secret_value()


def _make_signed_headers(
        app_name: str,
        method: str,
        path: str,
        params: Mapping[str, str] | QueryParams | None = None,
        body: bytes = b'',
        timestamp: int | None = None,
) -> dict[str, str]:
    """使用测试环境主密钥为请求生成完整签名 Headers

    注意: path 需与中间件看到的 request.url.path 一致(直打子应用时不含挂载前缀, 经主应用挂载时含 /{app_name} 前缀)
    """
    from src.service.omega_api import OmegaAPI
    from src.service.omega_api.consts import APP_HEADER_KEY, TIMESTAMP_HEADER_KEY, TOKEN_HEADER_KEY

    timestamp, token = OmegaAPI.sign_params_hmac(
        _get_master_key(), app_name, method, path, params if params is not None else {}, body, timestamp=timestamp
    )
    return {APP_HEADER_KEY: app_name, TIMESTAMP_HEADER_KEY: str(timestamp), TOKEN_HEADER_KEY: token}


@pytest.fixture
def omega_api_factory() -> Generator[Callable[..., 'OmegaAPI'], None, None]:
    """OmegaAPI 实例工厂(自动分配唯一 app_name), 测试后自动清理全局注册与挂载"""
    import nonebot

    from src.service.omega_api import OmegaAPI
    from src.service.omega_api.api import _REGISTERED_APP

    created: list[OmegaAPI] = []

    def _factory(app_name: str | None = None, **kwargs: Any) -> 'OmegaAPI':
        api = OmegaAPI(app_name or f'omega_test_{uuid4().hex[:8]}', **kwargs)
        created.append(api)
        return api

    yield _factory

    nonebot_app = nonebot.get_app()
    for api in created:
        _REGISTERED_APP.discard(api._app_name)
        for route in list(nonebot_app.router.routes):
            if isinstance(route, Mount) and route.path == f'/{api._app_name}':
                nonebot_app.router.routes.remove(route)


@pytest.fixture
def open_api(omega_api_factory: Callable[..., 'OmegaAPI']) -> 'OmegaAPI':
    """未启用 token 校验的 OmegaAPI 实例"""
    api = omega_api_factory()

    @api.register_get_route('/test')
    async def _test_handler() -> dict[str, bool]:
        return {'ok': True}

    return api


@pytest.fixture
def secured_api(omega_api_factory: Callable[..., 'OmegaAPI']) -> 'OmegaAPI':
    """启用 token 校验的 OmegaAPI 实例(注册 GET/POST 测试路由)"""
    api = omega_api_factory(enable_token_verify=True)

    @api.register_get_route('/test')
    async def _test_handler() -> dict[str, bool]:
        return {'ok': True}

    @api.register_post_route('/echo')
    async def _echo_handler(request: Request) -> dict[str, str]:
        body = await request.body()
        return {'echo': body.decode()}

    return api


@pytest.fixture
async def secured_client(secured_api: 'OmegaAPI') -> AsyncGenerator[AsyncClient, None]:
    """直打子应用的 HTTP 客户端(不经过主应用挂载层)"""
    async with AsyncClient(transport=ASGITransport(app=secured_api._app), base_url='http://testserver') as client:
        yield client


class TestModuleContract:
    """模块导出契约测试"""

    def test_package_all_exports(self):
        import src.service.omega_api

        assert src.service.omega_api.__all__ == [
            'OmegaAPI',
            'OmegaAPIRouter',
            'StandardOmegaAPIReturn',
            'return_standard_api_result',
        ]

    def test_api_module_all_exports(self):
        import src.service.omega_api.api

        assert src.service.omega_api.api.__all__ == ['OmegaAPI', 'OmegaAPIRouter']

    def test_helpers_module_all_exports(self):
        import src.service.omega_api.helpers

        assert src.service.omega_api.helpers.__all__ == ['return_standard_api_result']

    def test_model_module_all_exports(self):
        import src.service.omega_api.model

        assert src.service.omega_api.model.__all__ == ['StandardOmegaAPIReturn']

    def test_consts_module_all_exports(self):
        import src.service.omega_api.consts

        assert src.service.omega_api.consts.__all__ == [
            'APP_HEADER_KEY',
            'TIMESTAMP_HEADER_KEY',
            'TOKEN_HEADER_KEY',
            'MethodLogColor',
        ]

    def test_config_module_all_exports(self):
        import src.service.omega_api.config

        assert src.service.omega_api.config.__all__ == ['api_config']


class TestConsts:
    """常量模块测试"""

    def test_header_keys(self):
        from src.service.omega_api.consts import APP_HEADER_KEY, TIMESTAMP_HEADER_KEY, TOKEN_HEADER_KEY

        assert APP_HEADER_KEY == 'X-OmegaAPI-App'
        assert TIMESTAMP_HEADER_KEY == 'X-OmegaAPI-Timestamp'
        assert TOKEN_HEADER_KEY == 'X-OmegaAPI-Token'

    def test_method_log_color(self):
        from src.service.omega_api.consts import MethodLogColor

        assert issubclass(MethodLogColor, str)
        assert MethodLogColor.GET == 'lg'
        assert MethodLogColor.POST == 'ly'
        assert MethodLogColor.PUT == 'lc'
        assert MethodLogColor.DELETE == 'lr'


class TestApiConfig:
    """配置模块测试(具体取值由 .env.test 决定, 仅断言类型与合法性)"""

    def test_config_values(self):
        from src.service.omega_api.config import api_config

        assert isinstance(api_config.omega_api_master_key, SecretStr)
        assert api_config.omega_api_master_key.get_secret_value()
        assert api_config.omega_api_timestamp_expire_seconds > 0
        assert api_config.omega_api_used_signatures_max_size > 0
        assert api_config.omega_api_request_body_max_size > 0


class TestStandardOmegaAPIReturn:
    """StandardOmegaAPIReturn 模型测试"""

    def test_basic_construction(self):
        from src.service.omega_api import StandardOmegaAPIReturn

        result = StandardOmegaAPIReturn[dict](error=False, body={'k': 'v'}, message='ok')

        assert result.error is False
        assert result.body == {'k': 'v'}
        assert result.message == 'ok'
        assert result.success is True

    def test_defaults(self):
        from src.service.omega_api import StandardOmegaAPIReturn

        result = StandardOmegaAPIReturn[bool](error=True)

        assert result.body is None
        assert result.message == ''
        assert result.success is False

    def test_frozen(self):
        from src.service.omega_api import StandardOmegaAPIReturn

        result = StandardOmegaAPIReturn(error=False)

        with pytest.raises(ValidationError):
            result.error = True

    def test_extra_fields_ignored(self):
        from src.service.omega_api import StandardOmegaAPIReturn

        result = StandardOmegaAPIReturn(error=False, unknown_field='x')

        assert not hasattr(result, 'unknown_field')
        assert 'unknown_field' not in result.model_dump()

    def test_generic_type_coercion(self):
        from src.service.omega_api import StandardOmegaAPIReturn

        result = StandardOmegaAPIReturn[int](error=False, body='5')

        assert result.body == 5

    def test_coerce_numbers_to_str(self):
        from src.service.omega_api import StandardOmegaAPIReturn

        result = StandardOmegaAPIReturn[str](error=False, body=123)

        assert result.body == '123'

    def test_from_attributes(self):
        from src.service.omega_api import StandardOmegaAPIReturn

        obj = SimpleNamespace(error=False, body='x', message='m')
        result = StandardOmegaAPIReturn[str].model_validate(obj)

        assert result.body == 'x'
        assert result.message == 'm'


class TestReturnStandardApiResult:
    """return_standard_api_result 装饰器测试"""

    async def test_success_result(self):
        from src.service.omega_api import StandardOmegaAPIReturn, return_standard_api_result

        @return_standard_api_result
        async def _handler() -> dict[str, int]:
            return {'a': 1}

        result = await _handler()

        assert isinstance(result, StandardOmegaAPIReturn)
        assert result.error is False
        assert result.body == {'a': 1}
        assert result.message == 'success'
        assert result.success

    async def test_http_exception_passthrough(self):
        from src.service.omega_api import return_standard_api_result

        @return_standard_api_result
        async def _handler() -> None:
            raise HTTPException(status_code=418, detail='teapot')

        with pytest.raises(HTTPException) as exc_info:
            await _handler()
        assert exc_info.value.status_code == 418
        assert exc_info.value.detail == 'teapot'

    async def test_general_exception_wrapped_without_leaking_detail(self):
        from src.service.omega_api import return_standard_api_result

        @return_standard_api_result
        async def _handler() -> None:
            raise RuntimeError('sensitive internal detail')

        result = await _handler()

        assert result.error is True
        assert result.body is None
        assert result.message == 'internal error'
        assert 'sensitive internal detail' not in result.message

    def test_non_coroutine_function_rejected(self):
        from src.service.omega_api import return_standard_api_result

        with pytest.raises(TypeError, match='not coroutine function'):
            return_standard_api_result(lambda: None)

    def test_wraps_preserves_metadata(self):
        from src.service.omega_api import return_standard_api_result

        @return_standard_api_result
        async def _my_handler() -> None:
            """handler docstring"""

        assert _my_handler.__name__ == '_my_handler'
        assert _my_handler.__doc__ == 'handler docstring'


class TestNormalizeMountStr:
    """挂载路径归一化测试(纯函数边界)"""

    @pytest.mark.parametrize(
        ('raw', 'expected'),
        [
            ('api', 'api'),
            ('/api/', 'api'),
            ('//api//', 'api'),
            ('  api  ', 'api'),
            (' /api/v1/ ', 'api/v1'),
            ('a/b/c', 'a/b/c'),
            ('api服务', 'api'),
            ('api\n\t\x00service', 'apiservice'),
            ('', ''),
            ('中文', ''),
            ('///', ''),
            ('   ', ''),
            ('/ /', ''),
        ],
    )
    def test_normalize(self, raw: str, expected: str):
        from src.service.omega_api import OmegaAPI

        assert OmegaAPI._normalize_mount_str(raw) == expected


class TestDeriveAppKey:
    """应用子密钥派生测试"""

    def test_deterministic(self):
        from src.service.omega_api import OmegaAPI

        assert OmegaAPI._derive_app_key('master', 'app') == OmegaAPI._derive_app_key('master', 'app')

    def test_different_app_names_differ(self):
        from src.service.omega_api import OmegaAPI

        assert OmegaAPI._derive_app_key('master', 'app1') != OmegaAPI._derive_app_key('master', 'app2')

    def test_different_master_keys_differ(self):
        from src.service.omega_api import OmegaAPI

        assert OmegaAPI._derive_app_key('key1', 'app') != OmegaAPI._derive_app_key('key2', 'app')

    def test_hex_sha256_format(self):
        from src.service.omega_api import OmegaAPI

        key = OmegaAPI._derive_app_key('master', 'app')

        assert len(key) == 64
        assert all(c in '0123456789abcdef' for c in key)
        assert key != 'master'


class TestNormalizeSignParams:
    """签名参数规范化测试"""

    def test_sorted_output(self):
        from src.service.omega_api import OmegaAPI

        assert OmegaAPI._normalize_sign_params({'b': '2', 'a': '1'}) == '[["a","1"],["b","2"]]'

    def test_multi_value_params_preserved(self):
        from src.service.omega_api import OmegaAPI

        assert OmegaAPI._normalize_sign_params(QueryParams('a=2&a=1&b=3')) == '[["a","1"],["a","2"],["b","3"]]'

    def test_empty_params(self):
        from src.service.omega_api import OmegaAPI

        assert OmegaAPI._normalize_sign_params({}) == '[]'

    def test_unicode_values_kept(self):
        from src.service.omega_api import OmegaAPI

        assert OmegaAPI._normalize_sign_params({'k': '中文'}) == '[["k","中文"]]'


class TestSignParamsHmac:
    """sign_params_hmac 签名测试"""

    def test_deterministic_with_fixed_timestamp(self):
        from src.service.omega_api import OmegaAPI

        ts1, sig1 = OmegaAPI.sign_params_hmac('key', 'app', 'GET', '/x', {'a': '1'}, b'body', timestamp=_TEST_TIMESTAMP)
        ts2, sig2 = OmegaAPI.sign_params_hmac('key', 'app', 'GET', '/x', {'a': '1'}, b'body', timestamp=_TEST_TIMESTAMP)

        assert ts1 == ts2 == _TEST_TIMESTAMP
        assert sig1 == sig2

    def test_default_timestamp_is_now(self):
        from src.service.omega_api import OmegaAPI

        before = int(time.time())
        timestamp, _ = OmegaAPI.sign_params_hmac('key', 'app', 'GET', '/x', {})
        after = int(time.time())

        assert before <= timestamp <= after

    def test_method_case_insensitive(self):
        from src.service.omega_api import OmegaAPI

        _, sig_lower = OmegaAPI.sign_params_hmac('key', 'app', 'get', '/x', {}, timestamp=_TEST_TIMESTAMP)
        _, sig_upper = OmegaAPI.sign_params_hmac('key', 'app', 'GET', '/x', {}, timestamp=_TEST_TIMESTAMP)

        assert sig_lower == sig_upper

    @pytest.mark.parametrize(
        'override',
        [
            {'key': 'other_key'},
            {'app_name': 'other_app'},
            {'method': 'POST'},
            {'path': '/other'},
            {'params': {'a': '2'}},
            {'body': b'other'},
            {'timestamp': _TEST_TIMESTAMP + 1},
        ],
    )
    def test_signature_varies_with_any_component(self, override: dict[str, Any]):
        """签名消息任一组成部分变化都应产生不同签名"""
        from src.service.omega_api import OmegaAPI

        base = {
            'key': 'key',
            'app_name': 'app',
            'method': 'GET',
            'path': '/x',
            'params': {'a': '1'},
            'body': b'body',
            'timestamp': _TEST_TIMESTAMP,
        }
        _, sig_base = OmegaAPI.sign_params_hmac(**base)
        _, sig_changed = OmegaAPI.sign_params_hmac(**(base | override))

        assert sig_base != sig_changed

    def test_token_format(self):
        from src.service.omega_api import OmegaAPI

        _, token = OmegaAPI.sign_params_hmac('key', 'app', 'GET', '/x', {})

        assert len(token) == 64
        assert all(c in '0123456789abcdef' for c in token)

    def test_params_order_independent(self):
        """参数顺序不影响签名(规范化排序后签名一致)"""
        from src.service.omega_api import OmegaAPI

        _, sig1 = OmegaAPI.sign_params_hmac('key', 'app', 'GET', '/x', {'b': '2', 'a': '1'}, timestamp=_TEST_TIMESTAMP)
        _, sig2 = OmegaAPI.sign_params_hmac('key', 'app', 'GET', '/x', {'a': '1', 'b': '2'}, timestamp=_TEST_TIMESTAMP)

        assert sig1 == sig2

    def test_multi_value_params_not_collapsed(self):
        """多值参数完整参与签名, 不坍缩为单值(与坍缩后的单值 dict 签名不同)"""
        from src.service.omega_api import OmegaAPI

        _, sig_multi = OmegaAPI.sign_params_hmac(
            'key', 'app', 'GET', '/x', QueryParams('a=1&a=2&b=3'), timestamp=_TEST_TIMESTAMP
        )
        _, sig_collapsed = OmegaAPI.sign_params_hmac(
            'key', 'app', 'GET', '/x', {'a': '2', 'b': '3'}, timestamp=_TEST_TIMESTAMP
        )

        assert sig_multi != sig_collapsed


class TestVerifyParamsHmac:
    """verify_params_hmac 验签测试"""

    def test_valid_signature(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        from src.service.omega_api import OmegaAPI

        api = omega_api_factory()
        timestamp, token = OmegaAPI.sign_params_hmac(
            _get_master_key(), api._app_name, 'GET', '/test', {'a': '1'}, b'body', timestamp=_TEST_TIMESTAMP
        )

        assert api.verify_params_hmac(token, timestamp, 'GET', '/test', {'a': '1'}, b'body') is True

    def test_timestamp_accepts_str(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        from src.service.omega_api import OmegaAPI

        api = omega_api_factory()
        timestamp, token = OmegaAPI.sign_params_hmac(
            _get_master_key(), api._app_name, 'GET', '/test', {}, timestamp=_TEST_TIMESTAMP
        )

        assert api.verify_params_hmac(token, str(timestamp), 'GET', '/test', {}) is True

    def test_method_case_insensitive(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        from src.service.omega_api import OmegaAPI

        api = omega_api_factory()
        timestamp, token = OmegaAPI.sign_params_hmac(
            _get_master_key(), api._app_name, 'get', '/test', {}, timestamp=_TEST_TIMESTAMP
        )

        assert api.verify_params_hmac(token, timestamp, 'GET', '/test', {}) is True

    @pytest.mark.parametrize(
        ('signature', 'timestamp', 'method', 'path', 'params', 'body'),
        [
            ('0' * 64, _TEST_TIMESTAMP, 'GET', '/test', {'a': '1'}, b''),
            (None, _TEST_TIMESTAMP + 1, 'GET', '/test', {'a': '1'}, b''),
            (None, _TEST_TIMESTAMP, 'POST', '/test', {'a': '1'}, b''),
            (None, _TEST_TIMESTAMP, 'GET', '/other', {'a': '1'}, b''),
            (None, _TEST_TIMESTAMP, 'GET', '/test', {'a': '2'}, b''),
            (None, _TEST_TIMESTAMP, 'GET', '/test', {'a': '1'}, b'other'),
        ],
    )
    def test_invalid_signature_rejected(
            self,
            omega_api_factory: Callable[..., 'OmegaAPI'],
            signature: str | None,
            timestamp: int,
            method: str,
            path: str,
            params: dict[str, str],
            body: bytes,
    ):
        """任一组成部分被篡改或签名本身错误均应判定为非法"""
        from src.service.omega_api import OmegaAPI

        api = omega_api_factory()
        _, valid_token = OmegaAPI.sign_params_hmac(
            _get_master_key(), api._app_name, 'GET', '/test', {'a': '1'}, b'', timestamp=_TEST_TIMESTAMP
        )

        assert api.verify_params_hmac(signature or valid_token, timestamp, method, path, params, body) is False

    def test_signature_from_other_app_rejected(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        """其他 app 的签名(子密钥不同)对本 app 无效"""
        from src.service.omega_api import OmegaAPI

        api = omega_api_factory()
        timestamp, token = OmegaAPI.sign_params_hmac(
            _get_master_key(), 'other_app', 'GET', '/test', {}, timestamp=_TEST_TIMESTAMP
        )

        assert api.verify_params_hmac(token, timestamp, 'GET', '/test', {}) is False

    def test_wrong_master_key_signature_rejected(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        """使用错误主密钥生成的签名无效"""
        from src.service.omega_api import OmegaAPI

        api = omega_api_factory()
        timestamp, token = OmegaAPI.sign_params_hmac(
            'wrong_master_key', api._app_name, 'GET', '/test', {}, timestamp=_TEST_TIMESTAMP
        )

        assert api.verify_params_hmac(token, timestamp, 'GET', '/test', {}) is False

    def test_non_ascii_signature_rejected(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        """非 ASCII 签名应判定为非法而非抛出 TypeError(compare_digest 限制)"""
        api = omega_api_factory()

        assert api.verify_params_hmac('é' * 64, _TEST_TIMESTAMP, 'GET', '/test', {}) is False

    async def test_async_verify_consistent(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        from src.service.omega_api import OmegaAPI

        api = omega_api_factory()
        timestamp, token = OmegaAPI.sign_params_hmac(
            _get_master_key(), api._app_name, 'GET', '/test', {}, timestamp=_TEST_TIMESTAMP
        )

        assert await api.async_verify_params_hmac(token, timestamp, 'GET', '/test', {}) is True
        assert await api.async_verify_params_hmac('0' * 64, timestamp, 'GET', '/test', {}) is False


class TestOmegaAPIInit:
    """OmegaAPI 初始化测试"""

    def test_basic_attributes(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        api = omega_api_factory()

        assert api._app_name.startswith('omega_test_')
        assert isinstance(api.root_url, str)
        assert api.color_log_prefix

    def test_root_url(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        from nonebot import get_driver

        api = omega_api_factory()
        config = get_driver().config
        host = str(config.host)
        if host in ('0.0.0.0', '127.0.0.1'):
            host = 'localhost'

        assert api.root_url == f'http://{host}:{config.port}/{api._app_name}'

    def test_root_url_with_https(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        api = omega_api_factory(use_https=True)

        assert api.root_url.startswith('https://')

    def test_root_url_with_access_domain(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        """反代场景(access_domain 非空)不拼接本地端口"""
        api = omega_api_factory(access_domain='api.example.com')

        assert api.root_url == f'http://api.example.com/{api._app_name}'

    def test_root_url_with_access_domain_and_https(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        api = omega_api_factory(access_domain='api.example.com', use_https=True)

        assert api.root_url == f'https://api.example.com/{api._app_name}'

    def test_duplicate_app_name_rejected(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        from src.service.omega_api import OmegaAPI

        omega_api_factory(app_name='omega_test_dup')

        with pytest.raises(ValueError, match='already registered'):
            OmegaAPI('omega_test_dup')

    @pytest.mark.parametrize('app_name', ['', '中文', '///', '   ', '/ /'])
    def test_empty_normalized_app_name_rejected(self, app_name: str):
        """归一化后为空的 app_name 会导致子应用挂载到根路径, 必须拒绝"""
        from src.service.omega_api import OmegaAPI

        with pytest.raises(ValueError, match='Invalid app_name'):
            OmegaAPI(app_name)

    def test_fastapi_driver_required(self, monkeypatch: pytest.MonkeyPatch):
        import src.service.omega_api.api as api_module
        from src.service.omega_api import OmegaAPI

        fake_driver = SimpleNamespace(type='~aiohttp', config=SimpleNamespace(host='127.0.0.1', port=8080))
        monkeypatch.setattr(api_module, 'get_driver', lambda: fake_driver)

        with pytest.raises(RuntimeError, match='fastapi driver not enabled'):
            OmegaAPI('omega_test_no_fastapi')


class TestRouteRegistration:
    """路由注册测试"""

    def test_register_route_methods(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        api = omega_api_factory()

        @api.register_get_route('/x')
        async def _get_handler() -> dict[str, bool]:
            return {'ok': True}

        @api.register_post_route('/x')
        async def _post_handler() -> dict[str, bool]:
            return {'ok': True}

        @api.register_put_route('/x')
        async def _put_handler() -> dict[str, bool]:
            return {'ok': True}

        @api.register_delete_route('/x')
        async def _delete_handler() -> dict[str, bool]:
            return {'ok': True}

        registered = {(route.path, method) for route in api._app.routes for method in getattr(route, 'methods', set())}
        assert ('/x', 'GET') in registered
        assert ('/x', 'POST') in registered
        assert ('/x', 'PUT') in registered
        assert ('/x', 'DELETE') in registered

    def test_decorator_returns_original_function(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        api = omega_api_factory()

        async def _handler() -> None:
            pass

        result = api.register_get_route('/y')(_handler)

        assert result is _handler

    def test_non_coroutine_function_rejected(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        api = omega_api_factory()

        with pytest.raises(ValueError, match='coroutine function'):
            api.register_get_route('/bad')(lambda: None)

    def test_route_path_normalized(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        api = omega_api_factory()

        @api.register_get_route('//abc/')
        async def _handler() -> dict[str, bool]:
            return {'ok': True}

        assert any(route.path == '/abc' for route in api._app.routes)

    def test_router_prefix_and_registration(self):
        from src.service.omega_api import OmegaAPIRouter

        router = OmegaAPIRouter(prefix='/v1')

        @router.register_get_route('/info')
        async def _handler() -> dict[str, bool]:
            return {'ok': True}

        assert any(route.path == '/v1/info' for route in router.routes)

    def test_router_display_url_and_log_prefix(self):
        from src.service.omega_api import OmegaAPIRouter

        router = OmegaAPIRouter(prefix='/v1')

        assert router._route_display_url('/info') == '/v1/info'
        assert '/v1' in router.color_log_prefix

    def test_router_non_coroutine_function_rejected(self):
        from src.service.omega_api import OmegaAPIRouter

        router = OmegaAPIRouter()

        with pytest.raises(ValueError, match='coroutine function'):
            router.register_post_route('/bad')(lambda: None)


class TestTokenVerifyMiddleware:
    """Token 校验中间件测试(直打子应用, 签名 path 不含挂载前缀)"""

    async def test_disabled_verify_allows_plain_request(self, open_api: 'OmegaAPI'):
        async with AsyncClient(transport=ASGITransport(app=open_api._app), base_url='http://testserver') as client:
            resp = await client.get('/test')

        assert resp.status_code == 200
        assert resp.json() == {'ok': True}

    async def test_missing_app_header_rejected(self, secured_client: AsyncClient):
        resp = await secured_client.get('/test')

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Request App'}

    async def test_wrong_app_header_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        from src.service.omega_api.consts import APP_HEADER_KEY

        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test')
        headers[APP_HEADER_KEY] = 'other_app'
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Request App'}

    async def test_missing_timestamp_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        from src.service.omega_api.consts import APP_HEADER_KEY

        resp = await secured_client.get('/test', headers={APP_HEADER_KEY: secured_api._app_name})

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Timestamp Not Provided'}

    async def test_non_decimal_timestamp_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test')
        headers['X-OmegaAPI-Timestamp'] = 'not-a-number'
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Timestamp'}

    async def test_overlong_timestamp_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        """超长时间戳数字串直接拒绝(防 int() 异常/超大整数)"""
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test')
        headers['X-OmegaAPI-Timestamp'] = '1' * 17
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Timestamp'}

    async def test_expired_timestamp_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        expired_timestamp = int(time.time()) - 3600
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test', timestamp=expired_timestamp)
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Timestamp'}

    async def test_timestamp_at_window_edge_allowed(
            self, secured_client: AsyncClient, secured_api: 'OmegaAPI', monkeypatch: pytest.MonkeyPatch,
    ):
        """偏差恰好处于窗口内的时间戳应放行(放大窗口避免竞态)"""
        import src.service.omega_api.api as api_module

        monkeypatch.setattr(api_module, '_TIMESTAMP_EXPIRE_SECONDS', 100)
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test', timestamp=int(time.time()) - 95)
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 200

    async def test_timestamp_beyond_window_rejected(
            self, secured_client: AsyncClient, secured_api: 'OmegaAPI', monkeypatch: pytest.MonkeyPatch,
    ):
        import src.service.omega_api.api as api_module

        monkeypatch.setattr(api_module, '_TIMESTAMP_EXPIRE_SECONDS', 100)
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test', timestamp=int(time.time()) - 105)
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Timestamp'}

    async def test_future_timestamp_within_window_allowed(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        """未来时间戳在窗口内允许(容忍客户端时钟偏差)"""
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test', timestamp=int(time.time()) + 20)
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 200

    async def test_missing_token_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        from src.service.omega_api.consts import APP_HEADER_KEY, TIMESTAMP_HEADER_KEY

        headers = {APP_HEADER_KEY: secured_api._app_name, TIMESTAMP_HEADER_KEY: str(int(time.time()))}
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Token Not Provided'}

    async def test_wrong_token_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test')
        headers['X-OmegaAPI-Token'] = '0' * 64
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Token'}

    async def test_non_ascii_token_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        """非 ASCII Token 应正常返回 403 而非触发 500

        httpx 默认以 ASCII 编码 header 值, 需用 bytes 形式(latin-1)构造非 ASCII Token 头,
        模拟真实客户端可送达服务端的非 ASCII header
        """
        signed = _make_signed_headers(secured_api._app_name, 'GET', '/test')
        byte_headers = [
            (key.encode(), b'\xe9' * 64 if key == 'X-OmegaAPI-Token' else value.encode())
            for key, value in signed.items()
        ]
        resp = await secured_client.get('/test', headers=byte_headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Token'}

    async def test_valid_get_request(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test')
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 200
        assert resp.json() == {'ok': True}

    async def test_valid_post_with_body_and_downstream_body_readable(
            self, secured_client: AsyncClient, secured_api: 'OmegaAPI',
    ):
        """合法签名 POST 请求应放行, 且中间件读取后下游 handler 仍能读取请求体"""
        body = '请求体 content'.encode()
        headers = _make_signed_headers(secured_api._app_name, 'POST', '/echo', body=body)
        resp = await secured_client.post('/echo', headers=headers, content=body)

        assert resp.status_code == 200
        assert resp.json() == {'echo': '请求体 content'}

    async def test_tampered_body_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        headers = _make_signed_headers(secured_api._app_name, 'POST', '/echo', body=b'original')
        resp = await secured_client.post('/echo', headers=headers, content=b'tampered')

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Token'}

    async def test_tampered_query_params_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test', params={'a': '1'})
        resp = await secured_client.get('/test', params={'a': '2'}, headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Token'}

    async def test_wrong_path_signature_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/other')
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Token'}

    async def test_wrong_method_signature_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        headers = _make_signed_headers(secured_api._app_name, 'POST', '/test')
        resp = await secured_client.get('/test', headers=headers)

        assert resp.status_code == 403
        assert resp.json() == {'error': True, 'message': 'Invalid Token'}

    async def test_multi_value_query_params_signed(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        """多值 query 参数(?a=1&a=2)完整参与签名"""
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test', params=QueryParams('a=1&a=2'))
        resp = await secured_client.get('/test', params=[('a', '1'), ('a', '2')], headers=headers)

        assert resp.status_code == 200

    async def test_replayed_token_rejected(self, secured_client: AsyncClient, secured_api: 'OmegaAPI'):
        """相同签名在时间戳有效期内二次使用应被拒绝(防重放)"""
        headers = _make_signed_headers(secured_api._app_name, 'GET', '/test')

        first = await secured_client.get('/test', headers=headers)
        second = await secured_client.get('/test', headers=headers)

        assert first.status_code == 200
        assert second.status_code == 403
        assert second.json() == {'error': True, 'message': 'Replayed Token'}

    async def test_oversized_content_length_rejected(
            self, secured_client: AsyncClient, secured_api: 'OmegaAPI', monkeypatch: pytest.MonkeyPatch,
    ):
        import src.service.omega_api.api as api_module

        monkeypatch.setattr(api_module, '_REQUEST_BODY_MAX_SIZE', 8)
        body = b'x' * 16
        headers = _make_signed_headers(secured_api._app_name, 'POST', '/echo', body=body)
        resp = await secured_client.post('/echo', headers=headers, content=body)

        assert resp.status_code == 413
        assert resp.json() == {'error': True, 'message': 'Payload Too Large'}

    async def test_body_at_limit_allowed(
            self, secured_client: AsyncClient, secured_api: 'OmegaAPI', monkeypatch: pytest.MonkeyPatch,
    ):
        """恰好等于上限的请求体应放行(仅超出才拒绝)"""
        import src.service.omega_api.api as api_module

        monkeypatch.setattr(api_module, '_REQUEST_BODY_MAX_SIZE', 16)
        body = b'x' * 16
        headers = _make_signed_headers(secured_api._app_name, 'POST', '/echo', body=body)
        resp = await secured_client.post('/echo', headers=headers, content=body)

        assert resp.status_code == 200

    async def test_oversized_streamed_body_rejected(
            self, secured_client: AsyncClient, secured_api: 'OmegaAPI', monkeypatch: pytest.MonkeyPatch,
    ):
        """无 Content-Length 的流式请求体超限时由流式读取强制拒绝"""
        import src.service.omega_api.api as api_module

        monkeypatch.setattr(api_module, '_REQUEST_BODY_MAX_SIZE', 8)
        body = b'x' * 16
        headers = _make_signed_headers(secured_api._app_name, 'POST', '/echo', body=body)

        async def _body_stream() -> AsyncGenerator[bytes, None]:
            yield body

        resp = await secured_client.post('/echo', headers=headers, content=_body_stream())

        assert resp.status_code == 413
        assert resp.json() == {'error': True, 'message': 'Payload Too Large'}

    async def test_end_to_end_through_mounted_app(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        """经主应用挂载的完整链路: 中间件看到的 path 含 /{app_name} 前缀, 签名需使用完整路径"""
        from nonebot import get_app

        api = omega_api_factory(enable_token_verify=True)

        @api.register_get_route('/test')
        async def _get_handler() -> dict[str, bool]:
            return {'ok': True}

        @api.register_post_route('/echo')
        async def _post_handler(request: Request) -> dict[str, str]:
            return {'echo': (await request.body()).decode(), 'query': str(request.url.query)}

        async with AsyncClient(transport=ASGITransport(app=get_app()), base_url='http://testserver') as client:
            get_path = f'/{api._app_name}/test'
            get_headers = _make_signed_headers(api._app_name, 'GET', get_path)
            get_resp = await client.get(get_path, headers=get_headers)

            post_path = f'/{api._app_name}/echo'
            post_params = {'a': '1', 'b': '2'}
            post_body = b'{"foo": "bar"}'
            post_headers = _make_signed_headers(api._app_name, 'POST', post_path, post_params, post_body)
            post_resp = await client.post(post_path, params=post_params, headers=post_headers, content=post_body)

        assert get_resp.status_code == 200
        assert get_resp.json() == {'ok': True}
        assert post_resp.status_code == 200
        assert post_resp.json() == {'echo': '{"foo": "bar"}', 'query': 'a=1&b=2'}

    async def test_open_app_through_mounted_app(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        """未启用签名校验的 app 经主应用挂载后无头请求直接放行"""
        from nonebot import get_app

        api = omega_api_factory()

        @api.register_get_route('/ping')
        async def _handler() -> dict[str, bool]:
            return {'pong': True}

        async with AsyncClient(transport=ASGITransport(app=get_app()), base_url='http://testserver') as client:
            resp = await client.get(f'/{api._app_name}/ping')

        assert resp.status_code == 200
        assert resp.json() == {'pong': True}


class TestReplayCache:
    """防重放签名缓存测试(实例级)"""

    def test_first_use_accepted_second_rejected(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        api = omega_api_factory()

        assert api._is_replayed_signature('sig-a') is False
        assert api._is_replayed_signature('sig-a') is True

    def test_different_signatures_independent(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        api = omega_api_factory()

        assert api._is_replayed_signature('sig-a') is False
        assert api._is_replayed_signature('sig-b') is False
        assert api._is_replayed_signature('sig-b') is True

    def test_full_cache_rejects_new_signature(
            self, omega_api_factory: Callable[..., 'OmegaAPI'], monkeypatch: pytest.MonkeyPatch,
    ):
        """缓存达到容量阈值且无过期条目时拒绝新签名(fail-closed, 防缓存撑爆)"""
        import src.service.omega_api.api as api_module

        monkeypatch.setattr(api_module, '_USED_SIGNATURES_MAX_SIZE', 2)
        api = omega_api_factory()

        assert api._is_replayed_signature('sig-a') is False
        assert api._is_replayed_signature('sig-b') is False
        assert api._is_replayed_signature('sig-c') is True

        # 缓存有界: 被拒绝的新签名不入缓存
        cache = getattr(api, '_OmegaAPI__used_signatures')
        assert len(cache) == 2
        assert 'sig-c' not in cache

    def test_full_cache_cleans_expired_entries(
            self, omega_api_factory: Callable[..., 'OmegaAPI'], monkeypatch: pytest.MonkeyPatch,
    ):
        """缓存满时先清理过期条目, 清理后有容量则正常接受"""
        import src.service.omega_api.api as api_module

        monkeypatch.setattr(api_module, '_USED_SIGNATURES_MAX_SIZE', 2)
        api = omega_api_factory()
        api._is_replayed_signature('sig-a')
        api._is_replayed_signature('sig-b')

        cache = getattr(api, '_OmegaAPI__used_signatures')
        cache['sig-a'] = time.monotonic() - 1

        assert api._is_replayed_signature('sig-c') is False
        assert 'sig-a' not in cache
        assert len(cache) == 2


class TestMountRouter:
    """mount_router 挂载测试"""

    def test_mount_router_returns_router(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        from src.service.omega_api import OmegaAPIRouter

        api = omega_api_factory()
        router = OmegaAPIRouter(prefix='/v1')

        assert api.mount_router(router, prefix='/api') is router

    async def test_mounted_router_accessible(self, omega_api_factory: Callable[..., 'OmegaAPI']):
        from src.service.omega_api import OmegaAPIRouter

        api = omega_api_factory()
        router = OmegaAPIRouter(prefix='/v1')

        @router.register_get_route('/info')
        async def _handler() -> dict[str, bool]:
            return {'ok': True}

        api.mount_router(router, prefix='/api')

        async with AsyncClient(transport=ASGITransport(app=api._app), base_url='http://testserver') as client:
            resp = await client.get('/api/v1/info')

        assert resp.status_code == 200
        assert resp.json() == {'ok': True}

    @pytest.mark.parametrize('method', ['GET', 'POST', 'PUT', 'DELETE'])
    async def test_mounted_router_all_methods_accessible(
            self, omega_api_factory: Callable[..., 'OmegaAPI'], method: str,
    ):
        """mount_router 挂载后四种方法注册的路由均可访问"""
        from src.service.omega_api import OmegaAPIRouter

        api = omega_api_factory()
        router = OmegaAPIRouter(prefix='/r')

        @router.register_get_route('/x')
        async def _get_handler() -> dict[str, str]:
            return {'m': 'GET'}

        @router.register_post_route('/x')
        async def _post_handler() -> dict[str, str]:
            return {'m': 'POST'}

        @router.register_put_route('/x')
        async def _put_handler() -> dict[str, str]:
            return {'m': 'PUT'}

        @router.register_delete_route('/x')
        async def _delete_handler() -> dict[str, str]:
            return {'m': 'DELETE'}

        api.mount_router(router)

        async with AsyncClient(transport=ASGITransport(app=api._app), base_url='http://testserver') as client:
            resp = await client.request(method, '/r/x')

        assert resp.status_code == 200
        assert resp.json() == {'m': method}


class TestMountStaticPath:
    """mount_static_path 静态文件挂载测试"""

    async def test_static_file_served(self, omega_api_factory: Callable[..., 'OmegaAPI'], tmp_path):
        from src.resource import AnyResource

        tmp_path.joinpath('hello.txt').write_text('static-content', encoding='utf-8')
        api = omega_api_factory()
        api.mount_static_path(AnyResource(tmp_path), path='static')

        async with AsyncClient(transport=ASGITransport(app=api._app), base_url='http://testserver') as client:
            resp = await client.get('/static/hello.txt')

        assert resp.status_code == 200
        assert resp.text == 'static-content'

    async def test_prefix_and_path_normalized(self, omega_api_factory: Callable[..., 'OmegaAPI'], tmp_path):
        from src.resource import AnyResource

        tmp_path.joinpath('hello.txt').write_text('static-content', encoding='utf-8')
        api = omega_api_factory()
        api.mount_static_path(AnyResource(tmp_path), path='/sub/', prefix='/pfx/')

        async with AsyncClient(transport=ASGITransport(app=api._app), base_url='http://testserver') as client:
            resp = await client.get('/pfx/sub/hello.txt')

        assert resp.status_code == 200
        assert resp.text == 'static-content'

    def test_empty_path_and_prefix_rejected(self, omega_api_factory: Callable[..., 'OmegaAPI'], tmp_path):
        from src.resource import AnyResource

        api = omega_api_factory()

        with pytest.raises(ValueError, match='can not both be empty'):
            api.mount_static_path(AnyResource(tmp_path))

    def test_missing_dir_rejected(self, omega_api_factory: Callable[..., 'OmegaAPI'], tmp_path):
        from src.resource import AnyResource, ResourceNotFolderError

        api = omega_api_factory()

        with pytest.raises(ResourceNotFolderError):
            api.mount_static_path(AnyResource(tmp_path / 'missing'), path='static')


class TestReadRequestBody:
    """_read_request_body 私有行为测试(钉住与 Starlette request._body 的耦合契约, 检测上游行为漂移)"""

    @staticmethod
    def _make_stream_request(chunks: list[bytes]) -> Request:
        """构造携带指定请求体分块的 Request(最小 ASGI scope + 自制 receive 通道)"""
        messages = [{'type': 'http.request', 'body': chunk, 'more_body': True} for chunk in chunks]
        messages.append({'type': 'http.request', 'body': b'', 'more_body': False})

        async def _receive() -> dict[str, Any]:
            return messages.pop(0)

        return Request({'type': 'http', 'method': 'POST', 'path': '/', 'headers': []}, _receive)

    async def test_read_body_normal_and_cached(self):
        from src.service.omega_api import OmegaAPI

        request = self._make_stream_request([b'hello ', b'world'])

        body = await OmegaAPI._read_request_body(request, 1024)

        assert body == b'hello world'
        # 读取成功后缓存到 request._body, 下游 request.body() 行为一致
        assert request._body == b'hello world'
        assert await request.body() == b'hello world'

    async def test_read_body_at_limit_allowed(self):
        """总长度恰好等于上限时正常读取(仅超出才拒绝)"""
        from src.service.omega_api import OmegaAPI

        request = self._make_stream_request([b'x' * 8])

        assert await OmegaAPI._read_request_body(request, 8) == b'x' * 8

    async def test_read_body_over_limit_returns_none(self):
        from src.service.omega_api import OmegaAPI

        request = self._make_stream_request([b'x' * 8, b'x' * 8])

        assert await OmegaAPI._read_request_body(request, 8) is None

    async def test_read_body_empty(self):
        from src.service.omega_api import OmegaAPI

        request = self._make_stream_request([])

        assert await OmegaAPI._read_request_body(request, 8) == b''
        assert await request.body() == b''
