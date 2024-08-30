"""
@Author         : Ailitonia
@Date           : 2024/7/30 10:13:37
@FileName       : api_base.py
@Project        : omega-miya
@Description    : pixiv api 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from src.utils.common_api import BaseCommonAPI
from .config import pixiv_config

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes, HeaderTypes, QueryTypes


class BasePixivAPI(BaseCommonAPI):
    """Pixiv API 基类"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://www.pixiv.net'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> "HeaderTypes":
        headers = cls._get_omega_requests_default_headers()
        headers.update({'referer': 'https://www.pixiv.net/'})
        return headers

    @classmethod
    def _get_default_cookies(cls) -> "CookieTypes":
        return pixiv_config.cookie_phpssid

    @classmethod
    async def get_resource_as_bytes(cls, url: str, *, params: "QueryTypes" = None, timeout: int = 30) -> bytes:
        """请求原始资源内容"""
        return await cls._get_resource_as_bytes(url, params, timeout=timeout)

    @classmethod
    async def get_resource_as_text(cls, url: str, *, params: "QueryTypes" = None, timeout: int = 10) -> str:
        """请求原始资源内容"""
        return await cls._get_resource_as_text(url, params, timeout=timeout)


__all__ = [
    'BasePixivAPI'
]
