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
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

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


def new_request_token() -> str:
    """生成测试用例隔离 token(用于服务端按用例计数/记录请求头)"""
    return uuid.uuid4().hex[:8]


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
    '_STREAM_CHUNKS',
    '_STREAM_PAYLOAD',
    'line_chunks_stream',
    'make_test_file',
    'new_request_token',
    'register_test_routes',
]
