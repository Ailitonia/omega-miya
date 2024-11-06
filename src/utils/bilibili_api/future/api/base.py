"""
@Author         : Ailitonia
@Date           : 2024/11/4 10:59:54
@FileName       : base.py
@Project        : omega-miya
@Description    : bilibili API 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Any, Optional

from src.utils import BaseCommonAPI
from ..config import bilibili_api_config
from ..misc import (
    gen_buvid_fp,
    get_payload,
    gen_uuid_infoc,
    sign_wbi_params,
    sign_wbi_params_nav,
    extract_key_from_wbi_image,
    create_gen_web_ticket_params,
)
from ..models import Ticket, WebInterfaceNav, WebInterfaceSpi

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
    def _get_default_cookies(cls) -> "CookieTypes":
        return bilibili_api_config.bili_cookies

    @classmethod
    async def download_resource(cls, url: str) -> "TemporaryResource":
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=bilibili_api_config.download_folder, url=url,
        )

    @classmethod
    async def _sign_wbi_params_nav(cls, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """立即从 nav 接口请求参数进行 wbi 签名"""
        _wbi_nav_url: str = 'https://api.bilibili.com/x/web-interface/nav'

        response = await cls._get_json(url=_wbi_nav_url)
        return sign_wbi_params_nav(nav_data=WebInterfaceNav.model_validate(response), params=params)

    @classmethod
    async def sign_wbi_params(cls, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """对请求参数进行 wbi 签名"""
        img_key = bilibili_api_config.get_config('img_key')
        sub_key = bilibili_api_config.get_config('sub_key')

        if (img_key is None) or (sub_key is None):
            return await cls._sign_wbi_params_nav(params=params)

        return sign_wbi_params(params=params, img_key=img_key, sub_key=sub_key)

    @classmethod
    async def update_ticket_wbi_cookies(cls) -> dict[str, Any]:
        """从 BiliTicket 接口更新 web_ticket 及 wbi 签参数缓存"""
        _ticket_url: str = 'https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket'
        params = create_gen_web_ticket_params(bili_jct=bilibili_api_config.get_config('bili_jct'))

        response = await cls._post_json(url=_ticket_url, params=params)
        ticket_data = Ticket.model_validate(response)

        bilibili_api_config.update_config(
            bili_ticket=ticket_data.data.ticket,
            bili_ticket_expires=ticket_data.data.created_at + ticket_data.data.ttl,
            img_key=extract_key_from_wbi_image(ticket_data.data.nav.img),
            sub_key=extract_key_from_wbi_image(ticket_data.data.nav.sub),
        )
        return bilibili_api_config.bili_cookies


    @classmethod
    async def update_buvid_cookies(cls) -> dict[str, Any]:
        """为接口激活 buvid, 并更新 Cookies 缓存"""
        _spi_url: str = 'https://api.bilibili.com/x/frontend/finger/spi'
        _exclimbwuzhi_url: str = 'https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi'

        # get buvid3, buvid4
        spi_response = await cls._get_json(url=_spi_url)
        spi_data = WebInterfaceSpi.model_validate(spi_response)

        # active buvid
        uuid = gen_uuid_infoc()
        payload = get_payload()

        headers = cls._get_default_headers()
        headers.update({
            'origin': 'https://www.bilibili.com',
            'referer': 'https://www.bilibili.com/',
            'Content-Type': 'application/json'
        })

        bilibili_api_config.update_config(
            buvid3=spi_data.data.b_3,
            buvid4=spi_data.data.b_4,
            buvid_fp=gen_buvid_fp(payload, 31),
            _uuid=uuid
        )
        cookies = bilibili_api_config.bili_cookies
        await cls._post_json(url=_exclimbwuzhi_url, headers=headers, json=payload, cookies=cookies)
        return cookies


__all__ = [
    'BilibiliCommon',
]
