"""
@Author         : Ailitonia
@Date           : 2026/9/25 22:38
@FileName       : base.py
@Project        : omega-miya
@Description    : 微博 API 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Any

from src.utils import BaseCommonAPI
from .config import weibo_api_config
from .credential_manager import WEIBO_CREDENTIAL_MANAGER

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from src.utils.omega_common_api.types import CookieTypes


class BaseWeiboAPI(BaseCommonAPI):
    """微博 API 基类, 使用手机端网页 API"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://m.weibo.cn'

    @classmethod
    def _get_default_headers(cls) -> dict[str, Any]:
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'origin': f'{cls._get_root_url()}',
            'referer': f'{cls._get_root_url()}/'
        })
        return headers

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return WEIBO_CREDENTIAL_MANAGER.cookies

    @classmethod
    async def download_resource(
            cls,
            url: str,
            *,
            subdir: str | None = None,
            ignore_exist_file: bool = False,
    ) -> 'TemporaryResource':
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=weibo_api_config.default_download_folder,
            url=url,
            subdir=subdir,
            ignore_exist_file=ignore_exist_file
        )


__all__ = [
    'BaseWeiboAPI',
]
