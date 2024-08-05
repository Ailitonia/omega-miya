"""
@Author         : Ailitonia
@Date           : 2024/6/12 上午1:07
@FileName       : requests
@Project        : nonebot2_miya
@Description    : OmegaRequests, 通过对 ForwardDriver 的二次封装实现 HttpClient 功能
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import hashlib
import pathlib
from asyncio.exceptions import TimeoutError
from contextlib import asynccontextmanager
from copy import deepcopy
from typing import AsyncGenerator, Optional, Any
from urllib.parse import urlparse, unquote

import ujson
from nonebot import get_driver, logger
from nonebot.drivers import (ForwardDriver, HTTPClientMixin, HTTPClientSession, Response, Request,
                             WebSocket, WebSocketClientMixin)
from nonebot.internal.driver.model import QueryTypes, HeaderTypes, CookieTypes, ContentTypes, DataTypes, FilesTypes

from src.exception import WebSourceException
from src.resource import TemporaryResource
from .config import http_proxy_config


class ExceededAttemptError(WebSourceException):
    """重试次数超过限制异常"""


class OmegaRequests(object):
    """对 ForwardDriver 二次封装实现的 HttpClient"""

    _default_retry_limit: int = 3
    _default_timeout_time: float = 10.0
    _default_headers: dict[str, str] = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN,zh;q=0.9',
        'dnt': '1',
        'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/125.0.0.0 Safari/537.36'
    }

    def __init__(
            self,
            *,
            timeout: Optional[float] = None,
            headers: HeaderTypes = None,
            cookies: CookieTypes = None,
            retry: Optional[int] = None
    ):
        self.driver = get_driver()
        if not isinstance(self.driver, ForwardDriver):
            raise RuntimeError(
                f"Current driver {self.driver.type} doesn't support forward connections! "
                "OmegaRequests need a ForwardDriver to work."
            )

        self.timeout = self._default_timeout_time if timeout is None else timeout
        self.headers = self._default_headers if headers is None else headers
        self.cookies = cookies
        self.retry_limit = self._default_retry_limit if retry is None else retry

    @staticmethod
    def parse_content_json(response: Response, **kwargs) -> Any:
        """解析 Response Content 为 Json"""
        return ujson.loads(response.content, **kwargs)

    @staticmethod
    def parse_content_text(response: Response, encoding: str = 'utf-8') -> str | None:
        """解析 Response Content 为字符串"""
        if isinstance(response.content, bytes):
            return response.content.decode(encoding=encoding)
        else:
            return response.content

    @classmethod
    def parse_url_file_name(cls, url: str) -> str:
        """尝试解析 url 对应的文件名"""
        parsed_url = urlparse(url=url, allow_fragments=True)
        original_file_name = pathlib.PurePath(unquote(parsed_url.path)).name
        return original_file_name

    @classmethod
    def hash_url_file_name(cls, *prefix: str, url: str) -> str:
        """尝试解析 url 对应的文件后缀名并用 hash 和前缀代替"""
        parsed_url = urlparse(url=url, allow_fragments=True)
        name_hash = hashlib.sha256(url.encode(encoding='utf8')).hexdigest()
        name_suffix = pathlib.PurePath(unquote(parsed_url.path)).suffix
        name_prefix = '_'.join(prefix) if prefix else 'file'
        new_name = f'{name_prefix}_{name_hash}{name_suffix}'
        return new_name

    @classmethod
    def get_default_headers(cls) -> dict[str, str]:
        return deepcopy(cls._default_headers)

    def get_session(self, params: Optional[QueryTypes] = None, use_proxy: bool = True) -> HTTPClientSession:
        if not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(
                f"Current driver {self.driver.type} doesn't support forward http connections! "
                "OmegaRequests need a HTTPClient Driver to work."
            )
        return self.driver.get_session(
            params=params,
            headers=self.headers,
            cookies=self.cookies,
            timeout=self.timeout,
            proxy=http_proxy_config.proxy_url if use_proxy else None
        )

    async def request(self, setup: Request) -> Response:
        """装饰原 request 方法, 自动重试"""
        if not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(
                f"Current driver {self.driver.type} doesn't support forward http connections! "
                "OmegaRequests need a HTTPClient Driver to work."
            )

        attempts_num = 0
        final_exception = None
        while attempts_num < self.retry_limit:
            try:
                logger.opt(colors=True).trace(f'<lc>Omega Requests</lc> | Starting request <ly>{setup!r}</ly>')
                return await self.driver.request(setup=setup)
            except TimeoutError as e:
                logger.opt(colors=True).debug(
                    f'<lc>Omega Requests</lc> | <ly>{setup!r} failed on the {attempts_num + 1} attempt</ly> <c>></c> '
                    f'<r>TimeoutError</r>'
                )
                final_exception = e
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'<lc>Omega Requests</lc> | <ly>{setup!r} failed on the {attempts_num + 1} attempt</ly> <c>></c> '
                    f'<r>Exception {e.__class__.__name__}</r>: {e}')
                final_exception = e
            finally:
                attempts_num += 1
        else:
            logger.opt(colors=True).error(
                f'<lc>Omega Requests</lc> | <ly>{setup!r} failed with {attempts_num} times attempts</ly> <c>></c> '
                f'<r>Exception ExceededAttemptError</r>: The number of attempts exceeds limit with final exception: '
                f'<r>{final_exception.__class__.__name__}</r>: {final_exception}')
            raise ExceededAttemptError('The number of attempts exceeds limit.')

    @asynccontextmanager
    async def websocket(
            self,
            method: str,
            url: str,
            *,
            params: QueryTypes = None,
            headers: HeaderTypes = None,
            cookies: CookieTypes = None,
            content: ContentTypes = None,
            data: DataTypes = None,
            json: Any = None,
            files: FilesTypes = None,
            timeout: Optional[float] = None,
            use_proxy: bool = True
    ) -> AsyncGenerator[WebSocket, None]:
        """建立 websocket 连接"""
        if not isinstance(self.driver, WebSocketClientMixin):
            raise RuntimeError(
                f"Current driver {self.driver.type} doesn't support forward webSocket connections! "
                "OmegaRequests need a WebSocketClient Driver to work."
            )

        setup = Request(
            method=method,
            url=url,
            params=params,
            headers=self.headers if headers is None else headers,
            cookies=self.cookies if cookies is None else cookies,
            content=content,
            data=data,
            json=json,
            files=files,
            timeout=self.timeout if timeout is None else timeout,
            proxy=http_proxy_config.proxy_url if use_proxy else None
        )

        async with self.driver.websocket(setup=setup) as ws:
            yield ws

    async def get(
            self,
            url: str,
            *,
            params: QueryTypes = None,
            headers: HeaderTypes = None,
            cookies: CookieTypes = None,
            content: ContentTypes = None,
            data: DataTypes = None,
            json: Any = None,
            files: FilesTypes = None,
            timeout: Optional[float] = None,
            use_proxy: bool = True
    ) -> Response:
        setup = Request(
            method='GET',
            url=url,
            params=params,
            headers=self.headers if headers is None else headers,
            cookies=self.cookies if cookies is None else cookies,
            content=content,
            data=data,
            json=json,
            files=files,
            timeout=self.timeout if timeout is None else timeout,
            proxy=http_proxy_config.proxy_url if use_proxy else None
        )
        return await self.request(setup=setup)

    async def post(
            self,
            url: str,
            *,
            params: QueryTypes = None,
            headers: HeaderTypes = None,
            cookies: CookieTypes = None,
            content: ContentTypes = None,
            data: DataTypes = None,
            json: Any = None,
            files: FilesTypes = None,
            timeout: Optional[float] = None,
            use_proxy: bool = True
    ) -> Response:
        setup = Request(
            method='POST',
            url=url,
            params=params,
            headers=self.headers if headers is None else headers,
            cookies=self.cookies if cookies is None else cookies,
            content=content,
            data=data,
            json=json,
            files=files,
            timeout=self.timeout if timeout is None else timeout,
            proxy=http_proxy_config.proxy_url if use_proxy else None
        )
        return await self.request(setup=setup)

    async def download(
            self,
            url: str,
            file: TemporaryResource,
            *,
            params: QueryTypes = None,
            ignore_exist_file: bool = False,
            **kwargs
    ) -> TemporaryResource:
        """下载文件

        :param url: 链接
        :param file: 下载目标路径
        :param params: 请求参数
        :param ignore_exist_file: 忽略已存在文件
        :return: 下载目标路径
        """
        if ignore_exist_file and file.is_file:
            return file

        response = await self.get(url=url, params=params, **kwargs)

        if response.status_code != 200:
            logger.opt(colors=True).error(f'<lc>Omega Requests</lc> | Download <ly>{url!r}</ly> '
                                          f'to {file!r} failed with code <lr>{response.status_code!r}</lr>')
            raise WebSourceException(f'Download {url!r} to {file!r} failed with code {response.status_code!r}')

        if isinstance(response.content, str):
            response.content = response.content.encode(encoding='utf-8')

        async with file.async_open(mode='wb') as af:
            await af.write(response.content)

        return file


__all__ = [
    'OmegaRequests',
    'Request',
    'Response',
    'WebSocket'
]
