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
from typing import TYPE_CHECKING, Any, Optional

from src.exception import WebSourceException
from src.service import OmegaRequests

if TYPE_CHECKING:
    from nonebot.drivers import Response


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
    @abc.abstractmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        """内部方法, 异步获取 API 地址"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_default_headers(cls) -> dict[str, Any]:
        """内部方法, 获取默认 Headers"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _get_default_cookies(cls) -> dict[str, str]:
        """内部方法, 获取默认 Cookies"""
        raise NotImplementedError

    @staticmethod
    def _parse_content_json(response: "Response") -> Any:
        return OmegaRequests.parse_content_json(response)

    @classmethod
    async def _request_get(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
            timeout: int = 10,
    ) -> "Response":
        """内部方法, 使用 GET 方法请求"""
        if headers is None:
            headers = cls._get_default_headers()

        if cookies is None:
            cookies = cls._get_default_cookies()

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=cookies)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise WebSourceException(f'{response.request}, status code {response.status_code}')

        return response

    @classmethod
    async def _request_post(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            data: Optional[Any] = None,
            json: Optional[Any] = None,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
            timeout: int = 10,
    ) -> "Response":
        """内部方法, 使用 POST 方法请求"""
        if headers is None:
            headers = cls._get_default_headers()

        if cookies is None:
            cookies = cls._get_default_cookies()

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=cookies)
        response = await requests.post(url=url, params=params, data=data, json=json)
        if response.status_code != 200:
            raise WebSourceException(f'{response.request}, status code {response.status_code}')

        return response

    @classmethod
    async def _get_json(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
            timeout: int = 10,
    ) -> Any:
        """内部方法, 使用 GET 方法请求 API, 返回 json 内容"""
        response = await cls._request_get(url, params, headers=headers, cookies=cookies, timeout=timeout)
        return cls._parse_content_json(response)

    @classmethod
    async def _post_json(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            data: Optional[Any] = None,
            json: Optional[Any] = None,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
            timeout: int = 10,
    ) -> Any:
        """内部方法, 使用 POST 方法请求 API, 返回 json 内容"""
        response = await cls._request_post(
            url, params, data=data, json=json, headers=headers, cookies=cookies, timeout=timeout
        )
        return cls._parse_content_json(response)

    @classmethod
    async def _get_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
            timeout: int = 10,
    ) -> str | bytes:
        """内部方法, 使用 GET 方法获取内容"""
        response = await cls._request_get(url, params, headers=headers, cookies=cookies, timeout=timeout)
        return response.content


__all__ = [
    'BaseCommonAPI',
]
