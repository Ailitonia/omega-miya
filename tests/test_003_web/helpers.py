"""
@Author         : Ailitonia
@Date           : 2026/9/12 22:45
@FileName       : helpers
@Project        : omega-miya
@Description    : test_003_web 共享测试工具(负载常量与测试服务端路由注册)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import os
import time
import uuid
from collections.abc import AsyncGenerator
from http.cookiejar import Cookie, CookieJar
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest

if TYPE_CHECKING:
    from src.resource import AnyResource
    from src.service.omega_api import OmegaAPI

_STREAM_CHUNKS = [b'alpha', b'-beta', b'-game']
"""流式测试服务端输出的固定分块"""

_STREAM_PAYLOAD = b''.join(_STREAM_CHUNKS)
"""流式测试完整负载, 共 15 字节, chunk_size=4 时驱动重组块为 [4, 4, 4, 3]"""

_DOWNLOAD_PAYLOAD = bytes(range(256)) * 64
"""下载测试固定负载, 共 16 KiB 确定性内容"""

_LINES_EXPECTED = ['first', 'second', 'third', 'fourth', '', 'last-no-newline']
"""行迭代测试期望结果, 对应混合 \\n / \\r\\n / \\r 行结尾与无换行残留行"""


def make_test_file(tmp_path: Path, name: str) -> 'AnyResource':
    """在临时目录构造下载目标文件资源"""
    from src.resource import AnyResource

    return AnyResource(tmp_path, name)


def make_test_folder(tmp_path: Path) -> 'AnyResource':
    """构造指向临时目录本身的文件夹资源"""
    from src.resource import AnyResource

    return AnyResource(tmp_path)


def new_request_token() -> str:
    """生成测试用例隔离 token(用于服务端按用例计数/记录请求头)"""
    return uuid.uuid4().hex[:8]


def make_response(content: Any = None, headers: Any = None, status_code: int = 200):
    """构造合成 nonebot Response(不经网络); content 为 str/bytes 时原样作为响应体, 其余对象按 JSON 序列化"""
    import ujson
    from nonebot.drivers import Response

    if content is not None and not isinstance(content, (str, bytes, bytearray)):
        content = ujson.dumps(content).encode(encoding='utf-8')
    return Response(status_code, headers=headers, content=content)


def make_cookie_jar(name: str, value: str) -> CookieJar:
    """构造含单个 cookie 的 http.cookiejar.CookieJar"""
    jar = CookieJar()
    jar.set_cookie(Cookie(
        version=0, name=name, value=value,
        port=None, port_specified=False, domain='example.com', domain_specified=False, domain_initial_dot=False,
        path='/', path_specified=True, secure=False, expires=None, discard=True,
        comment=None, comment_url=None, rest={}, rfc2109=False,
    ))
    return jar


def capture_driver_request(monkeypatch: pytest.MonkeyPatch) -> list:
    """monkeypatch 驱动 request 方法, 捕获 Request setup 并返回固定 200 响应(不经网络)"""
    from nonebot import get_driver
    from nonebot.drivers import Response

    captured = []

    async def _fake_request(setup):
        captured.append(setup)
        return Response(200, content=b'{}')

    monkeypatch.setattr(get_driver(), 'request', _fake_request)
    return captured


def capture_driver_stream_request(monkeypatch: pytest.MonkeyPatch, stream_payload: bytes = b'a\nb\n') -> list:
    """monkeypatch 驱动 stream_request 方法, 捕获 Request setup 并产出固定分块(不经网络)"""
    from nonebot import get_driver
    from nonebot.drivers import Response

    captured = []

    async def _fake_stream_request(setup, *, chunk_size=1024):
        captured.append(setup)
        yield Response(200, content=stream_payload)

    monkeypatch.setattr(get_driver(), 'stream_request', _fake_stream_request)
    return captured


def patch_module_asyncio_sleep(monkeypatch: pytest.MonkeyPatch, module: ModuleType) -> AsyncMock:
    """以 AsyncMock 替换指定模块命名空间内的 asyncio.sleep, 跳过其固定等待

    重绑定的是目标模块内的 asyncio 名字(继承真实 asyncio 全部属性, 仅覆盖 sleep);
    不得全局 patch asyncio.sleep, 否则会与 session 事件循环上常驻的
    uvicorn Server.main_loop (asyncio.sleep 轮询) 竞态导致卡死
    """
    sleep_mock = AsyncMock()
    monkeypatch.setattr(module, 'asyncio', SimpleNamespace(**{**vars(asyncio), 'sleep': sleep_mock}))
    return sleep_mock


def patch_module_time(monkeypatch: pytest.MonkeyPatch, module: ModuleType, fixed_ts: int) -> None:
    """重绑定指定模块命名空间内的 time 名字, 使其 time.time() 返回固定时间戳

    目标模块以 `import time` 方式引用标准库, 直接 patch `module.time.time` 会冻结进程级 time.time,
    殃及 session 事件循环上常驻的 uvicorn/nonebot 组件; 此处仅替换模块内的 time 名字本身
    """
    monkeypatch.setattr(module, 'time', SimpleNamespace(**{**vars(time), 'time': lambda: fixed_ts}))


def require_env_flag(env_var: str, *, reason: str | None = None):
    """构造真实请求验证门禁(skipif 标记): 未设置对应环境变量时跳过

    日常运行(含全量套件)一律跳过, 由用户手动设置环境变量后发起(如 {env_var}=1)
    """
    enabled = os.getenv(env_var, '').lower() in ('1', 'true', 'yes', 'on')
    return pytest.mark.skipif(not enabled, reason=reason or f'真实请求验证, 需手动设置 {env_var}=1 环境变量后运行')


def patch_system_setting_dal(
        monkeypatch: pytest.MonkeyPatch,
        series: list | None = None,
        unique: dict[str, str] | None = None,
) -> SimpleNamespace:
    """以记录调用的伪 DAL 替换 SystemSettingDAL.create

    :param series: query_series 返回的配置项列表
    :param unique: query_unique 的键值表, 未命中键抛出 NoResultFound
    :return: SimpleNamespace(deleted=[被删除的 setting_key], saved={setting_key: setting_value})
    """
    from contextlib import asynccontextmanager

    from sqlalchemy.exc import NoResultFound

    from src.database import SystemSettingDAL

    fake_dal = SimpleNamespace(deleted=[], saved={}, _series=series or [], _unique=unique or {})

    async def _query_series(setting_name: str, **_kwargs):
        return fake_dal._series

    async def _query_unique(setting_name: str, setting_key: str, **_kwargs):
        if setting_key not in fake_dal._unique:
            raise NoResultFound(f'no row for {setting_key!r}')
        return SimpleNamespace(
            setting_name=setting_name, setting_key=setting_key, setting_value=fake_dal._unique[setting_key]
        )

    async def _delete(setting_name: str, setting_key: str) -> None:
        fake_dal.deleted.append(setting_key)

    async def _add_update_exist(setting_name: str, setting_key: str, setting_value: str, **_kwargs) -> None:
        fake_dal.saved[setting_key] = setting_value

    fake_dal.query_series = _query_series
    fake_dal.query_unique = _query_unique
    fake_dal.delete = _delete
    fake_dal.add_update_exist = _add_update_exist

    @asynccontextmanager
    async def _fake_create(_cls):
        yield fake_dal

    monkeypatch.setattr(SystemSettingDAL, 'create', classmethod(_fake_create))
    return fake_dal


async def line_chunks_stream(chunks: list[Any]) -> AsyncGenerator[Any, None]:
    """构造合成流式响应生成器(精确控制分块边界, 不经网络与驱动重组块)"""
    from nonebot.drivers import Response

    for chunk in chunks:
        yield Response(200, content=chunk)


def register_test_routes(api: 'OmegaAPI', state: SimpleNamespace) -> None:
    """向测试服务端子应用注册全部测试路由

    :param api: OmegaAPI 测试应用实例
    :param state: 共享状态(SimpleNamespace, 含 counters/range_headers/custom_headers 三个 dict)
    """
    from fastapi import Request as FastAPIRequest
    from fastapi import Response as FastAPIResponse
    from fastapi import WebSocket as FastAPIWebSocket
    from fastapi.responses import PlainTextResponse, StreamingResponse

    def _record(key: str, request: FastAPIRequest) -> None:
        state.counters[key] += 1
        state.range_headers[key].append(request.headers.get('range'))
        state.custom_headers[key].append(request.headers.get('x-test-header'))

    @api.register_get_route('/')
    async def _root():
        # 路径解析文件名为空的场景(parse_url_file_name 返回 ''), 覆盖下载文件名回退路径
        return FastAPIResponse(content=_DOWNLOAD_PAYLOAD, media_type='application/octet-stream')

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

    @api.register_delete_route('/status/{code}')
    @api.register_put_route('/status/{code}')
    @api.register_post_route('/status/{code}')
    @api.register_get_route('/status/{code}')
    async def _status(code: int, token: str = ''):
        state.counters[f'status:{code}:{token}'] += 1
        return PlainTextResponse(f'status {code}', status_code=code)

    @api.register_get_route('/status_empty/{code}')
    async def _status_empty(code: int):
        # 空响应体的错误响应: 流式请求不产生任何分块, 用于覆盖 stream_download 零分块核验路径
        return FastAPIResponse(status_code=code)

    @api.register_get_route('/redirect_target/{token}')
    async def _redirect_target(token: str):
        # 重定向终点: 计数用于断言跟随/未跟随, 返回 JSON 用于内容断言
        state.counters[f'redirect_target:{token}'] += 1
        return {'ok': True, 'token': token}

    @api.register_delete_route('/redirect/{code}')
    @api.register_put_route('/redirect/{code}')
    @api.register_post_route('/redirect/{code}')
    @api.register_get_route('/redirect/{code}')
    async def _redirect(code: int, target: str = '/redirect_target/default'):
        # 带响应体的重定向: 空响应体在流式请求中不产生分块, 带 body 才能覆盖流式不跟随重定向的状态校验路径
        return FastAPIResponse(content=f'redirect {code}', status_code=code, headers={'location': target})

    @api.register_get_route('/set_cookie')
    async def _set_cookie():
        # 附两个 Set-Cookie 头, 其中一个值内含等号, 覆盖响应 cookie 解析边界
        response = PlainTextResponse('ok')
        response.headers.append('set-cookie', 'session=abc; Path=/; HttpOnly')
        response.headers.append('set-cookie', 'token=v1=v2; Path=/')
        return response

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

    @api.register_get_route('/download_file/{name}')
    async def _download_file(name: str):
        # 文件名取自 URL path, 覆盖下载保持原始文件名场景
        return FastAPIResponse(content=_DOWNLOAD_PAYLOAD, media_type='application/octet-stream')

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


__all__ = [
    '_DOWNLOAD_PAYLOAD',
    '_LINES_EXPECTED',
    '_STREAM_PAYLOAD',
    'capture_driver_request',
    'capture_driver_stream_request',
    'line_chunks_stream',
    'make_cookie_jar',
    'make_response',
    'make_test_file',
    'make_test_folder',
    'new_request_token',
    'patch_module_asyncio_sleep',
    'patch_module_time',
    'patch_system_setting_dal',
    'register_test_routes',
    'require_env_flag',
]
