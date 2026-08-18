"""
@Author         : Ailitonia
@Date           : 2025/2/9 14:16
@FileName       : api
@Project        : omega-miya
@Description    : Omega API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import hmac
import time
from collections.abc import Callable, Coroutine, Mapping
from hashlib import sha256
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from nonebot import get_app, get_driver
from nonebot.log import logger
from nonebot.utils import run_sync

from src.compat import dump_json_as

from .config import api_config
from .consts import APP_HEADER_KEY, TIMESTAMP_HEADER_KEY, TOKEN_HEADER_KEY

if TYPE_CHECKING:
    from src.resource import BaseResource


_REGISTERED_APP: set[str] = set()
"""缓存全局已注册 app_name"""

_TIMESTAMP_EXPIRE_SECONDS: int = api_config.omega_api_timestamp_expire_seconds
"""请求时间戳允许的最大偏差秒数"""

_USED_SIGNATURES: dict[str, float] = {}
"""重放防护: 已使用签名的缓存, 值为过期时间点(time.monotonic)"""

_USED_SIGNATURES_TTL: float = _TIMESTAMP_EXPIRE_SECONDS * 2
"""已使用签名的缓存时长(秒), 需大于时间戳校验窗口"""

_USED_SIGNATURES_MAX_SIZE: int = api_config.omega_api_used_signatures_max_size
"""已使用签名缓存触发清理的容量阈值"""

_REQUEST_BODY_MAX_SIZE: int = api_config.omega_api_request_body_max_size
"""请求体最大允许大小(字节)"""


def _is_replayed_signature(signature: str) -> bool:
    """检查签名是否已被使用过, 未使用则记录该签名(防重放)

    缓存达到容量阈值时会先清理过期条目, 清理后仍超限则直接拒绝新签名, 保证缓存有界
    """
    now = time.monotonic()
    if len(_USED_SIGNATURES) >= _USED_SIGNATURES_MAX_SIZE:
        expired = [x for x, expire_at in _USED_SIGNATURES.items() if expire_at <= now]
        for x in expired:
            del _USED_SIGNATURES[x]
        if len(_USED_SIGNATURES) >= _USED_SIGNATURES_MAX_SIZE:
            # 清理后仍超限: 拒绝新签名, 防止缓存被撑爆(OOM), TTL 到期后自动恢复
            logger.opt(colors=True).warning(
                f'<lc>Omega API</lc> | used signatures cache is full (size={len(_USED_SIGNATURES)}), '
                f'reject new signature'
            )
            return True
    expire_at = _USED_SIGNATURES.get(signature)
    if expire_at is not None and expire_at > now:
        return True
    _USED_SIGNATURES[signature] = now + _USED_SIGNATURES_TTL
    return False


def _normalize_sign_params(params: Mapping[str, str]) -> str:
    """将 query 参数规范化为排序后的键值对列表 JSON, 多值参数(如 ?a=1&a=2)完整保留"""
    # QueryParams/MultiDict 等多值映射使用 multi_items() 保留重复键, 普通 Mapping 使用 items()
    if hasattr(params, 'multi_items'):
        pairs = list(params.multi_items())
    else:
        pairs = list(params.items())
    sorted_pairs = sorted(pairs, key=lambda item: (item[0], item[1]))
    return dump_json_as(list[tuple[str, str]], sorted_pairs)


class OmegaAPIRouter(APIRouter):
    """Omega API APIRouter 类"""

    @property
    def color_log_prefix(self) -> str:
        return f'<lc>Omega APIRouter</lc> | APIRouter <lc>{self.prefix}</lc>'

    def register_get_route(self, path: str):
        """包装 async function 并注册为 GET 路由

        :param path: 请求路径
        """
        path = f'/{path.strip().removeprefix("/").removesuffix("/").strip()}'

        def decorator[**P, T1, T2, R](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
            if not iscoroutinefunction(func):
                raise ValueError('The decorated function must be coroutine function')

            self.get(path)(func)
            logger.opt(colors=True).info(
                f'{self.color_log_prefix} registered: (<lg>GET</lg>) <b><u>{self.prefix}{path}</u></b>'
            )
            return func

        return decorator

    def register_post_route(self, path: str):
        """包装 async function 并注册为 POST 路由

        :param path: 请求路径
        """
        path = f'/{path.strip().removeprefix("/").removesuffix("/").strip()}'

        def decorator[**P, T1, T2, R](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
            if not iscoroutinefunction(func):
                raise ValueError('The decorated function must be coroutine function')

            self.post(path)(func)
            logger.opt(colors=True).info(
                f'{self.color_log_prefix} registered: (<ly>POST</ly>) <b><u>{self.prefix}{path}</u></b>'
            )
            return func

        return decorator

    def register_put_route(self, path: str):
        """包装 async function 并注册为 PUT 路由

        :param path: 请求路径
        """
        path = f'/{path.strip().removeprefix("/").removesuffix("/").strip()}'

        def decorator[**P, T1, T2, R](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
            if not iscoroutinefunction(func):
                raise ValueError('The decorated function must be coroutine function')

            self.put(path)(func)
            logger.opt(colors=True).info(
                f'{self.color_log_prefix} registered: (<lc>PUT</lc>) <b><u>{self.prefix}{path}</u></b>'
            )
            return func

        return decorator

    def register_delete_route(self, path: str):
        """包装 async function 并注册为 DELETE 路由

        :param path: 请求路径
        """
        path = f'/{path.strip().removeprefix("/").removesuffix("/").strip()}'

        def decorator[**P, T1, T2, R](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
            if not iscoroutinefunction(func):
                raise ValueError('The decorated function must be coroutine function')

            self.delete(path)(func)
            logger.opt(colors=True).info(
                f'{self.color_log_prefix} registered: (<lr>DELETE</lr>) <b><u>{self.prefix}{path}</u></b>'
            )
            return func

        return decorator


class OmegaAPI:
    """Omega API 应用创建与路由注册"""

    def __init__(
            self,
            app_name: str,
            *,
            enable_token_verify: bool = False,
            access_domain: str | None = None,
            use_https: bool = False,
    ) -> None:
        """初始化 Omega API 应用

        :param app_name: 应用名称, 应当为全局唯一
        :param enable_token_verify: 是否启用请求 headers token 校验
        :param access_domain: 外部访问域名, 适用于配置了 nginx 反向代理的访问
        :param use_https: 返回访问 URL 是是否使用 https
        """
        self._app_name = app_name.strip().removeprefix('/').removesuffix('/').strip()
        self._enable_token_verify = enable_token_verify
        self._access_domain = access_domain
        self._use_https = use_https
        self._api_key = self._derive_app_key(api_config.omega_api_master_key.get_secret_value(), self._app_name)
        self._app = self._init_sub_app()
        self._root_url = self._get_root_url()

    @property
    def color_log_prefix(self) -> str:
        return f'<lc>Omega API</lc> | Service <lc>{self._app_name}</lc>'

    @property
    def root_url(self) -> str:
        return self._root_url

    def _get_root_url(self) -> str:
        nonebot_config = get_driver().config
        host = self._access_domain if self._access_domain is not None else str(nonebot_config.host)
        port = nonebot_config.port
        if host in ['0.0.0.0', '127.0.0.1']:
            host = 'localhost'
        return f'{"https" if self._use_https else "http"}://{host}:{port}/{self._app_name}'

    @staticmethod
    def _derive_app_key(master_key: str, app_name: str) -> str:
        """由主密钥派生指定应用的子密钥, 避免单一密钥泄露影响全部应用"""
        return hmac.new(master_key.encode(), app_name.encode(), sha256).hexdigest()

    @staticmethod
    def sign_params_hmac(
        key: str,
        app_name: str,
        method: str,
        path: str,
        params: Mapping[str, str],
        body: bytes = b'',
        *,
        timestamp: int | None = None,
    ) -> tuple[int, str]:
        """对请求参数进行签名

        请求 Headers 中应当包括:
          - X-OmegaAPI-App: 请求的 App 名称
          - X-OmegaAPI-Timestamp: 发起请求时的时间戳
          - X-OmegaAPI-Token: 计算出的签名 Token

        签名消息格式: {app_name}.{method}.{path}.{timestamp}.{排序后的 query 参数键值对列表 JSON}.{请求体 SHA-256}

        :param key: 签名主密钥(内部会按应用名称派生子密钥)
        :param app_name: 应用名称
        :param method: 请求 HTTP 方法, 大小写不敏感, 会统一转为大写
        :param path: 请求完整路径(含挂载前缀), 需与请求 URL 路径一致
        :param params: 请求 query 参数, 多值参数(如 ?a=1&a=2)请传入 QueryParams 以保留重复键
        :param body: 请求体原始内容, 无请求体时留空
        :param timestamp: 显式指定的请求时间戳, 留空时使用当前时间
        :return: (时间戳, 签名 Token), 时间戳需放入 X-OmegaAPI-Timestamp 请求头

        注意: 每次请求(包括重试)都应重新生成时间戳与签名, 相同的签名在时间戳有效期内再次使用会被服务端拒绝(防重放)
        """
        timestamp = int(time.time()) if timestamp is None else timestamp
        params_json = _normalize_sign_params(params)
        body_hash = sha256(body).hexdigest()
        sign_message = f'{app_name}.{method.upper()}.{path}.{timestamp}.{params_json}.{body_hash}'
        app_key = OmegaAPI._derive_app_key(key, app_name)
        hmac_obj = hmac.new(app_key.encode(), sign_message.encode(), sha256)
        return timestamp, hmac_obj.hexdigest()

    def verify_params_hmac(
        self,
        signature: str,
        timestamp: int | str,
        method: str,
        path: str,
        params: Mapping[str, str],
        body: bytes = b'',
    ) -> bool:
        """对请求参数签名进行校验

        :param signature: 待校验的签名 Token
        :param timestamp: 请求 Headers 中提供的时间戳
        :param method: 请求 HTTP 方法, 大小写不敏感, 会统一转为大写
        :param path: 请求完整路径(含挂载前缀), 需与请求 URL 路径一致
        :param params: 请求 query 参数, 多值参数(如 ?a=1&a=2)请传入 QueryParams 以保留重复键
        :param body: 请求体原始内容, 无请求体时留空
        """
        params_json = _normalize_sign_params(params)
        body_hash = sha256(body).hexdigest()
        sign_message = f'{self._app_name}.{method.upper()}.{path}.{timestamp}.{params_json}.{body_hash}'
        hmac_obj = hmac.new(self._api_key.encode(), sign_message.encode(), sha256)
        return hmac.compare_digest(hmac_obj.hexdigest(), signature)

    @run_sync
    def async_verify_params_hmac(
        self,
        signature: str,
        timestamp: int | str,
        method: str,
        path: str,
        params: Mapping[str, str],
        body: bytes = b'',
    ) -> bool:
        """对请求参数签名进行校验"""
        return self.verify_params_hmac(signature, timestamp, method, path, params, body)

    def _init_sub_app(self) -> FastAPI:
        """初始化子应用"""
        # 检查 nonebot 驱动器类型
        if 'fastapi' not in get_driver().type:
            raise RuntimeError('fastapi driver not enabled')

        # 检查 app_name 是否已被注册
        if self._app_name in _REGISTERED_APP:
            raise ValueError(f'OmegaAPI service {self._app_name!r} already registered')
        _REGISTERED_APP.add(self._app_name)

        # 创建子应用
        sub_app = FastAPI()

        # 配置 Token 校验中间件
        @sub_app.middleware('http')
        async def token_verify_middleware(request: Request, call_next):
            """参数签名校验中间件"""
            if not self._enable_token_verify:
                return await call_next(request)

            async def _read_request_body(max_size: int) -> bytes | None:
                """流式读取请求体并限制最大大小, 超出限制时返回 None

                读取成功后缓存到 request._body(与 Request.body() 行为一致), 保证下游路由仍能正常读取请求体
                """
                request_body = bytearray()
                async for chunk in request.stream():
                    request_body.extend(chunk)
                    if len(request_body) > max_size:
                        return None
                request._body = bytes(request_body)
                return request._body

            def _log_rejected(reason: str) -> None:
                """记录校验失败的审计日志"""
                client_host = request.client.host if request.client is not None else 'unknown'
                logger.opt(colors=True).warning(
                    f'{self.color_log_prefix} rejected <ly>{request.method}</ly> '
                    f'<u>{request.url.path}</u> from <lc>{client_host}</lc>: {reason}'
                )

            # 请求 App 名称校验
            request_app = request.headers.get(APP_HEADER_KEY, None)
            if request_app is None or request_app != self._app_name:
                _log_rejected('Invalid Request App')
                return JSONResponse({'error': True, 'message': 'Invalid Request App'}, status_code=403)

            # 请求时间戳校验
            request_timestamp = request.headers.get(TIMESTAMP_HEADER_KEY, None)
            if request_timestamp is None:
                _log_rejected('Timestamp Not Provided')
                return JSONResponse({'error': True, 'message': 'Timestamp Not Provided'}, status_code=403)
            # 验证时间戳是否在合理范围内(±请求时间戳允许的最大偏差秒数内)
            # 限制数字串长度以避免超长整数触发 int() 异常
            if not request_timestamp.isdigit() or len(request_timestamp) > 16:
                _log_rejected('Invalid Timestamp')
                return JSONResponse({'error': True, 'message': 'Invalid Timestamp'}, status_code=403)
            if abs(int(time.time()) - int(request_timestamp)) > _TIMESTAMP_EXPIRE_SECONDS:
                _log_rejected('Invalid Timestamp')
                return JSONResponse({'error': True, 'message': 'Invalid Timestamp'}, status_code=403)

            # 请求签名校验(包含请求体哈希, 防止请求体被篡改或重放)
            token = request.headers.get(TOKEN_HEADER_KEY, None)
            if token is None:
                _log_rejected('Token Not Provided')
                return JSONResponse({'error': True, 'message': 'Token Not Provided'}, status_code=403)

            # 请求体大小限制: 先依据 Content-Length 快速拒绝, 再通过流式读取强制上限, 防止超大请求体耗尽内存
            content_length = request.headers.get('content-length')
            if content_length is not None and (
                not content_length.isdigit() or int(content_length) > _REQUEST_BODY_MAX_SIZE
            ):
                _log_rejected('Payload Too Large')
                return JSONResponse({'error': True, 'message': 'Payload Too Large'}, status_code=413)

            body = await _read_request_body(_REQUEST_BODY_MAX_SIZE)
            if body is None:
                _log_rejected('Payload Too Large')
                return JSONResponse({'error': True, 'message': 'Payload Too Large'}, status_code=413)

            if not await self.async_verify_params_hmac(
                token,
                request_timestamp,
                request.method,
                request.url.path,
                request.query_params,
                body,
            ):
                _log_rejected('Invalid Token')
                return JSONResponse({'error': True, 'message': 'Invalid Token'}, status_code=403)

            # 防重放校验, 已使用过的合法签名在缓存有效期内将被拒绝
            if _is_replayed_signature(token):
                _log_rejected('Replayed Token')
                return JSONResponse({'error': True, 'message': 'Replayed Token'}, status_code=403)

            return await call_next(request)

        # 挂载子应用
        nonebot_app: FastAPI = get_app()
        nonebot_app.mount(f'/{self._app_name}', sub_app)
        return sub_app

    def mount_router[T: APIRouter](self, api_router: T, prefix: str = '', **kwargs) -> T:
        """挂载 APIRouter"""
        prefix = f'/{prefix.strip().removeprefix("/").removesuffix("/").strip()}' if prefix else prefix
        self._app.include_router(api_router, prefix=prefix, **kwargs)
        logger.opt(colors=True).info(
            f'{self.color_log_prefix} mounted APIRouter at: <b><u>{self.root_url}{prefix}{api_router.prefix}</u></b>'
        )
        return api_router

    def mount_static_path(
            self,
            target_dir: 'BaseResource',
            path: str = '',
            *,
            prefix: str = '',
            html: bool = False,
            check_dir: bool = True,
            follow_symlink: bool = False,
    ) -> None:
        """挂载静态文件路径"""
        target_dir.raise_not_dir()
        prefix = f'/{prefix.strip().removeprefix("/").removesuffix("/").strip()}' if prefix else prefix
        path = f'/{path.strip().removeprefix("/").removesuffix("/").strip()}' if path else path
        mount_path = f'{prefix.strip()}{path.strip()}'
        self._app.mount(
            mount_path,
            StaticFiles(
                directory=target_dir.path,
                html=html,
                check_dir=check_dir,
                follow_symlink=follow_symlink,
            ),
            name=target_dir.name,
        )
        logger.opt(colors=True).info(
            f'{self.color_log_prefix} mounted <lc>{target_dir}</lc> at: <b><u>{self.root_url}{mount_path}</u></b>'
        )

    def register_get_route(self, path: str):
        """包装 async function 并注册为 GET 路由

        :param path: 请求路径
        """
        path = f'/{path.strip().removeprefix("/").removesuffix("/").strip()}'

        def decorator[**P, T1, T2, R](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
            if not iscoroutinefunction(func):
                raise ValueError('The decorated function must be coroutine function')

            self._app.get(path)(func)
            logger.opt(colors=True).info(
                f'{self.color_log_prefix} registered: (<lg>GET</lg>) <b><u>{self.root_url}{path}</u></b>'
            )
            return func

        return decorator

    def register_post_route(self, path: str):
        """包装 async function 并注册为 POST 路由

        :param path: 请求路径
        """
        path = f'/{path.strip().removeprefix("/").removesuffix("/").strip()}'

        def decorator[**P, T1, T2, R](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
            if not iscoroutinefunction(func):
                raise ValueError('The decorated function must be coroutine function')

            self._app.post(path)(func)
            logger.opt(colors=True).info(
                f'{self.color_log_prefix} registered: (<ly>POST</ly>) <b><u>{self.root_url}{path}</u></b>'
            )
            return func

        return decorator

    def register_put_route(self, path: str):
        """包装 async function 并注册为 PUT 路由

        :param path: 请求路径
        """
        path = f'/{path.strip().removeprefix("/").removesuffix("/").strip()}'

        def decorator[**P, T1, T2, R](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
            if not iscoroutinefunction(func):
                raise ValueError('The decorated function must be coroutine function')

            self._app.put(path)(func)
            logger.opt(colors=True).info(
                f'{self.color_log_prefix} registered: (<lc>PUT</lc>) <b><u>{self.root_url}{path}</u></b>'
            )
            return func

        return decorator

    def register_delete_route(self, path: str):
        """包装 async function 并注册为 DELETE 路由

        :param path: 请求路径
        """
        path = f'/{path.strip().removeprefix("/").removesuffix("/").strip()}'

        def decorator[**P, T1, T2, R](func: Callable[P, Coroutine[T1, T2, R]]) -> Callable[P, Coroutine[T1, T2, R]]:
            if not iscoroutinefunction(func):
                raise ValueError('The decorated function must be coroutine function')

            self._app.delete(path)(func)
            logger.opt(colors=True).info(
                f'{self.color_log_prefix} registered: (<lr>DELETE</lr>) <b><u>{self.root_url}{path}</u></b>'
            )
            return func

        return decorator


__all__ = [
    'OmegaAPI',
    'OmegaAPIRouter',
]
