"""
@Author         : Ailitonia
@Date           : 2022/12/13 15:04
@FileName       : patch.py
@Project        : nonebot2_miya 
@Description    : ForwardMixin cookies params 修复
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import aiohttp
import httpx

from types import MethodType
from nonebot.drivers import Request, Response
from nonebot.drivers import HTTPVersion

from nonebot.drivers.aiohttp import Mixin as AiohttpMixin
from nonebot.drivers.httpx import Mixin as HttpxMixin


async def aiohttp_request(self, setup: Request) -> Response:
    if setup.version == HTTPVersion.H10:
        version = aiohttp.HttpVersion10
    elif setup.version == HTTPVersion.H11:
        version = aiohttp.HttpVersion11
    else:
        raise RuntimeError(f"Unsupported HTTP version: {setup.version}")

    timeout = aiohttp.ClientTimeout(setup.timeout)
    files = None
    if setup.files:
        files = aiohttp.FormData()
        for name, file in setup.files:
            files.add_field(name, file[1], content_type=file[2], filename=file[0])
    async with aiohttp.ClientSession(version=version, trust_env=True) as session:
        async with session.request(
                setup.method,
                setup.url,
                data=setup.content or setup.data or files,
                json=setup.json,
                headers=setup.headers,
                timeout=timeout,
                proxy=setup.proxy,
                cookies={cookie.name: cookie.value for cookie in setup.cookies},
        ) as response:
            res = Response(
                response.status,
                headers=response.headers.copy(),
                content=await response.read(),
                request=setup,
            )
            return res


async def httpx_request(self, setup: Request) -> Response:
    async with httpx.AsyncClient(
            http2=setup.version == HTTPVersion.H2,
            proxies=setup.proxy,  # type: ignore
            follow_redirects=True,
    ) as client:
        response = await client.request(
            setup.method,
            str(setup.url),
            content=setup.content,  # type: ignore
            data=setup.data,  # type: ignore
            json=setup.json,
            files=setup.files,  # type: ignore
            headers=tuple(setup.headers.items()),
            timeout=setup.timeout,
            cookies=setup.cookies,
        )
        return Response(
            response.status_code,
            headers=response.headers.multi_items(),
            content=response.content,
            request=setup,
        )


AiohttpMixin.request = MethodType(aiohttp_request, AiohttpMixin)
HttpxMixin.request = MethodType(httpx_request, HttpxMixin)
