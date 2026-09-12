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
import re
from asyncio.exceptions import TimeoutError as AsyncTimeoutError
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import unquote, urlparse

import ujson
from nonebot import get_driver, logger
from nonebot.drivers import (
    ForwardDriver,
    HTTPClientMixin,
    Request,
    WebSocketClientMixin,
)

from src.exception import WebSourceException
from .config import omega_requests_config

if TYPE_CHECKING:
    from src.resource import BaseResource
    from .types import (
        ContentTypes,
        CookieTypes,
        DataTypes,
        FilesTypes,
        HTTPClientSession,
        HeaderTypes,
        QueryTypes,
        Response,
        TimeoutTypes,
        WebSocket,
    )

_URL_TRAILING_PUNCTUATION = ".,;:!?)]}>'\"`，。、；：？！）】》「」『』"
"""从文本提取 URL 时需剥离的尾随标点(中英文句读、成对符号右半部分等几乎不可能属于 URL 的字符)"""


class OmegaRequests:
    """对 ForwardDriver 二次封装实现的 HttpClient"""

    def __init__(
            self,
            *,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            retry: int | None = None,
    ):
        self.driver = get_driver()
        if not isinstance(self.driver, ForwardDriver):
            raise RuntimeError(
                f"Current driver {self.driver.type} doesn't support forward connections! "
                'OmegaRequests need a ForwardDriver to work.'
            )

        self.timeout = omega_requests_config.default_timeout if timeout is None else timeout
        self.headers = omega_requests_config.default_headers if headers is None else headers
        self.headers = None if not self.headers else self.headers  # 处理空值 headers
        self.cookies = None if not cookies else cookies
        self.retry_limit = omega_requests_config.default_retry_limit if retry is None else retry
        if self.retry_limit < 1:
            # retry_limit 语义为最大总尝试次数, 小于 1 时不会发起任何请求, 属于配置错误, 立即失败
            raise ValueError(f'retry must be a positive integer, got {self.retry_limit}')

    def set_timeout(self, timeout: 'TimeoutTypes') -> None:
        self.timeout = timeout

    def set_headers(self, headers: 'HeaderTypes') -> None:
        self.headers = headers

    def set_cookies(self, cookies: 'CookieTypes') -> None:
        self.cookies = cookies

    @staticmethod
    def parse_content_as_bytes(response: 'Response', encoding: str = 'utf-8') -> bytes:
        """解析 Response Content 为 bytes"""
        if isinstance(response.content, str):
            return response.content.encode(encoding=encoding)
        elif isinstance(response.content, bytes):
            return response.content
        else:
            return b'' if response.content is None else bytes(response.content)

    @staticmethod
    def parse_content_as_json(response: 'Response', **kwargs) -> Any:
        """解析 Response Content 为 Json"""
        if response.content is None:
            raise ValueError('content of response is None')
        return ujson.loads(response.content, **kwargs)

    @staticmethod
    def parse_content_as_text(response: 'Response', encoding: str = 'utf-8') -> str:
        """解析 Response Content 为字符串"""
        if isinstance(response.content, str):
            return response.content
        elif isinstance(response.content, bytes):
            return response.content.decode(encoding=encoding)
        else:
            return '' if response.content is None else str(response.content)

    @classmethod
    async def iter_content_as_lines(
            cls,
            stream_requester: AsyncGenerator['Response', Any],
            *,
            encoding: str = 'utf-8',
    ) -> AsyncGenerator[str, None]:
        """解析流式请求, 按文本行迭代"""
        buffer: bytes = b''
        trailing_cr: bool = False

        async for response in stream_requester:
            content = cls.parse_content_as_bytes(response, encoding=encoding)

            # Always push a trailing `\r` into the next iteration.
            if trailing_cr:
                content = b'\r' + content
                trailing_cr = False
            if content.endswith(b'\r'):
                trailing_cr = True
                content = content[:-1]

            if not content:
                continue

            trailing_newline = content.endswith(b'\n') or content.endswith(b'\r')
            lines = content.splitlines()

            if len(lines) == 1 and not trailing_newline:
                # No new lines, buffer the input and continue.
                buffer += lines[0]
                continue

            if buffer:
                # Include any existing buffer in the first portion of the splitlines result.
                lines[0] = buffer + lines[0]
                buffer = b''

            if not trailing_newline:
                # If the last segment of splitlines is not newline terminated,
                # then drop it from our output and start a new buffer.
                buffer = lines.pop()

            for line in lines:
                yield line.decode(encoding=encoding)

        # 流末尾孤立的 \r 是最后一行的终止符, 不属于行内容, 丢弃且不产出额外空行
        if buffer:
            yield buffer.decode(encoding=encoding)

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
    def get_url_in_text(cls, text: str) -> list[str]:
        """匹配并提取字符串中的合法 URL"""
        pattern = re.compile(
            r'https?://'  # 协议
            r'(?:'
            r'(?:[a-zA-Z0-9-]+\.)+(?:xn--[a-zA-Z0-9-]{2,}|[a-zA-Z]{2,})'  # 域名(punycode 或字母后缀)
            r'|(?:\d{1,3}\.){3}\d{1,3}'  # 或 IPv4 地址
            r')'
            r'(?::\d{1,5})?'  # 可选端口
            r'(?:/[\x21-\x7e]*)?'  # 可选路径(仅可打印 ASCII, 避免吞入紧随 URL 的中文等非 URL 文本)
        )
        matched_urls = [x.rstrip(_URL_TRAILING_PUNCTUATION) for x in re.findall(pattern, text)]
        parsed_urls = [urlparse(str(x)) for x in matched_urls]
        return [
            x.geturl() for x in parsed_urls
            if all((x.scheme in ['http', 'https'], x.netloc))
        ]

    @classmethod
    def get_default_headers(cls) -> dict[str, str]:
        """获取默认 Headers 内容"""
        return omega_requests_config.default_headers

    @classmethod
    def get_default_timeout(cls) -> 'TimeoutTypes':
        """获取默认超时配置"""
        return omega_requests_config.default_timeout

    def get_session(self, params: Optional['QueryTypes'] = None, use_proxy: bool = True) -> 'HTTPClientSession':
        """获取一个 HTTP 会话"""
        if not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(
                f"Current driver {self.driver.type} doesn't support forward http connections! "
                'OmegaRequests need a HTTPClient Driver to work.'
            )
        return self.driver.get_session(
            params=params,
            headers=self.headers,
            cookies=self.cookies,
            timeout=self.timeout,
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )

    async def request(self, setup: Request) -> 'Response':
        """发送一个 HTTP 请求, 自动重试"""
        if not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(
                f"Current driver {self.driver.type} doesn't support forward http connections! "
                'OmegaRequests need a HTTPClient Driver to work.'
            )

        # 处理自动重试
        attempts_num = 0
        final_exception = None
        while attempts_num < self.retry_limit:
            try:
                logger.opt(colors=True).trace(f'<lc>Omega Requests</lc> | Beginning <ly>{setup}</ly>')
                return await self.driver.request(setup=setup)
            except AsyncTimeoutError as e:
                logger.opt(colors=True).debug(
                    f'<lc>Omega Requests</lc> | <ly>{setup} failed {attempts_num + 1} times</ly> <c>></c> '
                    '<r>TimeoutError</r>'
                )
                final_exception = e
            except Exception as e:
                logger.opt(colors=True).warning(
                    f'<lc>Omega Requests</lc> | <ly>{setup} failed {attempts_num + 1} times</ly> <c>></c> '
                    f'<r>Exception {e.__class__.__name__}</r>: {e}'
                )
                final_exception = e
            finally:
                attempts_num += 1

        logger.opt(colors=True).error(
            f'<lc>Omega Requests</lc> | <ly>{setup} failed {attempts_num} times</ly> <c>></c> '
            '<r>ExceededAttemptLimited</r>: The number of attempts exceeds limit with final exception: '
            f'<r>{final_exception.__class__.__name__}</r>: {final_exception}'
        )
        raise WebSourceException(500, 'The number of attempts exceeds limit.') from final_exception

    async def stream_request(
            self,
            setup: Request,
            *,
            chunk_size: int = 1024,
    ) -> AsyncGenerator['Response', None]:
        """发送一个 HTTP 流式请求"""
        if not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(
                f"Current driver {self.driver.type} doesn't support forward http connections! "
                'OmegaRequests need a HTTPClient Driver to work.'
            )

        try:
            logger.opt(colors=True).trace(f'<lc>Omega Requests</lc> | Beginning <ly>{setup}</ly>')
            async for response in self.driver.stream_request(setup, chunk_size=chunk_size):
                yield response
        except AsyncTimeoutError as e:
            logger.opt(colors=True).debug(
                f'<lc>Omega Requests</lc> | <ly>{setup} failed</ly> <c>></c> <r>TimeoutError</r>'
            )
            raise WebSourceException(504, 'Timeout') from e
        except Exception as e:
            logger.opt(colors=True).warning(
                f'<lc>Omega Requests</lc> | <ly>{setup} failed</ly> <c>></c> '
                f'<r>Exception {e.__class__.__name__}</r>: {e}'
            )
            raise WebSourceException(500, f'{e.__class__.__name__}, {e}') from e

    @asynccontextmanager
    async def websocket(
            self,
            method: str,
            url: str,
            *,
            params: 'QueryTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            use_proxy: bool = True,
    ) -> AsyncGenerator['WebSocket', None]:
        """建立 websocket 连接"""
        if not isinstance(self.driver, WebSocketClientMixin):
            raise RuntimeError(
                f"Current driver {self.driver.type} doesn't support forward webSocket connections! "
                'OmegaRequests need a WebSocketClient Driver to work.'
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
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )

        async with self.driver.websocket(setup=setup) as ws:
            yield ws

    async def get(
            self,
            url: str,
            *,
            params: 'QueryTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            use_proxy: bool = True,
    ) -> 'Response':
        """发送一个 GET 请求"""
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
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )
        return await self.request(setup=setup)

    async def post(
            self,
            url: str,
            *,
            params: 'QueryTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            use_proxy: bool = True,
    ) -> 'Response':
        """发送一个 POST 请求"""
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
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )
        return await self.request(setup=setup)

    async def put(
            self,
            url: str,
            *,
            params: 'QueryTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            use_proxy: bool = True,
    ) -> 'Response':
        """发送一个 PUT 请求"""
        setup = Request(
            method='PUT',
            url=url,
            params=params,
            headers=self.headers if headers is None else headers,
            cookies=self.cookies if cookies is None else cookies,
            content=content,
            data=data,
            json=json,
            files=files,
            timeout=self.timeout if timeout is None else timeout,
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )
        return await self.request(setup=setup)

    async def delete(
            self,
            url: str,
            *,
            params: 'QueryTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            use_proxy: bool = True,
    ) -> 'Response':
        """发送一个 DELETE 请求"""
        setup = Request(
            method='DELETE',
            url=url,
            params=params,
            headers=self.headers if headers is None else headers,
            cookies=self.cookies if cookies is None else cookies,
            content=content,
            data=data,
            json=json,
            files=files,
            timeout=self.timeout if timeout is None else timeout,
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )
        return await self.request(setup=setup)

    async def stream_get(
            self,
            url: str,
            *,
            params: 'QueryTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            use_proxy: bool = True,
            chunk_size: int = 1024,
    ) -> AsyncGenerator['Response', None]:
        """发送一个 GET 流式请求"""
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
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )
        async for response in self.stream_request(setup, chunk_size=chunk_size):
            yield response

    async def stream_get_iter_lines(
            self,
            url: str,
            *,
            params: 'QueryTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            use_proxy: bool = True,
            chunk_size: int = 1024,
            encoding: str = 'utf-8',
    ) -> AsyncGenerator[str, None]:
        """发送一个 GET 流式请求, 按行迭代"""
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
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )
        async for line in self.iter_content_as_lines(
                stream_requester=self.stream_request(setup, chunk_size=chunk_size),
                encoding=encoding,
        ):
            yield line

    async def stream_post(
            self,
            url: str,
            *,
            params: 'QueryTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            use_proxy: bool = True,
            chunk_size: int = 1024,
    ) -> AsyncGenerator['Response', None]:
        """发送一个 POST 流式请求"""
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
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )
        async for response in self.stream_request(setup, chunk_size=chunk_size):
            yield response

    async def stream_post_iter_lines(
            self,
            url: str,
            *,
            params: 'QueryTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            use_proxy: bool = True,
            chunk_size: int = 1024,
            encoding: str = 'utf-8',
    ) -> AsyncGenerator[str, None]:
        """发送一个 POST 流式请求, 按行迭代"""
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
            proxy=omega_requests_config.proxy_url if use_proxy else None
        )
        async for line in self.iter_content_as_lines(
                stream_requester=self.stream_request(setup, chunk_size=chunk_size),
                encoding=encoding,
        ):
            yield line

    async def download[T: 'BaseResource'](
            self,
            url: str,
            file: T,
            *,
            params: 'QueryTypes' = None,
            ignore_exist_file: bool = False,
            **kwargs,
    ) -> T:
        """下载文件

        :param url: 链接
        :param file: 下载目标路径
        :param params: 请求参数
        :param ignore_exist_file: 忽略已存在文件
        :return: 下载目标路径
        """
        if ignore_exist_file and file.is_file:
            logger.opt(colors=True).info(
                f'<lc>Omega Requests</lc> | Download <ly>{url}</ly> to {file} ignored by exist file'
            )
            return file

        logger.opt(colors=True).debug(
            f'<lc>Omega Requests</lc> | Start downloading <ly>{url}</ly> to {file}'
        )

        response = await self.get(url=url, params=params, **kwargs)

        if response.status_code != 200:
            logger.opt(colors=True).error(
                f'<lc>Omega Requests</lc> | Download <ly>{url}</ly> to {file} '
                f'failed with code <lr>{response.status_code}</lr>'
            )
            raise WebSourceException(
                response.status_code,
                f'Download {url} to {file} failed with code {response.status_code}'
            )

        async with file.async_open(mode='wb') as af:
            await af.write(self.parse_content_as_bytes(response=response))

        logger.opt(colors=True).success(
            f'<lc>Omega Requests</lc> | Download <ly>{url}</ly> to {file} completed'
        )
        return file

    async def stream_download[T: 'BaseResource'](
            self,
            url: str,
            file: T,
            *,
            params: 'QueryTypes' = None,
            chunk_size: int = 1024 * 16,
            ignore_exist_file: bool = False,
            **kwargs,
    ) -> T:
        """流式下载文件, 支持断点续传

        :param url: 链接
        :param file: 下载目标路径
        :param params: 请求参数
        :param chunk_size: 分块大小, 默认 16 KB
        :param ignore_exist_file: 忽略已存在文件
        :return: 下载目标路径
        """
        if ignore_exist_file and file.is_file:
            logger.opt(colors=True).info(
                f'<lc>Omega Requests</lc> | Download <ly>{url}</ly> to {file} ignored by exist file'
            )
            return file

        # 创建临时文件路径, 准备断点续传
        clear_restart = False
        temp_file = file.with_name(name=f'{file.name}.DOWNLOADING_TMP')
        start_byte = temp_file.file_size if temp_file.is_file else 0

        # 合并请求头: 实例默认 < 调用方传入 < 断点续传 Range(内部控制头优先)
        extra_headers = kwargs.pop('headers', None)
        headers = dict(self.headers if self.headers is not None else {})
        if extra_headers:
            headers.update(dict(extra_headers))
        if start_byte > 0:
            headers.update({'Range': f'bytes={start_byte}-'})

        logger.opt(colors=True).debug(
            f'<lc>Omega Requests</lc> | Starting stream download <ly>{url}</ly> to temp {temp_file}'
        )

        # 追加写入模式打开文件, 分块写入
        received_any = False
        async with temp_file.async_open(mode='ab') as af:
            async for response in self.stream_get(
                    url=url, params=params, headers=headers, chunk_size=chunk_size, **kwargs
            ):
                received_any = True
                if start_byte > 0 and response.status_code == 206:
                    pass
                elif start_byte > 0 and response.status_code != 206:
                    logger.opt(colors=True).warning(
                        f'<lc>Omega Requests</lc> | Stream download <ly>{url}</ly> to temp {temp_file} failed, '
                        'the server does not support breakpoint resuming, and will re-download'
                    )
                    clear_restart = True
                    break
                elif response.status_code != 200:
                    logger.opt(colors=True).error(
                        f'<lc>Omega Requests</lc> | Stream download <ly>{url}</ly> to temp {temp_file} '
                        f'failed with code <lr>{response.status_code}</lr>'
                    )
                    raise WebSourceException(
                        response.status_code,
                        f'Download {url} to temp {temp_file} failed with code {response.status_code}'
                    )

                await af.write(self.parse_content_as_bytes(response=response))

        # 空响应体的响应在流式请求中不产生任何分块, 状态码无从获知, 需以相同请求(含 Range 头)额外核验
        if not clear_restart and not received_any:
            verify_response = await self.get(url=url, params=params, headers=headers, **kwargs)
            if start_byte > 0 and verify_response.status_code == 206:
                pass  # 续传余量为零, 临时文件已是完整内容
            elif start_byte > 0 and verify_response.status_code in (200, 416):
                # 服务端忽略 Range 或临时文件已超界, 清空后重新下载
                logger.opt(colors=True).warning(
                    f'<lc>Omega Requests</lc> | Stream download <ly>{url}</ly> to temp {temp_file} failed, '
                    'the server does not support breakpoint resuming, and will re-download'
                )
                clear_restart = True
            elif verify_response.status_code != 200:
                logger.opt(colors=True).error(
                    f'<lc>Omega Requests</lc> | Stream download <ly>{url}</ly> to temp {temp_file} '
                    f'failed with code <lr>{verify_response.status_code}</lr>'
                )
                raise WebSourceException(
                    verify_response.status_code,
                    f'Download {url} to temp {temp_file} failed with code {verify_response.status_code}'
                )

        # 如果需要重新下载, 清空文件并重新请求
        if clear_restart:
            file.remove(missing_ok=True)
            temp_file.remove(missing_ok=True)
            # 移除本次续传的 Range 头, 避免全新下载时误用旧的断点位置
            headers.pop('Range', None)
            return await self.stream_download(
                url, file, params=params, chunk_size=chunk_size, ignore_exist_file=False, headers=headers, **kwargs,
            )

        # 替换临时文件
        final_file = temp_file.replace(target=file.path)
        logger.opt(colors=True).success(
            f'<lc>Omega Requests</lc> | Download <ly>{url}</ly> to {final_file} completed'
        )
        return final_file


__all__ = [
    'OmegaRequests',
]
