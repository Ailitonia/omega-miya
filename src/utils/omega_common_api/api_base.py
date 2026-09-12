"""
@Author         : Ailitonia
@Date           : 2024/8/7 10:57:58
@FileName       : api_base.py
@Project        : omega-miya
@Description    : 通用 API 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
import pathlib
import re
from collections.abc import AsyncGenerator, Generator
from http.cookiejar import CookieJar
from typing import TYPE_CHECKING, Any

from multidict import CIMultiDict

from src.exception import WebSourceException
from ..omega_requests import OmegaRequests
from .types import Cookies, Timeout

if TYPE_CHECKING:
    from src.resource import BaseResource
    from .types import (
        ContentTypes,
        CookieTypes,
        DataTypes,
        FilesTypes,
        HeaderTypes,
        QueryTypes,
        Response,
        TimeoutTypes,
    )

_FILE_NAME_INVALID_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
"""Windows/POSIX 文件名保留字符与控制字符(不含路径分隔符, 分隔层级另行剥离)"""


class BaseCommonAPI(abc.ABC):
    """通用 API 基类"""

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    @abc.abstractmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        """内部方法, 获取 API 地址"""
        raise NotImplementedError

    @classmethod
    def _get_default_timeout(cls) -> 'TimeoutTypes':
        """内部方法, 获取默认 Timeout"""
        return cls._get_omega_requests_default_timeout()

    @classmethod
    @abc.abstractmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        """内部方法, 获取默认 Headers"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        """内部方法, 获取默认 Cookies"""
        raise NotImplementedError

    @staticmethod
    def _extra_set_cookies_from_response(response: 'Response') -> dict[str, str]:
        """从请求的响应头中获取 set-cookie 字段内容"""
        set_cookies: dict[str, str] = {}
        for k, v in response.headers.items():
            if k.lower() == 'set-cookie':
                item = v.split(';', maxsplit=1)[0].strip().split('=', maxsplit=1)
                if len(item) == 2:
                    set_cookies.update({item[0]: item[1]})
        return set_cookies

    @staticmethod
    def _iter_cookies_item(cookies: 'CookieTypes') -> Generator[tuple[str, str], None, None]:
        if cookies is None:
            return
        elif isinstance(cookies, (Cookies, CookieJar)):
            for item in cookies:
                yield item.name, item.value if item.value is not None else ''
        elif isinstance(cookies, dict):
            for k, v in cookies.items():
                yield k, v if v is not None else ''
        elif isinstance(cookies, list):
            for item in cookies:
                yield item[0], item[1]
        else:
            raise TypeError(f'Unsupported cookies type: {type(cookies)}')

    @staticmethod
    def _iter_headers_item(headers: 'HeaderTypes') -> Generator[tuple[str, str], None, None]:
        if headers is None:
            return
        elif isinstance(headers, (CIMultiDict, dict)):
            for k, v in headers.items():
                yield k, v if v is not None else ''
        elif isinstance(headers, list):
            for item in headers:
                yield item[0], item[1]
        else:
            raise TypeError(f'Unsupported headers type: {type(headers)}')

    @classmethod
    def _get_omega_requests_default_timeout(cls) -> 'TimeoutTypes':
        """获取 OmegaRequests 默认 Timeout"""
        return OmegaRequests.get_default_timeout()

    @classmethod
    def _get_omega_requests_default_headers(cls) -> dict[str, str]:
        """获取 OmegaRequests 默认 Headers"""
        return OmegaRequests.get_default_headers()

    @classmethod
    def _init_omega_requests(
            cls,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> OmegaRequests:
        """获取 OmegaRequests 实例"""
        if timeout is None:
            timeout = cls._get_default_timeout()

        if no_headers:
            headers = {}
        elif headers is None:
            headers = cls._get_default_headers()

        if no_cookies:
            cookies = {}
        elif cookies is None:
            cookies = cls._get_default_cookies()

        return OmegaRequests(timeout=timeout, headers=headers, cookies=cookies)

    @staticmethod
    def _parse_content_as_bytes(response: 'Response') -> bytes:
        return OmegaRequests.parse_content_as_bytes(response)

    @staticmethod
    def _parse_content_as_json(response: 'Response') -> Any:
        return OmegaRequests.parse_content_as_json(response)

    @staticmethod
    def _parse_content_as_text(response: 'Response') -> str:
        return OmegaRequests.parse_content_as_text(response)

    @staticmethod
    async def _iter_content_as_lines(
            stream_requester: AsyncGenerator['Response', Any],
            *,
            encoding: str = 'utf-8',
    ) -> AsyncGenerator[str, None]:
        async for line in OmegaRequests.iter_content_as_lines(
                stream_requester=stream_requester,
                encoding=encoding
        ):
            yield line

    @classmethod
    async def _request_get(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 GET 方法请求(仅接受 2xx 状态码响应)"""
        requests = cls._init_omega_requests(
            timeout=timeout, headers=headers, cookies=cookies, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.get(url=url, params=params)
        if not 200 <= response.status_code < 300:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _request_delete(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 DELETE 方法请求(仅接受 2xx 状态码响应)"""
        requests = cls._init_omega_requests(
            timeout=timeout, headers=headers, cookies=cookies, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.delete(url=url, params=params)
        if not 200 <= response.status_code < 300:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _request_post(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 POST 方法请求(仅接受 2xx 状态码响应)"""
        requests = cls._init_omega_requests(
            timeout=timeout, headers=headers, cookies=cookies, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.post(url=url, params=params, content=content, data=data, json=json, files=files)
        if not 200 <= response.status_code < 300:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _request_put(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 PUT 方法请求(仅接受 2xx 状态码响应)"""
        requests = cls._init_omega_requests(
            timeout=timeout, headers=headers, cookies=cookies, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.put(url=url, params=params, content=content, data=data, json=json, files=files)
        if not 200 <= response.status_code < 300:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _stream_request_get(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
            chunk_size: int = 1024,
    ) -> AsyncGenerator['Response', None]:
        """内部方法, 使用 GET 方法发起流式请求

        注意: 空响应体的错误响应(如 body 为空的 404/500)在流式请求中不产生任何分块,
        状态码校验无从执行, 调用方将观察到空流而非异常; 需要状态保证的场景请使用非流式接口
        """
        requests = cls._init_omega_requests(
            timeout=timeout, headers=headers, cookies=cookies, no_headers=no_headers, no_cookies=no_cookies
        )
        async for response in requests.stream_get(url=url, params=params, chunk_size=chunk_size):
            if not 200 <= response.status_code < 300:
                raise WebSourceException(response.status_code, str(response.request), response.content)
            yield response

    @classmethod
    async def _stream_request_post(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
            chunk_size: int = 1024,
    ) -> AsyncGenerator['Response', None]:
        """内部方法, 使用 POST 方法发起流式请求

        注意: 空响应体的错误响应(如 body 为空的 404/500)在流式请求中不产生任何分块,
        状态码校验无从执行, 调用方将观察到空流而非异常; 需要状态保证的场景请使用非流式接口
        """
        requests = cls._init_omega_requests(
            timeout=timeout, headers=headers, cookies=cookies, no_headers=no_headers, no_cookies=no_cookies
        )
        async for response in requests.stream_post(
                url=url, params=params, content=content, data=data, json=json, files=files, chunk_size=chunk_size,
        ):
            if not 200 <= response.status_code < 300:
                raise WebSourceException(response.status_code, str(response.request), response.content)
            yield response

    @classmethod
    async def _get_resource_as_json(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> Any:
        """内部方法, 使用 GET 方法请求 API, 返回 json 内容"""
        response = await cls._request_get(
            url=url, params=params,
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        return cls._parse_content_as_json(response)

    @classmethod
    async def _get_resource_as_bytes(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> bytes:
        """内部方法, 使用 GET 方法获取内容, 并转换为 bytes 类型返回"""
        response = await cls._request_get(
            url=url, params=params,
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        return cls._parse_content_as_bytes(response=response)

    @classmethod
    async def _get_resource_as_text(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> str:
        """内部方法, 使用 GET 方法获取内容, 并转换为 str 类型返回"""
        response = await cls._request_get(
            url=url, params=params,
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        return cls._parse_content_as_text(response=response)

    @classmethod
    async def _stream_get_resource_iter_lines(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
            chunk_size: int = 1024,
            encoding: str = 'utf-8',
    ) -> AsyncGenerator[str, None]:
        """内部方法, 使用 GET 方法发起流式请求获取内容, 转换为 str 类型按行迭代

        注意: 空响应体的错误响应在流式请求中不产生任何分块, 此时将静默得到零行结果
        """
        async for line in cls._iter_content_as_lines(
                stream_requester=cls._stream_request_get(
                    url=url,
                    params=params,
                    headers=headers,
                    cookies=cookies,
                    timeout=timeout,
                    no_headers=no_headers,
                    no_cookies=no_cookies,
                    chunk_size=chunk_size,
                ),
                encoding=encoding,
        ):
            yield line

    @classmethod
    async def _stream_post_acquire_iter_lines(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
            chunk_size: int = 1024,
            encoding: str = 'utf-8',
    ) -> AsyncGenerator[str, None]:
        """内部方法, 使用 POST 方法发起流式请求获取内容, 转换为 str 类型按行迭代

        注意: 空响应体的错误响应在流式请求中不产生任何分块, 此时将静默得到零行结果
        """
        async for line in cls._iter_content_as_lines(
                stream_requester=cls._stream_request_post(
                    url=url,
                    params=params,
                    content=content,
                    data=data,
                    json=json,
                    files=files,
                    headers=headers,
                    cookies=cookies,
                    timeout=timeout,
                    no_headers=no_headers,
                    no_cookies=no_cookies,
                    chunk_size=chunk_size,
                ),
                encoding=encoding,
        ):
            yield line

    @classmethod
    async def _post_acquire_as_json(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            content: 'ContentTypes' = None,
            data: 'DataTypes' = None,
            json: Any = None,
            files: 'FilesTypes' = None,
            timeout: 'TimeoutTypes' = None,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> Any:
        """内部方法, 使用 POST 方法请求 API, 返回 json 内容"""
        response = await cls._request_post(
            url=url, params=params, content=content, data=data, json=json, files=files,
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        return cls._parse_content_as_json(response)

    @classmethod
    def _clean_file_name(cls, file_name: str, *, url: str) -> str:
        """规范化下载文件名: 剥离路径层级与非法字符, 为空时回退为哈希文件名

        :param file_name: 原始文件名(可来自 URL 解析或调用方自定义)
        :param url: 下载链接(回退哈希文件名时使用)
        """
        cleaned = _FILE_NAME_INVALID_CHARS.sub('_', pathlib.PurePath(file_name).name).strip().rstrip('. ')
        if not cleaned:
            cleaned = OmegaRequests.hash_url_file_name(cls.__name__, url=url)
        return cleaned

    @classmethod
    def _clean_subdir(cls, subdir: str) -> str:
        """清理下载子目录名中的非法字符(保留路径分隔符以允许嵌套子目录)"""
        return _FILE_NAME_INVALID_CHARS.sub('_', subdir)

    @classmethod
    async def _download_resource[T: 'BaseResource'](
            cls,
            save_folder: T,
            url: str,
            params: 'QueryTypes' = None,
            *,
            trans_timeout: float = 300.0,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            subdir: str | None = None,
            ignore_exist_file: bool = False,
            no_headers: bool = False,
            no_cookies: bool = False,
            hash_file_name: bool = False,
            custom_file_name: str | None = None,
            stream_download: bool = False,
    ) -> T:
        """内部方法, 下载任意资源到本地, 默认保持原始文件名, 默认直接覆盖同名文件"""
        if custom_file_name is not None:
            file_name = custom_file_name
        elif hash_file_name:
            file_name = OmegaRequests.hash_url_file_name(cls.__name__, url=url)
        else:
            file_name = OmegaRequests.parse_url_file_name(url=url)
        file_name = cls._clean_file_name(file_name, url=url)

        if subdir is None:
            file = save_folder(file_name)
        else:
            file = save_folder(cls._clean_subdir(subdir), file_name)

        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, no_headers=no_headers, no_cookies=no_cookies
        )

        if stream_download:
            requests.set_timeout(Timeout(total=trans_timeout, connect=10, read=30))
        else:
            requests.set_timeout(Timeout(total=trans_timeout, connect=10, read=trans_timeout))

        if stream_download:
            return await requests.stream_download(url, file, params=params, ignore_exist_file=ignore_exist_file)
        else:
            return await requests.download(url, file, params=params, ignore_exist_file=ignore_exist_file)


__all__ = [
    'BaseCommonAPI',
]
