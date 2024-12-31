"""
@Author         : Ailitonia
@Date           : 2024/5/30 上午12:37
@FileName       : api_base
@Project        : nonebot2_miya
@Description    : bilibili api 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Any

from src.utils import BaseCommonAPI
from .config import bilibili_config, bilibili_resource_config
from .exclimbwuzhi import gen_buvid_fp, gen_uuid_infoc, get_payload
from .model import BilibiliWebInterfaceNav, BilibiliWebInterfaceSpi
from .verify_utils import sign_wbi_params

if TYPE_CHECKING:
    from nonebot.internal.driver import CookieTypes

    from src.resource import TemporaryResource


class BilibiliCommon(BaseCommonAPI):
    """Bilibili API 基类"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://www.bilibili.com'

    @classmethod
    async def _async_get_root_url(cls, *args, **kwargs) -> str:
        return cls._get_root_url(*args, **kwargs)

    @classmethod
    def _load_cloudflare_clearance(cls) -> bool:
        return False

    @classmethod
    def _get_default_headers(cls) -> dict[str, str]:
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'origin': 'https://www.bilibili.com',
            'referer': 'https://www.bilibili.com/'
        })
        return headers

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return bilibili_config.bili_cookies

    @classmethod
    async def download_resource(cls, url: str) -> 'TemporaryResource':
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=bilibili_resource_config.default_download_folder, url=url,
        )

    @classmethod
    async def update_wbi_params(cls, params: dict[str, Any] | None = None) -> dict:
        """为 wbi 接口请求参数进行 wbi 签名"""
        _wbi_nav_url: str = 'https://api.bilibili.com/x/web-interface/nav'

        response = await cls._get_json(url=_wbi_nav_url)
        return sign_wbi_params(nav_data=BilibiliWebInterfaceNav.model_validate(response), params=params)

    @classmethod
    async def update_buvid_params(cls) -> dict[str, Any]:
        """为接口激活 buvid"""
        _spi_url: str = 'https://api.bilibili.com/x/frontend/finger/spi'
        _exclimbwuzhi_url: str = 'https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi'

        # get buvid3, buvid4
        spi_response = await cls._get_json(url=_spi_url)
        spi_data = BilibiliWebInterfaceSpi.model_validate(spi_response)

        # active buvid
        uuid = gen_uuid_infoc()
        payload = get_payload()

        headers = cls._get_default_headers()
        headers.update({
            'origin': 'https://www.bilibili.com',
            'referer': 'https://www.bilibili.com/',
            'Content-Type': 'application/json'
        })

        cookies = bilibili_config.update_cookies_cache(
            buvid3=spi_data.data.b_3,
            buvid4=spi_data.data.b_4,
            buvid_fp=gen_buvid_fp(payload, 31),
            _uuid=uuid
        )

        await cls._post_json(url=_exclimbwuzhi_url, headers=headers, json=payload, cookies=cookies)
        return cookies


__all__ = [
    'BilibiliCommon',
]
