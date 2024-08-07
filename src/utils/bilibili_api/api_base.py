"""
@Author         : Ailitonia
@Date           : 2024/5/30 上午12:37
@FileName       : api_base
@Project        : nonebot2_miya
@Description    : bilibili api 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Any, Optional

from src.service import OmegaRequests
from src.utils.common_api import BaseCommonAPI
from .config import bilibili_config, bilibili_resource_config

if TYPE_CHECKING:
    from src.resource import TemporaryResource


class BilibiliCommon(BaseCommonAPI):
    """Bilibili API 基类"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://www.bilibili.com'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url()

    @classmethod
    def _get_default_headers(cls) -> dict[str, Any]:
        headers = OmegaRequests.get_default_headers()
        headers.update({
            'origin': 'https://www.bilibili.com',
            'referer': 'https://www.bilibili.com/'
        })
        return headers

    @classmethod
    def _get_default_cookies(cls) -> dict[str, str]:
        return bilibili_config.bili_cookies

    @classmethod
    async def download_resource(
            cls, url: str,
            params: Optional[dict[str, Any]] = None,
            *,
            timeout: int = 60,
    ) -> "TemporaryResource":
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        headers = cls._get_default_headers()
        cookies = cls._get_default_cookies()

        original_file_name = OmegaRequests.parse_url_file_name(url=url)
        file = bilibili_resource_config.default_download_folder(original_file_name)

        requests = OmegaRequests(timeout=timeout, headers=headers, cookies=cookies)
        return await requests.download(url=url, file=file, params=params)


__all__ = [
    'BilibiliCommon'
]
