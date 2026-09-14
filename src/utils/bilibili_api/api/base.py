"""
@Author         : Ailitonia
@Date           : 2024/11/4 10:59:54
@FileName       : base.py
@Project        : omega-miya
@Description    : bilibili API 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import time
from typing import TYPE_CHECKING, Any, ClassVar

from lxml import etree

from src.utils import BaseCommonAPI
from ..config import bilibili_api_config
from ..credential_manager import BILIBILI_CREDENTIAL_MANAGER, BilibiliCookiesData, BilibiliLoginCookiesData
from ..misc import (
    create_gen_web_ticket_params,
    extract_key_from_wbi_image,
    gen_buvid_fp,
    gen_payload,
    gen_uuid_infoc,
    sign_wbi_params,
    sign_wbi_params_nav,
)
from ..models import (
    SearchAllResult,
    SearchType,
    SearchTypeResult,
    Ticket,
    WebInterfaceNav,
    WebInterfaceSpi,
)

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from src.utils.omega_common_api.types import CookieTypes


class BilibiliCommon(BaseCommonAPI):
    """Bilibili API 基类"""

    _api_uuid: ClassVar[str]
    """发起请求时附带的 UUID"""
    _api_spm_prefix: ClassVar[str]
    """发起请求时附带的参数"""

    @classmethod
    def get_uuid(cls) -> str:
        if getattr(cls, '_api_uuid', None) is None:
            cls._api_uuid = gen_uuid_infoc()
        return cls._api_uuid

    @classmethod
    def get_spm_prefix(cls) -> str:
        if getattr(cls, '_api_spm_prefix', None) is None:
            cls._api_spm_prefix = '333.1387'
        return cls._api_spm_prefix

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://www.bilibili.com'

    @classmethod
    def _get_default_headers(cls) -> dict[str, str]:
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'origin': cls._get_root_url(),
            'referer': f'{cls._get_root_url()}/'
        })
        return headers

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return BILIBILI_CREDENTIAL_MANAGER.login_cookies

    @classmethod
    async def download_resource(cls, url: str) -> 'TemporaryResource':
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=bilibili_api_config.download_folder,
            url=url,
        )

    @classmethod
    async def _init_spm_prefix(cls) -> str:
        content = await cls._get_resource_as_text(url=cls._get_root_url())

        try:
            spm_prefix_item = etree.HTML(content).xpath('/html/head/meta[@name="spm_prefix"]').pop(0)
            spm_prefix = spm_prefix_item.attrib.get('content', None)
        except Exception as e:
            raise RuntimeError(f'parsing API spm_prefix not found, {e}') from e
        # 解析失败或未解析到都抛出 RuntimeError
        if not spm_prefix:
            raise RuntimeError('parsing API spm_prefix failed')

        cls._api_spm_prefix = spm_prefix
        return cls._api_spm_prefix

    @classmethod
    async def _sign_wbi_params_nav(cls, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """立即从 nav 接口请求参数进行 wbi 签名"""
        _wbi_nav_url: str = 'https://api.bilibili.com/x/web-interface/nav'

        json_response = await cls._get_resource_as_json(url=_wbi_nav_url)
        return sign_wbi_params_nav(nav_data=WebInterfaceNav.model_validate(json_response), params=params)

    @classmethod
    async def sign_wbi_params(cls, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """对请求参数进行 wbi 签名"""
        img_key = BILIBILI_CREDENTIAL_MANAGER.get_cookie('img_key')
        sub_key = BILIBILI_CREDENTIAL_MANAGER.get_cookie('sub_key')

        if (img_key is None) or (sub_key is None):
            return await cls._sign_wbi_params_nav(params=params)

        return sign_wbi_params(params=params, img_key=img_key, sub_key=sub_key)

    @classmethod
    async def _fetch_ticket_wbi_cookies(
            cls,
            bili_jct: str | None,
            *,
            cookies: 'CookieTypes' = None,
    ) -> dict[str, Any]:
        """从 BiliTicket 接口请求 web_ticket 及 wbi 签参数 (不更新 Cookies 缓存)

        :param bili_jct: Cookies 中的 bili_jct 字段, 未登录时传 None
        :param cookies: 请求使用的 Cookies, 默认使用全局凭据缓存
        :return: 新增 Cookies 值
        """
        _ticket_url: str = 'https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket'
        params = create_gen_web_ticket_params(bili_jct=bili_jct)

        json_response = await cls._post_acquire_as_json(url=_ticket_url, params=params, cookies=cookies)
        ticket_data = Ticket.model_validate(json_response)

        return {
            'bili_ticket': ticket_data.data.ticket,
            'bili_ticket_expires': ticket_data.data.created_at + ticket_data.data.ttl,
            'img_key': extract_key_from_wbi_image(ticket_data.data.nav.img),
            'sub_key': extract_key_from_wbi_image(ticket_data.data.nav.sub),
        }

    @classmethod
    async def update_ticket_wbi_cookies(cls) -> dict[str, Any]:
        """从 BiliTicket 接口更新 web_ticket 及 wbi 签参数, 并更新 Cookies 缓存"""
        new_cookies = await cls._fetch_ticket_wbi_cookies(
            bili_jct=BILIBILI_CREDENTIAL_MANAGER.get_cookie('bili_jct')
        )
        BILIBILI_CREDENTIAL_MANAGER.update_cookies(**new_cookies)
        return BILIBILI_CREDENTIAL_MANAGER.login_cookies

    @classmethod
    async def _fetch_buvid_cookies(cls, *, base_cookies: dict[str, Any] | None = None) -> dict[str, Any]:
        """为接口激活 buvid (不更新 Cookies 缓存)

        :param base_cookies: 激活请求所基于的 Cookies, 默认使用全局凭据缓存
        :return: 新增 Cookies 值
        """
        _spi_url: str = 'https://api.bilibili.com/x/frontend/finger/spi'
        _exclimbwuzhi_url: str = 'https://api.bilibili.com/x/internal/gaia-gateway/ExClimbWuzhi'
        headers = cls._get_default_headers()

        # get buvid3, buvid4
        spi_json_response = await cls._get_resource_as_json(url=_spi_url)
        spi_data = WebInterfaceSpi.model_validate(spi_json_response)

        # active buvid
        _uuid = cls.get_uuid()
        payload = gen_payload(
            post_url=cls._get_root_url(),
            spm_prefix=cls.get_spm_prefix(),
            uuid=_uuid,
            user_agent=headers.get('user-agent', ''),
        )

        new_cookies: dict[str, Any] = {
            'buvid3': spi_data.data.b_3,
            'buvid4': spi_data.data.b_4,
            'buvid_fp': gen_buvid_fp(payload, 31),
            'b_nut': time.time_ns() // 1_000_000_000,
            '_uuid': _uuid,
        }

        base = BILIBILI_CREDENTIAL_MANAGER.cookies if base_cookies is None else base_cookies
        merged_cookies = BilibiliCookiesData.model_validate({**base, **new_cookies})
        request_cookies = BilibiliLoginCookiesData.model_validate(merged_cookies.as_dict).as_dict
        headers.update({'Content-Type': 'application/json'})

        exclimbwuzhi_response = await cls._post_acquire_as_json(
            url=_exclimbwuzhi_url,
            headers=headers,
            data=payload,  # type: ignore 这里不能传 json 的入参 否则永远只会返回 -400 code
            cookies=request_cookies,
        )
        if not isinstance(exclimbwuzhi_response, dict) or exclimbwuzhi_response.get('code') != 0:
            raise RuntimeError(f'active buvid failed, exclimbwuzhi response: {exclimbwuzhi_response!r}')

        return new_cookies

    @classmethod
    async def update_buvid_cookies(cls) -> dict[str, Any]:
        """为接口激活 buvid, 并更新 Cookies 缓存"""
        new_cookies = await cls._fetch_buvid_cookies()
        BILIBILI_CREDENTIAL_MANAGER.update_cookies(**new_cookies)
        return BILIBILI_CREDENTIAL_MANAGER.login_cookies

    @classmethod
    async def global_search_all(cls, keyword: str) -> SearchAllResult:
        """综合搜索 (web端), 返回和关键字相关的 20 条信息

        综合搜索为默认搜索方式, 主要用于优先搜索用户、影视、番剧、游戏、话题等, 并加载第一页的20项相关视频
        """
        url = 'https://api.bilibili.com/x/web-interface/wbi/search/all/v2'
        params = await cls.sign_wbi_params(params={'keyword': keyword})
        data = await cls._get_resource_as_json(url=url, params=params)
        return SearchAllResult.model_validate(data)

    @classmethod
    async def global_search_by_type(
            cls,
            search_type: SearchType,
            keyword: str,
            page: int = 1,
            **kwargs,
    ) -> SearchTypeResult:
        """分类搜索 (web端), 根据关键词进行搜索, 返回结果每页 20 项

        :param search_type: 搜索类型
        :param keyword: 搜索关键词
        :param page: 搜索页码
        """
        params = {
            'search_type': search_type,
            'keyword': keyword,
            'page': page,
            **kwargs
        }
        search_url: str = 'https://api.bilibili.com/x/web-interface/wbi/search/type'
        searching_data = await cls._get_resource_as_json(url=search_url, params=params)
        return SearchTypeResult.model_validate(searching_data)


__all__ = [
    'BilibiliCommon',
]
