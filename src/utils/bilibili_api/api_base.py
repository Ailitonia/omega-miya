"""
@Author         : Ailitonia
@Date           : 2024/5/30 上午12:37
@FileName       : api_base
@Project        : nonebot2_miya
@Description    : bilibili api 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal, Optional, Any

from src.resource import TemporaryResource
from src.service import OmegaRequests

from .config import bilibili_config, bilibili_resource_config
from .exception import BilibiliNetworkError


class BilibiliBase(object):
    """Bilibili 基类"""
    _root_url: str = 'https://www.bilibili.com'

    def __repr__(self) -> str:
        return self.__class__.__name__

    @staticmethod
    def parse_content_json(response: Any) -> Any:
        return OmegaRequests.parse_content_json(response)

    @classmethod
    async def request(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            *,
            method: Literal['GET', 'POST'] = 'GET',
            cookies: Optional[dict[str, str]] = None,
            data: Optional[Any] = None,
            json: Optional[Any] = None
    ) -> Any:
        """请求 api"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({
                'origin': 'https://www.bilibili.com',
                'referer': 'https://www.bilibili.com/'
            })
        if cookies is None:
            cookies = bilibili_config.bili_cookies

        requests = OmegaRequests(timeout=10, headers=headers, cookies=cookies)
        match method:
            case 'POST':
                response = await requests.post(url=url, params=params, data=data, json=json)
            case _:
                response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise BilibiliNetworkError(f'{response.request}, status code {response.status_code}')

        return response

    @classmethod
    async def request_json(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            *,
            method: Literal['GET', 'POST'] = 'GET',
            cookies: Optional[dict[str, str]] = None,
            data: Optional[Any] = None,
            json: Optional[Any] = None
    ) -> Any:
        """请求 api 并返回 json 数据"""
        response = await cls.request(url, params, headers, method=method, cookies=cookies, data=data, json=json)
        return OmegaRequests.parse_content_json(response)

    @classmethod
    async def request_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            headers: Optional[dict[str, Any]] = None,
            cookies: Optional[dict[str, str]] = None,
            timeout: int = 30
    ) -> str | bytes | None:
        """请求原始资源内容"""
        if headers is None:
            headers = OmegaRequests.get_default_headers()
            headers.update({
                'origin': 'https://www.bilibili.com',
                'referer': 'https://www.bilibili.com/'
            })
        if cookies is None:
            cookies = bilibili_config.bili_cookies

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=cookies)
        response = await requests.get(url=url, params=params)
        if response.status_code != 200:
            raise BilibiliNetworkError(f'{response.request}, status code {response.status_code}')

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
            headers.update({
                'origin': 'https://www.bilibili.com',
                'referer': 'https://www.bilibili.com/'
            })

        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        file = bilibili_resource_config.default_download_folder(original_file_name)
        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=bilibili_config.bili_cookies)

        return await requests.download(url=url, file=file, params=params)


__all__ = [
    'BilibiliBase'
]
