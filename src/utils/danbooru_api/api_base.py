"""
@Author         : Ailitonia
@Date           : 2024/8/1 14:46:26
@FileName       : api_base.py
@Project        : omega-miya
@Description    : API 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import Optional, Any

from nonebot.drivers import Response

from src.resource import TemporaryResource
from src.service import OmegaRequests
from .config import danbooru_config, danbooru_resource_config
from .exception import DanbooruNetworkError


class DanbooruBase(abc.ABC):
    """Danbooru 基类"""

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    @abc.abstractmethod
    def get_root_url(cls) -> str:
        """获取 API 地址"""
        raise NotImplementedError

    @staticmethod
    def _parse_content_json(response: Response) -> Any:
        return OmegaRequests.parse_content_json(response)

    @classmethod
    async def _request_get(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
    ) -> Response:
        """使用 GET 方法请求 API"""
        requests = OmegaRequests(timeout=10, headers=headers, cookies=cookies)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise DanbooruNetworkError(f'{response.request}, status code {response.status_code}')

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
    ) -> Response:
        """使用 POST 方法请求 API"""
        requests = OmegaRequests(timeout=10, headers=headers, cookies=cookies)
        response = await requests.post(url=url, params=params, data=data, json=json)
        if response.status_code != 200:
            raise DanbooruNetworkError(f'{response.request}, status code {response.status_code}')

        return response

    @classmethod
    async def get_json(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
            enable_auth: bool = False,
    ) -> Any:
        """使用 GET 方法请求 API, 返回 json 内容"""
        if headers:
            headers.update({'Content-Type': 'application/json'})
        else:
            headers = {'Content-Type': 'application/json'}

        if enable_auth and not params:
            params = danbooru_config.auth_params
        elif enable_auth and params:
            params.update(danbooru_config.auth_params)

        response = await cls._request_get(url, params, headers=headers, cookies=cookies)
        return cls._parse_content_json(response)

    @classmethod
    async def post_json(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            data: Optional[Any] = None,
            json: Optional[Any] = None,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
            enable_auth: bool = False,
    ) -> Any:
        """使用 POST 方法请求 API, 返回 json 内容"""
        if headers:
            headers.update({'Content-Type': 'application/json'})
        else:
            headers = {'Content-Type': 'application/json'}

        if enable_auth and not params:
            params = danbooru_config.auth_params
        elif enable_auth and params:
            params.update(danbooru_config.auth_params)

        response = await cls._request_post(url, params, data=data, json=json, headers=headers, cookies=cookies)
        return cls._parse_content_json(response)

    @classmethod
    async def get_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
    ) -> str | bytes:
        """使用 GET 方法获取内容"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()

        headers.update({
            'origin': f'{cls.get_root_url()}',
            'referer': f'{cls.get_root_url()}/'
        })

        response = await cls._request_get(url, params, headers=headers, cookies=cookies)
        return response.content

    @classmethod
    async def download_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
            timeout: int = 60,
            folder_name: str | None = None,
            ignore_exist_file: bool = False
    ) -> TemporaryResource:
        """下载资源到本地, 保持原始文件名, 默认直接覆盖同名文件"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()

        headers.update({
            'origin': f'{cls.get_root_url()}',
            'referer': f'{cls.get_root_url()}/'
        })

        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        if folder_name is None:
            file = danbooru_resource_config.default_download_folder(original_file_name)
        else:
            file = danbooru_resource_config.default_download_folder(folder_name, original_file_name)

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=cookies)
        return await requests.download(url=url, file=file, params=params, ignore_exist_file=ignore_exist_file)


__all__ = [
    'DanbooruBase',
]
