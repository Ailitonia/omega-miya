"""
@Author         : Ailitonia
@Date           : 2024/7/30 10:13:37
@FileName       : api_base.py
@Project        : omega-miya
@Description    : pixiv api 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import Optional, Any

from src.resource import TemporaryResource
from src.service import OmegaRequests
from .config import pixiv_config, pixiv_resource_config
from .exception import PixivNetworkError


class PixivApiBase(abc.ABC):
    """Pixiv API 基类"""
    _root_url: str = 'https://www.pixiv.net'

    def __repr__(self) -> str:
        return self.__class__.__name__

    @classmethod
    async def request_json(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None
    ) -> Any:
        """请求 api 并返回 json 数据"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({'referer': 'https://www.pixiv.net/'})

        requests = OmegaRequests(timeout=10, headers=headers, cookies=pixiv_config.cookie_phpssid)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise PixivNetworkError(f'{response.request}, status code {response.status_code}')

        return OmegaRequests.parse_content_json(response)

    @classmethod
    async def request_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 45
    ) -> str | bytes | None:
        """请求原始资源内容"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({'referer': 'https://www.pixiv.net/'})

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=pixiv_config.cookie_phpssid)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise PixivNetworkError(f'{response.request}, status code {response.status_code}')

        return response.content

    @classmethod
    async def download_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            timeout: int = 60
    ) -> TemporaryResource:
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({'referer': 'https://www.pixiv.net/'})

        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        file = pixiv_resource_config.default_download_folder(original_file_name)
        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=pixiv_config.cookie_phpssid)

        return await requests.download(url=url, file=file, params=params)


__all__ = [
    'PixivApiBase'
]
