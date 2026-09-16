"""
@Author         : Ailitonia
@Date           : 2026/9/12 22:45
@FileName       : conftest
@Project        : omega-miya
@Description    : test_003_web 共享 fixtures(真实 HTTP/WebSocket 测试服务端)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import contextlib
import os
import socket
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest
import uvicorn
from starlette.routing import Mount

from tests.test_003_web.helpers import register_test_routes


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

    from src.service.omega_api import OmegaAPI
    from src.service.omega_api.api import _REGISTERED_APP
    from src.utils.omega_requests.config import omega_requests_config

    # 测试环境配置默认启用代理(.env.test omega_requests_enable_proxy=True), 会话内强制禁用,
    # 保证集成用例直连本地测试服务端; 代理行为由各测试模块经 monkeypatch 逐用例覆盖
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
    register_test_routes(api, state)

    config = uvicorn.Config(
        app=api._app,
        host='127.0.0.1',
        port=0,
        log_level='warning',
        timeout_graceful_shutdown=3,
    )
    server = uvicorn.Server(config)
    serve_task = asyncio.create_task(server.serve())
    for _ in range(200):
        if server.started:
            break
        await asyncio.sleep(0.05)
    else:
        serve_task.cancel()
        raise RuntimeError('omega test server failed to start')
    port = server.servers[0].sockets[0].getsockname()[1]

    try:
        yield SimpleNamespace(base_url=f'http://127.0.0.1:{port}', api=api, state=state)
    finally:
        omega_requests_config.omega_requests_enable_proxy = saved_enable_proxy

        # should_exit=False 使 uvicorn 走完 lifespan shutdown 流程,
        # 避免孤儿 lifespan 任务在 event loop 关闭时被取消而打出 CancelledError traceback
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
