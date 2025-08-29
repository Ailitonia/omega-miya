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
import re
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from nonebot.utils import run_sync

from src.exception import WebSourceException
from .cf_utils import cloudflare_clearance_config
from .helpers import iter_cookies_types_item, iter_headers_types_item
from ..omega_requests import OmegaRequests

if TYPE_CHECKING:
    from src.resource import TemporaryResource

    from .types import (
        ContentTypes,
        CookieTypes,
        DataTypes,
        FilesTypes,
        HeaderTypes,
        QueryTypes,
        Response,
        Timeout,
        TimeoutTypes,
    )


class BaseCommonAPI(abc.ABC):
    """通用 API 基类"""

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        """内部方法, 异步获取 API 地址"""
        return await run_sync(cls._get_root_url)(*args, **kwargs)

    @classmethod
    @abc.abstractmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        """内部方法, 获取 API 地址"""
        raise NotImplementedError

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

    @classmethod
    def _extra_set_cookies_from_response(cls, response: 'Response') -> dict[str, str]:
        """从请求的响应头中获取 set-cookie 字段内容"""
        set_cookies: dict[str, str] = {}
        for k, v in response.headers.items():
            if re.match(re.compile('set-cookie', re.IGNORECASE), k):
                item = v.split(';', maxsplit=1)[0].strip().split('=', maxsplit=1)
                if len(item) == 2:
                    set_cookies.update({item[0]: item[1]})
        return set_cookies

    @classmethod
    def _get_default_timeout(cls) -> 'Timeout':
        """内部方法, 获取默认 Timeout"""
        return cls._get_omega_requests_default_timeout()

    @classmethod
    def _get_omega_requests_default_headers(cls) -> dict[str, str]:
        """获取 OmegaRequests 默认 Headers"""
        return OmegaRequests.get_default_headers()

    @classmethod
    def _get_omega_requests_default_timeout(cls) -> 'Timeout':
        """获取 OmegaRequests 默认 Timeout"""
        return OmegaRequests.get_default_timeout()

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        """内部方法, 判断是否需要请求加载 Cloudflare Clearance 配置"""
        return False

    @classmethod
    def _init_omega_requests(
            cls,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> OmegaRequests:
        """获取 OmegaRequests 实例"""
        if no_cookies:
            cookies = {}
        elif cookies is None:
            cookies = cls._get_default_cookies()

        if no_headers:
            headers = {}
        elif headers is None:
            headers = cls._get_default_headers()

        if timeout is None:
            timeout = cls._get_default_timeout()

        # 处理加载 Cloudflare Clearance 参数
        if cls._load_cloudflare_clearance():
            domain_cloudflare_clearance = cloudflare_clearance_config.get_url_config(url=cls._get_root_url())
            if domain_cloudflare_clearance is not None:
                headers = dict(iter_headers_types_item(headers))
                headers.update(domain_cloudflare_clearance.get_headers())
                cookies = dict(iter_cookies_types_item(cookies))
                cookies.update(domain_cloudflare_clearance.get_cookies())

        return OmegaRequests(headers=headers, cookies=cookies, timeout=timeout)

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
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 GET 方法请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _request_delete(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 DELETE 方法请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.delete(url=url, params=params)
        if response.status_code != 200:
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
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 POST 方法请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.post(url=url, params=params, content=content, data=data, json=json, files=files)
        if response.status_code != 200:
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
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
    ) -> 'Response':
        """内部方法, 使用 PUT 方法请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        response = await requests.put(url=url, params=params, content=content, data=data, json=json, files=files)
        if response.status_code != 200:
            raise WebSourceException(response.status_code, str(response.request), response.content)

        return response

    @classmethod
    async def _stream_request_get(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
            chunk_size: int = 1024,
    ) -> AsyncGenerator['Response', None]:
        """内部方法, 使用 GET 方法发起流式请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        async for response in requests.stream_get(url=url, params=params, chunk_size=chunk_size):
            if response.status_code != 200:
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
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
            chunk_size: int = 1024,
    ) -> AsyncGenerator['Response', None]:
        """内部方法, 使用 POST 方法发起流式请求"""
        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, timeout=timeout, no_headers=no_headers, no_cookies=no_cookies
        )
        async for response in requests.stream_post(
                url=url, params=params, content=content, data=data, json=json, files=files, chunk_size=chunk_size,
        ):
            if response.status_code != 200:
                raise WebSourceException(response.status_code, str(response.request), response.content)
            yield response

    @classmethod
    async def _get_resource_as_json(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
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
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
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
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
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
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
            chunk_size: int = 1024,
            encoding: str = 'utf-8',
    ) -> AsyncGenerator[str, None]:
        """内部方法, 使用 GET 方法发起流式请求获取内容, 转换为 str 类型按行迭代"""
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
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
            no_headers: bool = False,
            no_cookies: bool = False,
            chunk_size: int = 1024,
            encoding: str = 'utf-8',
    ) -> AsyncGenerator[str, None]:
        """内部方法, 使用 POST 方法发起流式请求获取内容, 转换为 str 类型按行迭代"""
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
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            timeout: 'TimeoutTypes' = None,
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
    async def _download_resource(
            cls,
            save_folder: 'TemporaryResource',
            url: str,
            params: 'QueryTypes' = None,
            *,
            headers: 'HeaderTypes' = None,
            cookies: 'CookieTypes' = None,
            trans_timeout: float = 300.0,
            subdir: str | None = None,
            ignore_exist_file: bool = False,
            no_headers: bool = False,
            no_cookies: bool = False,
            hash_file_name: bool = False,
            custom_file_name: str | None = None,
            stream_download: bool = False,
    ) -> 'TemporaryResource':
        """内部方法, 下载任意资源到本地, 保持原始文件名, 默认直接覆盖同名文件"""
        if custom_file_name is not None:
            file_name = custom_file_name
        elif hash_file_name:
            file_name = OmegaRequests.hash_url_file_name(url=url)
        else:
            file_name = OmegaRequests.parse_url_file_name(url=url)

        if subdir is None:
            file = save_folder(file_name)
        else:
            file = save_folder(subdir, file_name)

        requests = cls._init_omega_requests(
            headers=headers, cookies=cookies, no_headers=no_headers, no_cookies=no_cookies
        )

        if stream_download:
            requests.set_timeout(total=trans_timeout, connect=10, read=20)
        else:
            requests.set_timeout(total=trans_timeout, connect=10, read=trans_timeout)

        if stream_download:
            return await requests.stream_download(url, file, params=params, ignore_exist_file=ignore_exist_file)
        else:
            return await requests.download(url, file, params=params, ignore_exist_file=ignore_exist_file)


__all__ = [
    'BaseCommonAPI',
]
