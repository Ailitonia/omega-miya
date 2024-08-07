"""
@Author         : Ailitonia
@Date           : 2024/7/30 10:13:37
@FileName       : api_base.py
@Project        : omega-miya
@Description    : pixiv api 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional, Any

from src.utils.common_api import BaseCommonAPI
from .config import pixiv_config


class BasePixivAPI(BaseCommonAPI):
    """Pixiv API 基类"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://www.pixiv.net'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _get_default_headers(cls) -> dict[str, Any]:
        headers = cls._get_omega_requests_default_headers()
        headers.update({'referer': 'https://www.pixiv.net/'})
        return headers

    @classmethod
    def _get_default_cookies(cls) -> dict[str, str]:
        return pixiv_config.cookie_phpssid

    @classmethod
    async def get_resource(
            cls,
            url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            timeout: int = 30,
    ) -> str | bytes:
        """请求原始资源内容"""
        return await cls._get_resource(url, params, timeout=timeout)


__all__ = [
    'BasePixivAPI'
]
