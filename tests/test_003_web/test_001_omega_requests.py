"""
@Author         : Ailitonia
@Date           : 2026/9/12 18:12
@FileName       : test_001_omega_requests
@Project        : omega-miya
@Description    : OmegaRequests 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import contextlib
import hashlib
import os
import socket
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn

if TYPE_CHECKING:
    from src.resource import AnyResource

_STREAM_CHUNKS = [b'alpha', b'-beta', b'-game']
"""流式测试服务端输出的固定分块"""

_STREAM_PAYLOAD = b''.join(_STREAM_CHUNKS)
"""流式测试完整负载, 共 15 字节, chunk_size=4 时驱动重组块为 [4, 4, 4, 3]"""

_DOWNLOAD_PAYLOAD = bytes(range(256)) * 64
"""下载测试固定负载, 共 16 KiB 确定性内容"""

_LINES_EXPECTED = ['first', 'second', 'third', 'fourth', '', 'last-no-newline']
"""行迭代测试期望结果, 对应混合 \\n / \\r\\n / \\r 行结尾与无换行残留行"""


def _make_file(tmp_path: Path, name: str) -> 'AnyResource':
    """在临时目录构造下载目标文件资源"""
    from src.resource import AnyResource

    return AnyResource(tmp_path, name)


def _new_token() -> str:
    """生成测试用例隔离 token(用于服务端按用例计数/记录请求头)"""
    return uuid.uuid4().hex[:8]


async def _line_chunks(chunks: list[Any]) -> AsyncGenerator[Any, None]:
    """构造合成流式响应生成器(精确控制分块边界, 不经网络与驱动重组块)"""
    from nonebot.drivers import Response

    for chunk in chunks:
        yield Response(200, content=chunk)


@pytest.fixture(scope='session')
def unused_port() -> int:
    """获取一个当前空闲(已关闭)的本地端口, 用于连接拒绝/代理失败用例"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope='session')
async def test_server(nonebug_init: None) -> AsyncGenerator[SimpleNamespace, None]:
    """基于 OmegaAPI 子应用 + uvicorn 真实端口的测试 HTTP/WebSocket 服务端

    nonebug 的 app.test_server() 是进程内 ASGI client, 无法承载 nonebot aiohttp 驱动发起的真实 TCP 请求,
    故此处将 OmegaAPI 子应用直接交由 uvicorn 监听 127.0.0.1 随机端口, 供 OmegaRequests 真实访问

    依赖 session 级 nonebug_init 夹具作为 NoneBot 初始化与 lifespan 就绪屏障
    """
    import nonebot
    from fastapi import Request as FastAPIRequest
    from fastapi import Response as FastAPIResponse
    from fastapi import WebSocket as FastAPIWebSocket
    from fastapi.responses import PlainTextResponse, StreamingResponse
    from starlette.routing import Mount

    from src.service.omega_api import OmegaAPI
    from src.service.omega_api.api import _REGISTERED_APP
    from src.utils.omega_requests.config import omega_requests_config

    # 测试环境配置默认启用代理(.env.test omega_requests_enable_proxy=True), 会话内强制禁用,
    # 保证集成用例直连本地测试服务端; 代理行为由 TestProxy 经 monkeypatch 逐用例覆盖
    saved_enable_proxy = omega_requests_config.omega_requests_enable_proxy
    omega_requests_config.omega_requests_enable_proxy = False

    # aiohttp 驱动 trust_env=True 会读取 HTTP(S)_PROXY 环境变量, 此处确保本地请求不被系统代理劫持
    saved_no_proxy = {key: os.environ.get(key) for key in ('NO_PROXY', 'no_proxy')}
    os.environ['NO_PROXY'] = '127.0.0.1,localhost'
    os.environ['no_proxy'] = '127.0.0.1,localhost'

    api = OmegaAPI(f'omega_requests_test_{uuid.uuid4().hex[:8]}')
    state = SimpleNamespace(
        counters=defaultdict(int),  # 按 key 计数请求次数
        range_headers=defaultdict(list),  # 按 key 记录每次请求携带的 Range 头
        custom_headers=defaultdict(list),  # 按 key 记录每次请求携带的 x-test-header 头
    )

    def _record(key: str, request: FastAPIRequest) -> None:
        state.counters[key] += 1
        state.range_headers[key].append(request.headers.get('range'))
        state.custom_headers[key].append(request.headers.get('x-test-header'))

    @api.register_get_route('/get')
    async def _get_echo(request: FastAPIRequest):
        return {
            'params': [list(x) for x in request.query_params.multi_items()],
            'headers': dict(request.headers),
        }

    @api.register_post_route('/post')
    async def _post_echo(request: FastAPIRequest):
        return FastAPIResponse(
            content=await request.body(),
            media_type='application/octet-stream',
            headers={'X-Echo-Content-Type': request.headers.get('content-type', '')},
        )

    @api.register_post_route('/post_json')
    async def _post_json_echo(request: FastAPIRequest):
        return {'echo': await request.json()}

    @api.register_put_route('/put')
    async def _put():
        return {'ok': True, 'method': 'PUT'}

    @api.register_delete_route('/delete')
    async def _delete():
        return {'ok': True, 'method': 'DELETE'}

    @api.register_get_route('/status/{code}')
    async def _status(code: int, token: str = ''):
        state.counters[f'status:{code}:{token}'] += 1
        return PlainTextResponse(f'status {code}', status_code=code)

    @api.register_get_route('/status_empty/{code}')
    async def _status_empty(code: int):
        # 空响应体的错误响应: 流式请求不产生任何分块, 用于覆盖 stream_download 零分块核验路径
        return FastAPIResponse(status_code=code)

    @api.register_get_route('/stream')
    async def _stream_get():
        async def _gen():
            for chunk in _STREAM_CHUNKS:
                yield chunk

        return StreamingResponse(_gen())

    @api.register_post_route('/stream')
    async def _stream_post():
        async def _gen():
            for chunk in _STREAM_CHUNKS:
                yield chunk

        return StreamingResponse(_gen())

    @api.register_get_route('/lines')
    async def _lines_get():
        async def _gen():
            yield 'first\nsec'
            yield 'ond\r\nthird\r'
            yield 'fourth\n\nlast-no-newline'

        return StreamingResponse(_gen())

    @api.register_post_route('/lines')
    async def _lines_post():
        async def _gen():
            yield 'first\nsec'
            yield 'ond\r\nthird\r'
            yield 'fourth\n\nlast-no-newline'

        return StreamingResponse(_gen())

    @api.register_get_route('/stream_stall')
    async def _stream_stall():
        async def _gen():
            yield b'first-chunk'
            await asyncio.sleep(3)
            yield b'second-chunk'

        return StreamingResponse(_gen())

    @api.register_get_route('/slow/{token}')
    async def _slow(token: str):
        state.counters[f'slow:{token}'] += 1
        await asyncio.sleep(3)
        return {'ok': True}

    @api.register_get_route('/flaky/{token}')
    async def _flaky(token: str, fail: int = 2):
        state.counters[f'flaky:{token}'] += 1
        if state.counters[f'flaky:{token}'] <= fail:
            await asyncio.sleep(3)
        return {'attempt': state.counters[f'flaky:{token}']}

    @api.register_get_route('/download')
    async def _download():
        return FastAPIResponse(content=_DOWNLOAD_PAYLOAD, media_type='application/octet-stream')

    @api.register_get_route('/download_empty')
    async def _download_empty():
        return FastAPIResponse(content=b'', media_type='application/octet-stream')

    @api.register_get_route('/download_range/{token}')
    async def _download_range(request: FastAPIRequest, token: str):
        key = f'range:{token}'
        _record(key, request)
        range_header = request.headers.get('range')
        if range_header is not None and range_header.startswith('bytes='):
            start = int(range_header.removeprefix('bytes=').split('-')[0])
            if start >= len(_DOWNLOAD_PAYLOAD):
                return FastAPIResponse(status_code=416)
            return FastAPIResponse(
                content=_DOWNLOAD_PAYLOAD[start:],
                status_code=206,
                media_type='application/octet-stream',
                headers={'Content-Range': f'bytes {start}-{len(_DOWNLOAD_PAYLOAD) - 1}/{len(_DOWNLOAD_PAYLOAD)}'},
            )
        return FastAPIResponse(content=_DOWNLOAD_PAYLOAD, media_type='application/octet-stream')

    @api.register_get_route('/download_no_range/{token}')
    async def _download_no_range(request: FastAPIRequest, token: str):
        # 忽略 Range 头恒返回 200 全量内容, 用于断点续传不支持时的重下场景
        _record(f'no_range:{token}', request)
        return FastAPIResponse(content=_DOWNLOAD_PAYLOAD, media_type='application/octet-stream')

    @api.register_get_route('/download_206_empty/{token}')
    async def _download_206_empty(request: FastAPIRequest, token: str):
        # 恒返回 206 空响应体, 用于断点续传余量为零的核验路径
        _record(f'206_empty:{token}', request)
        return FastAPIResponse(
            status_code=206, headers={'Content-Range': f'bytes */{len(_DOWNLOAD_PAYLOAD)}'}
        )

    @api._app.websocket('/ws')
    async def _ws_echo(websocket: FastAPIWebSocket):
        await websocket.accept()
        message = await websocket.receive()
        if message.get('text') is not None:
            await websocket.send_text(f'echo:{message['text']}')
        elif message.get('bytes') is not None:
            await websocket.send_bytes(b'echo:' + message['bytes'])

    config = uvicorn.Config(app=api._app, host='127.0.0.1', port=0, log_level='warning')
    server = uvicorn.Server(config)
    serve_task = asyncio.create_task(server.serve())
    for _ in range(200):
        if server.started:
            break
        await asyncio.sleep(0.05)
    else:
        serve_task.cancel()
        raise RuntimeError('OmegaRequests test server failed to start')
    port = server.servers[0].sockets[0].getsockname()[1]

    try:
        yield SimpleNamespace(base_url=f'http://127.0.0.1:{port}', api=api, state=state)
    finally:
        omega_requests_config.omega_requests_enable_proxy = saved_enable_proxy

        server.force_exit = True
        server.should_exit = True
        try:
            await asyncio.wait_for(serve_task, timeout=10)
        except (TimeoutError, asyncio.CancelledError):
            serve_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await serve_task

        for key, value in saved_no_proxy.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        _REGISTERED_APP.discard(api._app_name)
        nonebot_app = nonebot.get_app()
        for route in list(nonebot_app.router.routes):
            if isinstance(route, Mount) and route.path == f'/{api._app_name}':
                nonebot_app.router.routes.remove(route)


class TestModuleContract:
    """模块导出契约测试"""

    def test_package_all_exports(self):
        import src.utils.omega_requests

        assert src.utils.omega_requests.__all__ == ['OmegaRequests']

    def test_requests_module_all_exports(self):
        import src.utils.omega_requests.requests

        assert src.utils.omega_requests.requests.__all__ == ['OmegaRequests']

    def test_config_module_all_exports(self):
        import src.utils.omega_requests.config

        assert src.utils.omega_requests.config.__all__ == ['omega_requests_config']

    def test_types_module_all_exports(self):
        import src.utils.omega_requests.types

        assert src.utils.omega_requests.types.__all__ == [
            'ContentTypes',
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


class TestConfig:
    """配置模块测试(具体取值由 .env.test 决定, 代理相关断言通过 monkeypatch 固定前置条件)"""

    def test_default_values(self):
        from nonebot.drivers import Timeout

        from src.utils.omega_requests.config import omega_requests_config

        assert isinstance(omega_requests_config.default_retry_limit, int)
        assert omega_requests_config.default_retry_limit >= 1
        assert isinstance(omega_requests_config.default_timeout, Timeout)
        assert isinstance(omega_requests_config.default_headers, dict)
        assert 'user-agent' in omega_requests_config.default_headers

    def test_proxy_url_disabled(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.omega_requests.config import omega_requests_config

        monkeypatch.setattr(omega_requests_config, 'omega_requests_enable_proxy', False)

        assert omega_requests_config.proxy_url is None

    def test_proxy_url_enabled(self, monkeypatch: pytest.MonkeyPatch):
        from ipaddress import IPv4Address

        from src.utils.omega_requests.config import omega_requests_config

        monkeypatch.setattr(omega_requests_config, 'omega_requests_enable_proxy', True)
        monkeypatch.setattr(omega_requests_config, 'omega_requests_proxy_type', 'http')
        monkeypatch.setattr(omega_requests_config, 'omega_requests_proxy_address', IPv4Address('127.0.0.1'))
        monkeypatch.setattr(omega_requests_config, 'omega_requests_proxy_port', 1081)

        assert omega_requests_config.proxy_url == 'http://127.0.0.1:1081'

    def test_retry_limit_lower_bound(self):
        """重试次数至少为 1(总尝试次数), 配置为 0 应在校验期被拒绝"""
        from pydantic import ValidationError

        from src.utils.omega_requests.config import OmegaRequestsConfig

        with pytest.raises(ValidationError):
            OmegaRequestsConfig(omega_requests_default_retry_limit=0)


class TestInit:
    """OmegaRequests 初始化测试"""

    def test_default_values(self):
        from src.utils.omega_requests import OmegaRequests
        from src.utils.omega_requests.config import omega_requests_config

        requests = OmegaRequests()

        assert requests.timeout == omega_requests_config.default_timeout
        assert requests.headers == omega_requests_config.default_headers
        assert requests.cookies is None
        assert requests.retry_limit == omega_requests_config.default_retry_limit

    def test_custom_values(self):
        from src.utils.omega_requests import OmegaRequests

        requests = OmegaRequests(timeout=10, headers={'x-custom': 'value'}, cookies={'session': 'abc'}, retry=5)

        assert requests.timeout == 10
        assert requests.headers == {'x-custom': 'value'}
        assert requests.cookies == {'session': 'abc'}
        assert requests.retry_limit == 5

    def test_empty_headers_and_cookies_normalized_to_none(self):
        from src.utils.omega_requests import OmegaRequests

        requests = OmegaRequests(headers={}, cookies={})

        assert requests.headers is None
        assert requests.cookies is None

    @pytest.mark.parametrize('retry', [0, -1])
    def test_invalid_retry_rejected(self, retry: int):
        """retry 语义为最大总尝试次数, 小于 1 时不会发起任何请求, 必须快速失败"""
        from src.utils.omega_requests import OmegaRequests

        with pytest.raises(ValueError, match='retry must be a positive integer'):
            OmegaRequests(retry=retry)

    def test_setters(self):
        from src.utils.omega_requests import OmegaRequests

        requests = OmegaRequests()
        requests.set_timeout(5)
        requests.set_headers({'x-a': 'b'})
        requests.set_cookies({'c': 'd'})

        assert requests.timeout == 5
        assert requests.headers == {'x-a': 'b'}
        assert requests.cookies == {'c': 'd'}

    def test_forward_driver_required(self, monkeypatch: pytest.MonkeyPatch):
        import src.utils.omega_requests.requests as requests_module
        from src.utils.omega_requests import OmegaRequests

        monkeypatch.setattr(requests_module, 'get_driver', lambda: SimpleNamespace(type='~none'))

        with pytest.raises(RuntimeError, match='ForwardDriver'):
            OmegaRequests()


class TestParseContent:
    """Response Content 解析测试"""

    def test_bytes_from_str(self):
        from src.utils.omega_requests import OmegaRequests

        response = _make_response('hello')

        assert OmegaRequests.parse_content_as_bytes(response) == b'hello'

    def test_bytes_from_bytes(self):
        from src.utils.omega_requests import OmegaRequests

        response = _make_response(b'hello')

        assert OmegaRequests.parse_content_as_bytes(response) == b'hello'

    def test_bytes_from_none(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.parse_content_as_bytes(_make_response(None)) == b''

    def test_bytes_from_other_types(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.parse_content_as_bytes(_make_response(bytearray(b'abc'))) == b'abc'

    def test_bytes_custom_encoding(self):
        from src.utils.omega_requests import OmegaRequests

        response = _make_response('中文')

        assert OmegaRequests.parse_content_as_bytes(response, encoding='gbk') == '中文'.encode('gbk')

    def test_text_from_str(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.parse_content_as_text(_make_response('hello')) == 'hello'

    def test_text_from_bytes(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.parse_content_as_text(_make_response(b'hello')) == 'hello'

    def test_text_from_none(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.parse_content_as_text(_make_response(None)) == ''

    def test_text_from_other_types(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.parse_content_as_text(_make_response(123)) == '123'

    def test_text_custom_encoding(self):
        from src.utils.omega_requests import OmegaRequests

        response = _make_response('中文'.encode('gbk'))

        assert OmegaRequests.parse_content_as_text(response, encoding='gbk') == '中文'

    def test_json_from_bytes(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.parse_content_as_json(_make_response(b'{"a": 1}')) == {'a': 1}

    def test_json_from_str(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.parse_content_as_json(_make_response('[1, 2]')) == [1, 2]

    def test_json_from_none_rejected(self):
        from src.utils.omega_requests import OmegaRequests

        with pytest.raises(ValueError, match='content of response is None'):
            OmegaRequests.parse_content_as_json(_make_response(None))

    def test_json_invalid_rejected(self):
        import ujson

        from src.utils.omega_requests import OmegaRequests

        with pytest.raises(ujson.JSONDecodeError):
            OmegaRequests.parse_content_as_json(_make_response(b'{not json'))


def _make_response(content: Any):
    from nonebot.drivers import Response

    return Response(200, content=content)


class TestUrlFileName:
    """URL 文件名解析测试"""

    @pytest.mark.parametrize(
        ('url', 'expected'),
        [
            ('http://example.com/path/to/file.jpg', 'file.jpg'),
            ('http://example.com/file.jpg?query=1', 'file.jpg'),
            ('http://example.com/file.jpg#fragment', 'file.jpg'),
            ('http://example.com/%E4%B8%AD%E6%96%87.jpg', '中文.jpg'),
            ('http://example.com/dir/', 'dir'),  # PurePath 归一化尾斜杠后取最后一段
            ('http://example.com', ''),
        ],
    )
    def test_parse_url_file_name(self, url: str, expected: str):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.parse_url_file_name(url) == expected

    def test_hash_url_file_name_deterministic(self):
        from src.utils.omega_requests import OmegaRequests

        url = 'http://example.com/file.jpg'
        expected_hash = hashlib.sha256(url.encode(encoding='utf8')).hexdigest()

        assert OmegaRequests.hash_url_file_name(url=url) == f'file_{expected_hash}.jpg'
        assert OmegaRequests.hash_url_file_name(url=url) == OmegaRequests.hash_url_file_name(url=url)

    def test_hash_url_file_name_prefixes(self):
        from src.utils.omega_requests import OmegaRequests

        url = 'http://example.com/file.jpg'
        expected_hash = hashlib.sha256(url.encode(encoding='utf8')).hexdigest()

        assert OmegaRequests.hash_url_file_name('pixiv', 'artwork', url=url) == f'pixiv_artwork_{expected_hash}.jpg'

    def test_hash_url_file_name_without_suffix(self):
        from src.utils.omega_requests import OmegaRequests

        name = OmegaRequests.hash_url_file_name(url='http://example.com/download')

        assert name.startswith('file_')
        assert '.' not in name

    def test_hash_url_file_name_varies_with_query(self):
        """hash 覆盖完整 URL(含 query), 后缀仅取自 path"""
        from src.utils.omega_requests import OmegaRequests

        name1 = OmegaRequests.hash_url_file_name(url='http://example.com/f.jpg?a=1')
        name2 = OmegaRequests.hash_url_file_name(url='http://example.com/f.jpg?a=2')

        assert name1 != name2
        assert name1.endswith('.jpg')
        assert name2.endswith('.jpg')


class TestGetUrlInText:
    """文本 URL 提取测试(审计 L2 改进后行为: 支持端口/IP/punycode, 剥离尾随标点, 路径仅可打印 ASCII)"""

    def test_single_url(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('visit https://example.com/page now') == ['https://example.com/page']

    def test_multiple_urls_keep_order(self):
        from src.utils.omega_requests import OmegaRequests

        text = 'see http://a.example.com/x and https://b.example.com/y'

        assert OmegaRequests.get_url_in_text(text) == ['http://a.example.com/x', 'https://b.example.com/y']

    def test_url_with_query(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('https://example.com/p?q=1&r=2 end') == ['https://example.com/p?q=1&r=2']

    def test_domain_with_port(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('see http://example.com:8080/p end') == ['http://example.com:8080/p']

    def test_ip_host(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('http://127.0.0.1:8080/x') == ['http://127.0.0.1:8080/x']
        assert OmegaRequests.get_url_in_text('http://10.0.0.1/a') == ['http://10.0.0.1/a']

    def test_punycode_domain(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('https://example.xn--p1ai/path') == ['https://example.xn--p1ai/path']

    def test_adjacent_cjk_text(self):
        """路径仅匹配可打印 ASCII, 紧随 URL 的中文不再被吞入"""
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('链接https://example.com/a结尾') == ['https://example.com/a']

    def test_trailing_punctuation_stripped(self):
        """尾随中英文标点及成对符号右半部分自动剥离"""
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('见 https://example.com/a.') == ['https://example.com/a']
        assert OmegaRequests.get_url_in_text('(https://example.com/a)。') == ['https://example.com/a']
        assert OmegaRequests.get_url_in_text('<https://example.com/a>') == ['https://example.com/a']

    def test_unsupported_scheme_rejected(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('ftp://example.com/x file://example.com/y') == []

    def test_bare_domain_rejected(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('example.com/path') == []

    def test_host_without_tld_rejected(self):
        """无后缀主机名(如 localhost)不识别为合法 URL"""
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('http://localhost:8080/x') == []

    def test_empty_text(self):
        from src.utils.omega_requests import OmegaRequests

        assert OmegaRequests.get_url_in_text('') == []

    def test_duplicated_occurrences_kept(self):
        from src.utils.omega_requests import OmegaRequests

        text = 'https://example.com/a https://example.com/a'

        assert OmegaRequests.get_url_in_text(text) == ['https://example.com/a', 'https://example.com/a']


class TestGetDefaults:
    """默认配置获取测试(深拷贝隔离)"""

    def test_default_headers_deepcopy(self):
        from src.utils.omega_requests import OmegaRequests
        from src.utils.omega_requests.config import omega_requests_config

        headers = OmegaRequests.get_default_headers()
        headers['injected'] = 'x'

        assert 'injected' not in omega_requests_config.default_headers

    def test_default_timeout_deepcopy(self):
        from src.utils.omega_requests import OmegaRequests
        from src.utils.omega_requests.config import omega_requests_config

        timeout = OmegaRequests.get_default_timeout()
        origin_total = omega_requests_config.default_timeout.total
        timeout.total = 999

        assert omega_requests_config.default_timeout.total == origin_total


class TestIterContentAsLines:
    """流式行迭代测试(合成响应生成器, 精确控制分块边界)"""

    @pytest.mark.parametrize(
        ('chunks', 'expected'),
        [
            ([], []),
            ([b'line1\nline2\n'], ['line1', 'line2']),
            ([b'lin', b'e1\nli', b'ne2\n'], ['line1', 'line2']),
            ([b'line1\r', b'\nline2\r\n'], ['line1', 'line2']),
            ([b'line1\rline2\r'], ['line1', 'line2']),
            ([b'line\r'], ['line']),  # 流末尾孤立 \r 是行终止符, 不进入行内容(审计 M1)
            ([b'a\r\r\n'], ['a', '']),
            ([b'a\r', b'\n'], ['a']),
            ([b''], []),
            ([None], []),
            ([b'', b'a\n', None, b'b'], ['a', 'b']),
            ([b'no-newline-tail'], ['no-newline-tail']),
            ([b'\n'], ['']),
        ],
    )
    async def test_iter_lines(self, chunks: list[Any], expected: list[str]):
        from src.utils.omega_requests import OmegaRequests

        lines = [line async for line in OmegaRequests.iter_content_as_lines(_line_chunks(chunks))]

        assert lines == expected

    async def test_iter_lines_custom_encoding(self):
        from src.utils.omega_requests import OmegaRequests

        chunks = ['第一行\n第二'.encode('gbk'), '行\n'.encode('gbk')]

        lines = [line async for line in OmegaRequests.iter_content_as_lines(_line_chunks(chunks), encoding='gbk')]

        assert lines == ['第一行', '第二行']


class TestDriverGuards:
    """驱动能力守卫测试(替换实例 driver 为假驱动)"""

    def test_get_session_guard(self):
        from src.utils.omega_requests import OmegaRequests

        requests = OmegaRequests()
        requests.driver = SimpleNamespace(type='~none')

        with pytest.raises(RuntimeError, match='HTTPClient Driver'):
            requests.get_session()

    async def test_request_guard(self):
        from nonebot.drivers import Request

        from src.utils.omega_requests import OmegaRequests

        requests = OmegaRequests()
        requests.driver = SimpleNamespace(type='~none')

        with pytest.raises(RuntimeError, match='HTTPClient Driver'):
            await requests.request(Request('GET', 'http://127.0.0.1/'))

    async def test_stream_request_guard(self):
        from nonebot.drivers import Request

        from src.utils.omega_requests import OmegaRequests

        requests = OmegaRequests()
        requests.driver = SimpleNamespace(type='~none')

        async def _collect():
            return [x async for x in requests.stream_request(Request('GET', 'http://127.0.0.1/'))]

        with pytest.raises(RuntimeError, match='HTTPClient Driver'):
            await _collect()

    async def test_websocket_guard(self):
        from src.utils.omega_requests import OmegaRequests

        requests = OmegaRequests()
        requests.driver = SimpleNamespace(type='~none')

        async def _connect():
            async with requests.websocket('GET', 'http://127.0.0.1/'):
                pass

        with pytest.raises(RuntimeError, match='WebSocketClient Driver'):
            await _connect()


class TestHttpMethods:
    """HTTP 方法集成测试(真实请求测试服务端)"""

    async def test_get_echo_with_default_headers(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests
        from src.utils.omega_requests.config import omega_requests_config

        response = await OmegaRequests().get(f'{test_server.base_url}/get', params={'a': '1'})

        assert response.status_code == 200
        data = OmegaRequests.parse_content_as_json(response)
        assert ['a', '1'] in data['params']
        assert data['headers']['user-agent'] == omega_requests_config.default_headers['user-agent']

    async def test_get_with_multi_value_params(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        response = await OmegaRequests().get(f'{test_server.base_url}/get', params=[('a', '1'), ('a', '2')])

        data = OmegaRequests.parse_content_as_json(response)
        assert ['a', '1'] in data['params']
        assert ['a', '2'] in data['params']

    async def test_per_request_headers_replace_instance_headers(self, test_server: SimpleNamespace):
        """单请求 headers 整体替换实例 headers(aiohttp 会自动补 UA, 故默认 UA 不再出现)"""
        from src.utils.omega_requests import OmegaRequests
        from src.utils.omega_requests.config import omega_requests_config

        response = await OmegaRequests().get(f'{test_server.base_url}/get', headers={'x-custom': '1'})

        data = OmegaRequests.parse_content_as_json(response)
        assert data['headers']['x-custom'] == '1'
        assert data['headers']['user-agent'] != omega_requests_config.default_headers['user-agent']

    async def test_cookies_sent(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        response = await OmegaRequests(cookies={'session_id': 'abc123'}).get(f'{test_server.base_url}/get')

        data = OmegaRequests.parse_content_as_json(response)
        assert 'session_id=abc123' in data['headers']['cookie']

    async def test_post_raw_content(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        response = await OmegaRequests().post(f'{test_server.base_url}/post', content=b'\x00\xffbinary')

        assert response.status_code == 200
        assert OmegaRequests.parse_content_as_bytes(response) == b'\x00\xffbinary'
        assert response.headers['X-Echo-Content-Type'] == 'application/octet-stream'

    async def test_post_form_data(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        response = await OmegaRequests().post(f'{test_server.base_url}/post', data={'key': 'value'})

        assert OmegaRequests.parse_content_as_bytes(response) == b'key=value'
        assert response.headers['X-Echo-Content-Type'].startswith('application/x-www-form-urlencoded')

    async def test_post_json(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        response = await OmegaRequests().post(f'{test_server.base_url}/post_json', json={'a': 1, 'b': 'x'})

        assert OmegaRequests.parse_content_as_json(response) == {'echo': {'a': 1, 'b': 'x'}}

    async def test_put(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        response = await OmegaRequests().put(f'{test_server.base_url}/put', content=b'data')

        assert OmegaRequests.parse_content_as_json(response) == {'ok': True, 'method': 'PUT'}

    async def test_delete(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        response = await OmegaRequests().delete(f'{test_server.base_url}/delete')

        assert OmegaRequests.parse_content_as_json(response) == {'ok': True, 'method': 'DELETE'}


class TestRetry:
    """自动重试集成测试(仅超时/连接异常触发重试, 非 2xx 状态码不触发)"""

    async def test_retry_then_success(self, test_server: SimpleNamespace):
        from nonebot.drivers import Timeout

        from src.utils.omega_requests import OmegaRequests

        token = _new_token()
        requests = OmegaRequests(timeout=Timeout(total=1), retry=3)

        response = await requests.get(f'{test_server.base_url}/flaky/{token}', params={'fail': 2})

        assert response.status_code == 200
        assert OmegaRequests.parse_content_as_json(response)['attempt'] == 3
        assert test_server.state.counters[f'flaky:{token}'] == 3

    async def test_retry_exhausted_by_timeout(self, test_server: SimpleNamespace):
        from nonebot.drivers import Timeout

        from src.exception import WebSourceException
        from src.utils.omega_requests import OmegaRequests

        token = _new_token()
        requests = OmegaRequests(timeout=Timeout(total=1), retry=2)

        with pytest.raises(WebSourceException) as exc_info:
            await requests.get(f'{test_server.base_url}/slow/{token}')

        assert exc_info.value.status_code == 500
        assert isinstance(exc_info.value.__cause__, TimeoutError)
        assert test_server.state.counters[f'slow:{token}'] == 2

    async def test_retry_exhausted_by_connection_error(self, unused_port: int):
        import aiohttp

        from src.exception import WebSourceException
        from src.utils.omega_requests import OmegaRequests

        requests = OmegaRequests(retry=2)

        with pytest.raises(WebSourceException) as exc_info:
            await requests.get(f'http://127.0.0.1:{unused_port}/')

        assert exc_info.value.status_code == 500
        assert isinstance(exc_info.value.__cause__, aiohttp.ClientError)

    async def test_error_status_not_retried(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        token = _new_token()

        response = await OmegaRequests(retry=3).get(f'{test_server.base_url}/status/503', params={'token': token})

        assert response.status_code == 503
        assert test_server.state.counters[f'status:503:{token}'] == 1


class TestStreaming:
    """流式请求集成测试"""

    async def test_stream_get(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        responses = [x async for x in OmegaRequests().stream_get(f'{test_server.base_url}/stream', chunk_size=4)]

        # 驱动按 chunk_size 精确重组块, 15 字节负载应为 [4, 4, 4, 3]
        assert [len(x.content) for x in responses] == [4, 4, 4, 3]
        assert b''.join(x.content for x in responses) == _STREAM_PAYLOAD
        assert all(x.status_code == 200 for x in responses)

    async def test_stream_post(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        responses = [x async for x in OmegaRequests().stream_post(f'{test_server.base_url}/stream', chunk_size=4)]

        assert b''.join(x.content for x in responses) == _STREAM_PAYLOAD

    async def test_stream_get_iter_lines(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        lines = [x async for x in OmegaRequests().stream_get_iter_lines(f'{test_server.base_url}/lines')]

        assert lines == _LINES_EXPECTED

    async def test_stream_post_iter_lines(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        lines = [x async for x in OmegaRequests().stream_post_iter_lines(f'{test_server.base_url}/lines')]

        assert lines == _LINES_EXPECTED

    async def test_stream_timeout(self, test_server: SimpleNamespace):
        from nonebot.drivers import Timeout

        from src.exception import WebSourceException
        from src.utils.omega_requests import OmegaRequests

        received: list[bytes] = []

        # 驱动按 chunk_size 精确重组块, 不足一块的余量仅在流正常结束时冲刷; chunk_size 取首块全长,
        # 保证超时前确定性收到完整 'first-chunk'
        async def _collect():
            async for x in OmegaRequests().stream_get(
                    f'{test_server.base_url}/stream_stall', chunk_size=len(b'first-chunk'), timeout=Timeout(read=1)
            ):
                received.append(x.content)

        with pytest.raises(WebSourceException) as exc_info:
            await _collect()

        assert exc_info.value.status_code == 504
        assert b''.join(received) == b'first-chunk'

    async def test_stream_error_status_passthrough(self, test_server: SimpleNamespace):
        """流式请求不校验状态码, 错误状态随分块透传给调用方处理"""
        from src.utils.omega_requests import OmegaRequests

        responses = [x async for x in OmegaRequests().stream_get(f'{test_server.base_url}/status/500')]

        assert responses
        assert all(x.status_code == 500 for x in responses)

    async def test_stream_empty_error_yields_nothing(self, test_server: SimpleNamespace):
        """空响应体的错误响应在流式请求中不产生分块(驱动层固有限制, 由 download 层核验状态兜底)"""
        from src.utils.omega_requests import OmegaRequests

        responses = [x async for x in OmegaRequests().stream_get(f'{test_server.base_url}/status_empty/404')]

        assert responses == []

    async def test_stream_connection_error(self, unused_port: int):
        """非超时类异常(如连接拒绝)在流式请求中包装为 WebSourceException(500)"""
        import aiohttp

        from src.exception import WebSourceException
        from src.utils.omega_requests import OmegaRequests

        async def _collect():
            return [x async for x in OmegaRequests().stream_get(f'http://127.0.0.1:{unused_port}/')]

        with pytest.raises(WebSourceException) as exc_info:
            await _collect()

        assert exc_info.value.status_code == 500
        assert isinstance(exc_info.value.__cause__, aiohttp.ClientError)


class TestDownload:
    """下载集成测试"""

    async def test_download_success(self, test_server: SimpleNamespace, tmp_path: Path):
        from src.utils.omega_requests import OmegaRequests

        file = _make_file(tmp_path, 'download_success.bin')

        result = await OmegaRequests().download(url=f'{test_server.base_url}/download', file=file)

        assert result is file
        assert file.is_file
        assert file.path.read_bytes() == _DOWNLOAD_PAYLOAD

    async def test_download_ignore_exist_file(self, test_server: SimpleNamespace, tmp_path: Path):
        from src.utils.omega_requests import OmegaRequests

        file = _make_file(tmp_path, 'download_ignore.bin')
        file.path.write_bytes(b'existing')

        result = await OmegaRequests().download(
            url=f'{test_server.base_url}/download', file=file, ignore_exist_file=True
        )

        assert result is file
        assert file.path.read_bytes() == b'existing'

    async def test_download_error_status(self, test_server: SimpleNamespace, tmp_path: Path):
        from src.exception import WebSourceException
        from src.utils.omega_requests import OmegaRequests

        file = _make_file(tmp_path, 'download_error.bin')

        with pytest.raises(WebSourceException) as exc_info:
            await OmegaRequests().download(url=f'{test_server.base_url}/status/404', file=file)

        assert exc_info.value.status_code == 404
        assert not file.is_file

    async def test_stream_download_success(self, test_server: SimpleNamespace, tmp_path: Path):
        from src.utils.omega_requests import OmegaRequests

        file = _make_file(tmp_path, 'stream_success.bin')

        result = await OmegaRequests().stream_download(url=f'{test_server.base_url}/download', file=file)

        assert result.is_file
        assert result.path.read_bytes() == _DOWNLOAD_PAYLOAD
        assert not tmp_path.joinpath('stream_success.bin.DOWNLOADING_TMP').exists()

    async def test_stream_download_ignore_exist_file(self, test_server: SimpleNamespace, tmp_path: Path):
        from src.utils.omega_requests import OmegaRequests

        token = _new_token()
        file = _make_file(tmp_path, 'stream_ignore.bin')
        file.path.write_bytes(b'existing')

        result = await OmegaRequests().stream_download(
            url=f'{test_server.base_url}/download_range/{token}', file=file, ignore_exist_file=True
        )

        assert result is file
        assert file.path.read_bytes() == b'existing'
        assert test_server.state.counters.get(f'range:{token}', 0) == 0

    async def test_stream_download_resume(self, test_server: SimpleNamespace, tmp_path: Path):
        """断点续传: 预置临时文件前 100 字节, 服务端应收到 Range 头并以 206 返回剩余内容"""
        from src.utils.omega_requests import OmegaRequests

        token = _new_token()
        file = _make_file(tmp_path, 'resume.bin')
        _make_file(tmp_path, 'resume.bin.DOWNLOADING_TMP').path.write_bytes(_DOWNLOAD_PAYLOAD[:100])

        result = await OmegaRequests().stream_download(
            url=f'{test_server.base_url}/download_range/{token}', file=file
        )

        assert result.path.read_bytes() == _DOWNLOAD_PAYLOAD
        assert test_server.state.range_headers[f'range:{token}'] == ['bytes=100-']
        assert test_server.state.counters[f'range:{token}'] == 1

    async def test_stream_download_resume_unsupported_restart(self, test_server: SimpleNamespace, tmp_path: Path):
        """服务端忽略 Range 返回 200 时应清空临时文件并全量重下"""
        from src.utils.omega_requests import OmegaRequests

        token = _new_token()
        file = _make_file(tmp_path, 'restart.bin')
        _make_file(tmp_path, 'restart.bin.DOWNLOADING_TMP').path.write_bytes(b'x' * 100)

        result = await OmegaRequests().stream_download(
            url=f'{test_server.base_url}/download_no_range/{token}', file=file
        )

        assert result.path.read_bytes() == _DOWNLOAD_PAYLOAD
        assert test_server.state.counters[f'no_range:{token}'] == 2
        assert test_server.state.range_headers[f'no_range:{token}'] == ['bytes=100-', None]

    async def test_stream_download_error_status(self, test_server: SimpleNamespace, tmp_path: Path):
        from src.exception import WebSourceException
        from src.utils.omega_requests import OmegaRequests

        file = _make_file(tmp_path, 'stream_error.bin')

        with pytest.raises(WebSourceException) as exc_info:
            await OmegaRequests().stream_download(url=f'{test_server.base_url}/status/404', file=file)

        assert exc_info.value.status_code == 404
        assert not file.is_file

    async def test_stream_download_empty_error_rejected(self, test_server: SimpleNamespace, tmp_path: Path):
        """审计 H1 回归: 空响应体的错误响应不得静默成功(零分块时核验状态并抛错, 不产出文件)"""
        from src.exception import WebSourceException
        from src.utils.omega_requests import OmegaRequests

        file = _make_file(tmp_path, 'stream_empty_error.bin')

        with pytest.raises(WebSourceException) as exc_info:
            await OmegaRequests().stream_download(url=f'{test_server.base_url}/status_empty/404', file=file)

        assert exc_info.value.status_code == 404
        assert not file.is_file

    async def test_stream_download_empty_ok(self, test_server: SimpleNamespace, tmp_path: Path):
        """空响应体的 200 响应是合法空文件下载, 应正常产出 0 字节文件"""
        from src.utils.omega_requests import OmegaRequests

        file = _make_file(tmp_path, 'stream_empty_ok.bin')

        result = await OmegaRequests().stream_download(url=f'{test_server.base_url}/download_empty', file=file)

        assert result.is_file
        assert result.file_size == 0
        assert not tmp_path.joinpath('stream_empty_ok.bin.DOWNLOADING_TMP').exists()

    async def test_stream_download_resume_stale_temp_rejected(self, test_server: SimpleNamespace, tmp_path: Path):
        """临时文件已不落后于资源(416)时应清空重下: 流式与核验各一次 416, 第三次全新下载成功"""
        from src.utils.omega_requests import OmegaRequests

        token = _new_token()
        file = _make_file(tmp_path, 'resume_stale.bin')
        _make_file(tmp_path, 'resume_stale.bin.DOWNLOADING_TMP').path.write_bytes(_DOWNLOAD_PAYLOAD)

        result = await OmegaRequests().stream_download(
            url=f'{test_server.base_url}/download_range/{token}', file=file
        )

        assert result.path.read_bytes() == _DOWNLOAD_PAYLOAD
        assert test_server.state.counters[f'range:{token}'] == 3
        assert test_server.state.range_headers[f'range:{token}'] == [
            f'bytes={len(_DOWNLOAD_PAYLOAD)}-',
            f'bytes={len(_DOWNLOAD_PAYLOAD)}-',
            None,
        ]

    async def test_stream_download_resume_zero_remainder(self, test_server: SimpleNamespace, tmp_path: Path):
        """服务端对已完整断点返回 206 空响应体: 核验状态为 206 后直接使用临时文件内容"""
        from src.utils.omega_requests import OmegaRequests

        token = _new_token()
        file = _make_file(tmp_path, 'resume_done.bin')
        _make_file(tmp_path, 'resume_done.bin.DOWNLOADING_TMP').path.write_bytes(_DOWNLOAD_PAYLOAD)

        result = await OmegaRequests().stream_download(
            url=f'{test_server.base_url}/download_206_empty/{token}', file=file
        )

        assert result.path.read_bytes() == _DOWNLOAD_PAYLOAD
        assert test_server.state.counters[f'206_empty:{token}'] == 2
        assert test_server.state.range_headers[f'206_empty:{token}'] == [
            f'bytes={len(_DOWNLOAD_PAYLOAD)}-',
            f'bytes={len(_DOWNLOAD_PAYLOAD)}-',
        ]

    async def test_stream_download_custom_headers(self, test_server: SimpleNamespace, tmp_path: Path):
        """审计 M2 回归: 调用方 headers 可正常传入并与断点续传 Range 头共存"""
        from src.utils.omega_requests import OmegaRequests

        token = _new_token()
        file = _make_file(tmp_path, 'resume_headers.bin')
        _make_file(tmp_path, 'resume_headers.bin.DOWNLOADING_TMP').path.write_bytes(_DOWNLOAD_PAYLOAD[:100])

        result = await OmegaRequests().stream_download(
            url=f'{test_server.base_url}/download_range/{token}', file=file, headers={'x-test-header': 'omega_test'}
        )

        assert result.path.read_bytes() == _DOWNLOAD_PAYLOAD
        assert test_server.state.custom_headers[f'range:{token}'] == ['omega_test']
        assert test_server.state.range_headers[f'range:{token}'] == ['bytes=100-']


class TestGetSession:
    """get_session 集成测试"""

    async def test_session_request(self, test_server: SimpleNamespace):
        from nonebot.drivers import HTTPClientSession, Request

        from src.utils.omega_requests import OmegaRequests

        session = OmegaRequests().get_session()
        assert isinstance(session, HTTPClientSession)

        async with session:
            response = await session.request(Request('GET', f'{test_server.base_url}/get'))

        assert response.status_code == 200

    async def test_session_without_proxy(self, test_server: SimpleNamespace):
        from nonebot.drivers import Request

        from src.utils.omega_requests import OmegaRequests

        session = OmegaRequests().get_session(use_proxy=False)

        async with session:
            response = await session.request(Request('GET', f'{test_server.base_url}/get'))

        assert response.status_code == 200


class TestWebSocket:
    """WebSocket 集成测试"""

    async def test_text_echo(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        async with OmegaRequests().websocket('GET', f'{test_server.base_url}/ws') as ws:
            await ws.send_text('hello')
            assert await ws.receive_text() == 'echo:hello'

    async def test_bytes_echo(self, test_server: SimpleNamespace):
        from src.utils.omega_requests import OmegaRequests

        async with OmegaRequests().websocket('GET', f'{test_server.base_url}/ws') as ws:
            await ws.send_bytes(b'\x00\x01')
            assert await ws.receive_bytes() == b'echo:\x00\x01'

    async def test_handshake_failure(self, test_server: SimpleNamespace):
        """对非 WebSocket 端点发起握手: 本方法不包装驱动异常, 原始 aiohttp 异常向上传播"""
        import aiohttp

        from src.utils.omega_requests import OmegaRequests

        async def _connect():
            async with OmegaRequests().websocket('GET', f'{test_server.base_url}/get'):
                pass

        with pytest.raises(aiohttp.ClientError):
            await _connect()


class TestProxy:
    """代理行为集成测试(monkeypatch 固定代理配置前置条件)"""

    @staticmethod
    def _enable_proxy(monkeypatch: pytest.MonkeyPatch, port: int) -> None:
        from src.utils.omega_requests.config import omega_requests_config

        monkeypatch.setattr(omega_requests_config, 'omega_requests_enable_proxy', True)
        monkeypatch.setattr(omega_requests_config, 'omega_requests_proxy_port', port)

    async def test_use_proxy_routes_through_proxy(self, test_server: SimpleNamespace, unused_port: int, monkeypatch):
        """启用代理且代理不可达时请求失败, 证明代理配置已生效"""
        from src.exception import WebSourceException
        from src.utils.omega_requests import OmegaRequests

        self._enable_proxy(monkeypatch, unused_port)

        with pytest.raises(WebSourceException):
            await OmegaRequests(retry=1).get(f'{test_server.base_url}/get', use_proxy=True)

    async def test_use_proxy_false_bypasses_proxy(self, test_server: SimpleNamespace, unused_port: int, monkeypatch):
        """use_proxy=False 可绕过已启用的代理配置直连"""
        from src.utils.omega_requests import OmegaRequests

        self._enable_proxy(monkeypatch, unused_port)

        response = await OmegaRequests().get(f'{test_server.base_url}/get', use_proxy=False)

        assert response.status_code == 200

    async def test_proxy_disabled_plain_request(self, test_server: SimpleNamespace, monkeypatch):
        from src.utils.omega_requests import OmegaRequests
        from src.utils.omega_requests.config import omega_requests_config

        monkeypatch.setattr(omega_requests_config, 'omega_requests_enable_proxy', False)

        response = await OmegaRequests().get(f'{test_server.base_url}/get', use_proxy=True)

        assert response.status_code == 200
