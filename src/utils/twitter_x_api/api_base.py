"""
@Author         : Ailitonia
@Date           : 2026/9/27 22:59
@FileName       : api_base
@Project        : omega-miya
@Description    : Twitter API 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import urlparse

from nonebot.log import logger

from src.exception import WebSourceException
from src.utils import BaseCommonAPI
from .config import twitter_api_config
from .consts import DEFAULT_LANGUAGE, DOMAIN, GUEST_ACTIVATE_URL, TOKEN
from .misc import flatten_params
from .model import TwitterGuestActivateResult
from .transaction import ClientTransaction

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from src.utils.omega_common_api.types import CookieTypes, HeaderTypes, QueryTypes


class BaseTwitterAPI(BaseCommonAPI):
    """推特 API 基类"""

    # 注意: 以下三个 ClassVar 经子类 cls 写入时会落在子类上(类属性遮蔽);
    # 当前所有公开入口均在唯一子类 TwitterGuest 上, 读写一致, 新增子类时须注意状态不共享
    _client_transaction: ClassVar[ClientTransaction | None] = None
    """X-Client-Transaction 计算状态(惰性初始化)"""
    _client_transaction_unavailable: ClassVar[bool] = False
    """X-Client-Transaction 计算状态不可用标志位(初始化失败后不再重复尝试)"""
    _guest_token: ClassVar[str | None] = None
    """访客令牌(惰性初始化)"""

    @classmethod
    def _get_root_url(cls, *args, **kwargs) -> str:
        return f'https://{DOMAIN}'

    @classmethod
    def _get_default_headers(cls) -> 'HeaderTypes':
        headers = cls._get_omega_requests_default_headers()
        headers.update({'referer': f'{cls._get_root_url()}/'})
        return headers

    @classmethod
    def _get_default_cookies(cls) -> 'CookieTypes':
        return None

    @classmethod
    def _get_api_headers(cls, *, guest_token: str | None = None, with_active_user: bool = True) -> dict[str, str]:
        """构造 X API 请求头

        :param guest_token: 可选, 注入访客令牌
        :param with_active_user: 是否携带 X-Twitter-Active-User 头(激活访客令牌时不需要)
        """
        headers = {str(k): str(v) for k, v in cls._iter_headers_item(cls._get_default_headers())}
        headers.update({
            'authorization': f'Bearer {TOKEN}',
            'content-type': 'application/json',
            'accept-language': DEFAULT_LANGUAGE,
            'x-twitter-client-language': DEFAULT_LANGUAGE,
            'origin': cls._get_root_url(),
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
        })
        if with_active_user:
            headers.update({'x-twitter-active-user': 'yes'})
        if guest_token is not None:
            headers.update({'x-guest-token': guest_token})
        return headers

    @classmethod
    async def _ensure_client_transaction(cls) -> ClientTransaction | None:
        """惰性初始化 X-Client-Transaction 计算状态

        初始化失败(如 X 首页结构变更)时返回 None, 后续请求将不携带 X-Client-Transaction-Id 头
        """
        if cls._client_transaction is not None and cls._client_transaction.is_initialized:
            return cls._client_transaction
        if cls._client_transaction_unavailable:
            return None

        transaction = ClientTransaction()
        headers = {str(k): str(v) for k, v in cls._iter_headers_item(cls._get_default_headers())}
        headers.update({
            'accept-language': f'{DEFAULT_LANGUAGE},{DEFAULT_LANGUAGE.split("-")[0]};q=0.9',
            'cache-control': 'no-cache',
        })
        requester = cls._init_omega_requests(headers=headers, no_cookies=True)
        try:
            await transaction.init(requester=requester)
        except Exception as e:
            logger.opt(colors=True).warning(
                f'<lc>Twitter</lc> | X-Client-Transaction 初始化失败, 后续请求将不携带 transaction id, {e}'
            )
            cls._client_transaction_unavailable = True
            return None
        cls._client_transaction = transaction
        return transaction

    @classmethod
    def _get_transaction_headers(cls, method: str, url: str, transaction: ClientTransaction | None) -> dict[str, str]:
        """构造 X-Client-Transaction-Id 请求头, transaction 不可用时返回空"""
        if transaction is None:
            return {}
        return {
            'x-client-transaction-id': transaction.generate_transaction_id(method=method, path=urlparse(url).path)
        }

    @classmethod
    async def _activate_guest(cls) -> str:
        """激活访客会话, 生成并缓存新的访客令牌"""
        transaction = await cls._ensure_client_transaction()
        url = GUEST_ACTIVATE_URL
        headers = cls._get_api_headers(with_active_user=False)
        headers.update(cls._get_transaction_headers(method='POST', url=url, transaction=transaction))
        response = await cls._request_post(url=url, data={}, headers=headers)
        activate_result = TwitterGuestActivateResult.model_validate(cls._parse_content_as_json(response))
        cls._guest_token = activate_result.guest_token
        return cls._guest_token

    @classmethod
    async def _ensure_guest_token(cls) -> str:
        """获取访客令牌, 未激活时自动激活访客会话"""
        if cls._guest_token is None:
            cls._guest_token = await cls._activate_guest()
        return cls._guest_token

    @classmethod
    def _reset_guest_state(cls) -> None:
        """重置访客会话状态(访客令牌失效/请求被拒绝时使用)"""
        cls._guest_token = None
        cls._client_transaction = None
        cls._client_transaction_unavailable = False

    @classmethod
    async def _request_gql_api(
            cls,
            url: str,
            *,
            variables: dict[str, Any],
            features: dict[str, Any] | None = None,
            extra_params: dict[str, Any] | None = None,
            _retried: bool = False,
    ) -> Any:
        """请求 GraphQL API 并返回 json 内容, 自动注入访客令牌与 X-Client-Transaction-Id

        访客令牌失效(401/403)时自动重置访客会话状态并重试一次
        """
        guest_token = await cls._ensure_guest_token()
        transaction = await cls._ensure_client_transaction()
        headers = cls._get_api_headers(guest_token=guest_token)
        headers.update(cls._get_transaction_headers(method='GET', url=url, transaction=transaction))

        params: dict[str, Any] = {'variables': variables}
        if features is not None:
            params['features'] = features
        if extra_params:
            params.update(extra_params)

        try:
            response = await cls._request_get(url=url, params=flatten_params(params), headers=headers)
        except WebSourceException as e:
            if e.status_code in (401, 403) and not _retried:
                logger.debug(f'TwitterGuest | 访客会话状态可能已失效({e.status_code}), 重置并重新激活后重试')
                cls._reset_guest_state()
                return await cls._request_gql_api(
                    url=url, variables=variables, features=features, extra_params=extra_params, _retried=True
                )
            raise
        return cls._parse_content_as_json(response)

    @classmethod
    async def get_resource_as_bytes(cls, url: str, *, params: 'QueryTypes' = None, timeout: int = 30) -> bytes:
        """请求原始资源内容"""
        return await cls._get_resource_as_bytes(url, params, timeout=timeout)

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
            save_folder=twitter_api_config.default_download_folder,
            url=url,
            subdir=subdir,
            headers=headers,
            ignore_exist_file=ignore_exist_file,
        )


__all__ = [
    'BaseTwitterAPI',
]
