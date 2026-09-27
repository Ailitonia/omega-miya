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

from nonebot.log import logger

from src.utils import BaseCommonAPI
from .config import weibo_api_config
from .credential_manager import WEIBO_CREDENTIAL_MANAGER, WeiboCookiesData
from .misc import merge_cookies

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes, QueryTypes, Response


class BaseWeiboAPI(BaseCommonAPI):
    """微博 API 基类, 使用手机端网页 API"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return 'https://m.weibo.cn'

    @classmethod
    def _get_default_headers(cls) -> dict[str, Any]:
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'accept': 'application/json, text/plain, */*',
            'origin': f'{cls._get_root_url()}',
            'referer': f'{cls._get_root_url()}/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-requested-with': 'XMLHttpRequest',
            'mweibo-pwa': '1',
        })
        return headers

    @classmethod
    def _get_api_headers(cls, *, referer: str | None = None) -> dict[str, Any]:
        """构造 m.weibo.cn API 请求头, 注入 XSRF 校验头与场景化 Referer

        :param referer: 可选, 覆盖场景化 referer (如用户主页 https://m.weibo.cn/u/{uid})
        """
        headers = cls._get_default_headers()
        if xsrf_token := WEIBO_CREDENTIAL_MANAGER.get_cookie('XSRF-TOKEN'):
            headers.update({'x-xsrf-token': xsrf_token})
        if referer is not None:
            headers.update({'referer': referer})
        return headers

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return WEIBO_CREDENTIAL_MANAGER.cookies

    @classmethod
    async def _sync_response_cookies(cls, response: 'Response') -> None:
        """回收响应 set-cookie 到全局凭据缓存, 凭据有实际变化时同步落库 (服务端 Cookies 续约)"""
        set_cookies = cls._extra_set_cookies_from_response(response)
        if not set_cookies:
            return

        new_cookies_data = WeiboCookiesData.model_validate(
            merge_cookies(WEIBO_CREDENTIAL_MANAGER.cookies, set_cookies)
        )
        new_cookies = new_cookies_data.as_dict
        old_cookies = WEIBO_CREDENTIAL_MANAGER.cookies
        if new_cookies == old_cookies:
            return

        WEIBO_CREDENTIAL_MANAGER.replace_cookies(new_cookies_data)
        try:
            await WEIBO_CREDENTIAL_MANAGER.save_to_database()
        except Exception as e:
            # 落库失败不影响业务请求, 内存缓存已更新, 后续同步自愈
            logger.opt(colors=True).error(f'<lc>Weibo</lc> | <r>响应 Cookies 落库失败</r>, {e}')
        changed_keys = sorted(key for key, value in new_cookies.items() if old_cookies.get(key) != value)
        logger.opt(colors=True).debug(f'<lc>Weibo</lc> | 响应 Cookies 已回收并落库, 更新: {changed_keys}')

    @classmethod
    async def _get_api_json(
            cls,
            url: str,
            params: 'QueryTypes' = None,
            *,
            referer: str | None = None,
    ) -> Any:
        """请求 m.weibo.cn API 并返回 json 内容, 自动注入风控请求头并回收响应 set-cookie"""
        response = await cls._request_get(
            url=url,
            params=params,
            headers=cls._get_api_headers(referer=referer),
        )
        await cls._sync_response_cookies(response)
        return cls._parse_content_as_json(response)

    @classmethod
    async def download_resource(
            cls,
            url: str,
            *,
            subdir: str | None = None,
            headers: 'HeaderTypes' = None,
            ignore_exist_file: bool = False,
    ) -> 'TemporaryResource':
        """下载任意资源到本地, 保持原始文件名, 直接覆盖同名文件"""
        return await cls._download_resource(
            save_folder=weibo_api_config.default_download_folder,
            url=url,
            subdir=subdir,
            headers=headers,
            ignore_exist_file=ignore_exist_file,
        )


__all__ = [
    'BaseWeiboAPI',
]
