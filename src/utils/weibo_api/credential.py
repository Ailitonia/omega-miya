"""
@Author         : Ailitonia
@Date           : 2026/9/25 22:38
@FileName       : credential.py
@Project        : omega-miya
@Description    : 微博凭据操作类 (访客风控校验与扫码登录流程)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import time
from typing import TYPE_CHECKING, Any, ClassVar

from nonebot.drivers import Request
from nonebot.log import logger

from .base import BaseWeiboAPI
from .consts import WEIBO_DETECTION_SAMPLE_UID, LoginStatusCode, LoginUrl, RiskFlowStep, VisitorUrl
from .credential_manager import WEIBO_CREDENTIAL_MANAGER, WeiboCookiesData
from .misc import (
    build_fingerprint,
    build_risk_flow_step_headers,
    extract_params_from_html,
    gen_rand_param,
    make_bd_payload,
    merge_cookies,
    parse_callback_js,
    parse_loose_json_object,
)
from .model import (
    WeiboApiConfig,
    WeiboBdResponse,
    WeiboGenVisitorResult,
    WeiboLoginQrCodeInfo,
    WeiboQrCodeCheck,
    WeiboQrCodeImage,
    WeiboVisitorPageParams,
)

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from src.utils.omega_requests.types import HTTPClientSession


class WeiboCredential(BaseWeiboAPI):
    """微博凭据操作类, 实现访客风控校验与扫码登录流程"""

    _LOGIN_QR_MAX_ATTEMPT: ClassVar[int] = 25
    """扫码登录最大轮询次数"""
    _LOGIN_QR_POLL_INTERVAL: ClassVar[int] = 6
    """扫码登录轮询间隔秒数"""

    # ------------------------------------------------------------------ #
    # 访客风控流程
    # ------------------------------------------------------------------ #

    @classmethod
    async def _fetch_initial_page(cls, *, cookies: dict[str, str]) -> WeiboVisitorPageParams:
        """RiskFlowStep 1: 获取访客流程起始页面, 解析风控参数并合并响应 Cookies 到传入字典"""
        default_headers = cls._get_omega_requests_default_headers()
        response = await cls._request_get(
            url=VisitorUrl.START_URL,
            headers=build_risk_flow_step_headers(RiskFlowStep.S1_INIT_PAGE, default_headers),
            cookies=cookies,
        )
        merge_cookies(cookies, cls._extra_set_cookies_from_response(response))
        return extract_params_from_html(cls._parse_content_as_text(response))

    @classmethod
    async def _post_visitor_enter(cls, *, cookies: dict[str, str]) -> str:
        """RiskFlowStep 2: POST 访客系统 enter 接口, 返回本次会话的 _rand 值并合并响应 Cookies 到传入字典"""
        default_headers = cls._get_omega_requests_default_headers()
        rand = gen_rand_param()
        data = {
            'entry': 'sinawap',
            'a': 'enter',
            'url': VisitorUrl.START_URL,
            'domain': '.weibo.cn',
            'sudaref': '',
            'ua': 'php-sso_sdk_client-0.6.36',
            '_rand': rand,
        }
        response = await cls._request_post(
            url=VisitorUrl.VISITOR_ENTER_URL,
            data=data, headers=build_risk_flow_step_headers(RiskFlowStep.S2_VISITOR_ENTER, default_headers),
            cookies=cookies,
        )
        merge_cookies(cookies, cls._extra_set_cookies_from_response(response))
        return rand

    @classmethod
    async def _preload_risk_scripts(cls, *, rand: str, cookies: dict[str, str]) -> None:
        """RiskFlowStep 3/4: 模拟加载风控脚本 (仅发起请求, 不使用响应内容), 并合并响应 Cookies 到传入字典"""
        default_headers = cls._get_omega_requests_default_headers()
        mini_response = await cls._request_get(
            url=VisitorUrl.VISITOR_MINI_JS_URL,
            headers=build_risk_flow_step_headers(
                RiskFlowStep.S3_PRELOAD_MINI_SCRIPTS,
                default_headers=default_headers,
                referer=f'{VisitorUrl.VISITOR_ENTER_URL}?_rand={rand}',
            ),
            cookies=cookies,
        )
        merge_cookies(cookies, cls._extra_set_cookies_from_response(mini_response))

        umd_response = await cls._request_get(
            url=VisitorUrl.VISITOR_UMD_JS_URL,
            headers=build_risk_flow_step_headers(
                RiskFlowStep.S4_PRELOAD_UMD_SCRIPTS,
                default_headers=default_headers,
                referer='https://visitor.passport.weibo.cn/',
            ),
            cookies=cookies,
        )
        merge_cookies(cookies, cls._extra_set_cookies_from_response(umd_response))

    @classmethod
    async def _fetch_visitor_rid(cls, *, cookies: dict[str, str]) -> str:
        """RiskFlowStep 5: 构造指纹并向 bd 接口发送加密数据以获取访客 rid, 并合并响应 Cookies 到传入字典

        bd 未返回 rid 时回退为毫秒时间戳
        """
        default_headers = cls._get_omega_requests_default_headers()
        bd_payload = make_bd_payload(build_fingerprint())
        response = await cls._request_post(
            url=VisitorUrl.BD_PAYLOAD_URL,
            data={'data': bd_payload, 'from': 'android-visitor'},
            headers=build_risk_flow_step_headers(RiskFlowStep.S5_GENE_VISITOR_RID, default_headers),
            cookies=cookies,
        )
        merge_cookies(cookies, cls._extra_set_cookies_from_response(response))

        parsed = parse_loose_json_object(cls._parse_content_as_text(response)) or {}
        rid = parsed.get('data', {}).get('rid')
        if not rid:
            logger.opt(colors=True).warning(
                f'<lc>Weibo</lc> | bd 接口未返回 rid, 将使用时间戳回退值, 返回内容: {parsed!r}'
            )
            rid = str(int(time.time() * 1000))
        return str(rid)

    @classmethod
    async def _post_genvisitor(
            cls,
            *,
            page_params: WeiboVisitorPageParams,
            rid: str,
            rand: str,
            cookies: dict[str, str],
    ) -> None:
        """RiskFlowStep 6: POST genvisitor2 接口签发访客 tid, 校验返回状态并合并 Cookies 到传入字典"""
        default_headers = cls._get_omega_requests_default_headers()
        data = {
            'cb': VisitorUrl.VISITOR_CALLBACK_NAME,
            'ver': page_params.ver,
            'request_id': page_params.request_id,
            'tid': cookies.get('tid', ''),
            'from': page_params.from_,
            'webdriver': 'false',
            'rid': rid,
            'return_url': page_params.return_url,
        }
        response = await cls._request_post(
            url=VisitorUrl.GENVISITOR_URL,
            data=data,
            headers=build_risk_flow_step_headers(
                RiskFlowStep.S6_GENVISITOR_TID,
                default_headers=default_headers,
                referer=f'{VisitorUrl.VISITOR_ENTER_URL}?_rand={rand}',
            ),
            cookies=cookies,
        )
        merge_cookies(cookies, cls._extra_set_cookies_from_response(response))

        parsed = parse_callback_js(cls._parse_content_as_text(response), cb_name=VisitorUrl.VISITOR_CALLBACK_NAME)
        if parsed is None:
            raise RuntimeError('解析 genvisitor2 返回失败 (非标准 JSONP)')

        gen_result = WeiboGenVisitorResult.model_validate(parsed)
        if (
                gen_result.retcode != LoginStatusCode.RETCODE_SUCCESS
                or gen_result.data is None
                or not gen_result.data.tid
        ):
            raise RuntimeError(f'genvisitor2 签发访客 tid 失败, 返回内容: {parsed!r}')
        merge_cookies(cookies, {'tid': gen_result.data.tid})

    @classmethod
    async def refresh_visitor_cookies(cls) -> bool:
        """完整执行访客风控流程刷新 Cookies

        先在局部累积候选 Cookies 并执行全部流程步骤, 全部成功后一次性替换全局凭据缓存并落库;
        任一步失败或异常时全局凭据保持原状
        """
        try:
            cookies: dict[str, str] = {}
            page_params = await cls._fetch_initial_page(cookies=cookies)
            rand = await cls._post_visitor_enter(cookies=cookies)
            await cls._preload_risk_scripts(rand=rand, cookies=cookies)
            rid = await cls._fetch_visitor_rid(cookies=cookies)
            await cls._post_genvisitor(page_params=page_params, rid=rid, rand=rand, cookies=cookies)
        except Exception as e:
            logger.opt(colors=True).error(f'<lc>Weibo</lc> | <r>访客 Cookies 刷新异常</r>, {e}')
            return False

        WEIBO_CREDENTIAL_MANAGER.replace_cookies(WeiboCookiesData.model_validate(cookies))
        await WEIBO_CREDENTIAL_MANAGER.rebuild_to_database()
        logger.opt(colors=True).success('<lc>Weibo</lc> | <lg>访客 Cookies 刷新成功</lg>')
        return True

    @classmethod
    async def check_visitor_cookies_valid(cls) -> bool:
        """以固定探测样本用户 uid 轻量探测当前 Cookies 是否可用"""
        url = f'{cls._get_root_url()}/api/container/getIndex'
        params = {
            'type': 'uid',
            'value': WEIBO_DETECTION_SAMPLE_UID,
            'containerid': f'100505{WEIBO_DETECTION_SAMPLE_UID}',
        }

        try:
            data = await cls._get_resource_as_json(url=url, params=params)
        except Exception as e:
            logger.opt(colors=True).warning(f'<lc>Weibo</lc> | 访客 Cookies 探测请求异常, {e}')
            return False
        return isinstance(data, dict) and data.get('ok') == 1

    @classmethod
    async def ensure_cookies(cls, *, force_refresh: bool = False) -> None:
        """确保全局凭据缓存中有可用的 Cookies, 依次经由内存缓存、数据库、访客风控流程

        :param force_refresh: 跳过内存缓存与数据库检查, 直接执行完整访客风控流程
        """
        if force_refresh:
            await cls.refresh_visitor_cookies()
            return

        if WEIBO_CREDENTIAL_MANAGER.get_cookie('SUB') or WEIBO_CREDENTIAL_MANAGER.get_cookie('SUBP'):
            return

        await WEIBO_CREDENTIAL_MANAGER.load_from_database()
        if WEIBO_CREDENTIAL_MANAGER.get_cookie('SUB') or WEIBO_CREDENTIAL_MANAGER.get_cookie('SUBP'):
            return

        await cls.refresh_visitor_cookies()

    # ------------------------------------------------------------------ #
    # 扫码登录流程
    # ------------------------------------------------------------------ #

    @staticmethod
    def _harvest_session_cookies(session: 'HTTPClientSession') -> dict[str, str]:
        """从驱动会话的 CookieJar 中收割全部 Cookies (兼容 aiohttp/httpx driver)"""
        client = getattr(session, 'client', None)
        if client is None:
            return {}

        # aiohttp driver: client.cookie_jar 迭代产生 Morsel
        cookie_jar = getattr(client, 'cookie_jar', None)
        if cookie_jar is not None:
            return {morsel.key: morsel.value for morsel in cookie_jar if morsel.value}

        # httpx driver: client.cookies.jar 迭代产生 http.cookiejar.Cookie
        httpx_cookies = getattr(client, 'cookies', None)
        jar = getattr(httpx_cookies, 'jar', None)
        if jar is not None:
            return {cookie.name: cookie.value for cookie in jar if cookie.value}

        return {}

    @classmethod
    async def _request_harvesting_cookies(
            cls,
            url: str,
            *,
            cookies: dict[str, str] | None = None,
            headers: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """发起一次 GET 请求, 收割会话级 Cookies (含自动跟随的重定向链中间跳设置的 Cookies) 及响应 set-cookie

        底层 driver 固定跟随重定向且逐请求丢弃会话, 登录跨域重定向链各跳的 set-cookie
        只能在请求结束后从会话 CookieJar 中收割
        """
        requests = cls._init_omega_requests(headers=headers, cookies=cookies)
        async with requests.get_session() as session:
            response = await session.request(Request(method='GET', url=url))
            harvested = cls._harvest_session_cookies(session)

        merged = dict(cookies) if cookies else {}
        merge_cookies(merged, cls._extra_set_cookies_from_response(response))
        merge_cookies(merged, harvested)
        return merged

    @classmethod
    async def _fetch_login_csrf_token(cls) -> str:
        """访问登录入口获取 X-CSRF-TOKEN"""
        cookies = await cls._request_harvesting_cookies(LoginUrl.SSO_SIGNIN_URL)

        csrf_token = cookies.get('X-CSRF-TOKEN')
        if not csrf_token:
            raise RuntimeError('访问登录入口未获取到 X-CSRF-TOKEN')
        return csrf_token

    @classmethod
    async def _fetch_login_rid(cls, *, csrf_token: str) -> str:
        """登录前访问 bd 接口获取 rid"""
        bd_payload = make_bd_payload(build_fingerprint())
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'origin': 'https://passport.weibo.com',
            'referer': 'https://passport.weibo.com/',
        })
        response = await cls._request_post(
            url=VisitorUrl.BD_PAYLOAD_URL,
            data={'data': bd_payload, 'from': 'weibo'},
            headers=headers,
            cookies={'X-CSRF-TOKEN': csrf_token},
        )

        parsed = parse_loose_json_object(cls._parse_content_as_text(response))
        if parsed is None:
            raise RuntimeError('解析 bd 接口返回失败')
        bd_result = WeiboBdResponse.model_validate(parsed)
        if (
                bd_result.retcode != LoginStatusCode.RETCODE_SUCCESS
                or bd_result.data is None
                or not bd_result.data.rid
        ):
            raise RuntimeError(f'获取登录 rid 失败, 返回内容: {parsed!r}')
        return bd_result.data.rid

    @classmethod
    async def get_login_qrcode(cls) -> WeiboLoginQrCodeInfo:
        """获取登录二维码信息 (含 qrid/rid/csrf_token)"""
        csrf_token = await cls._fetch_login_csrf_token()

        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'x-csrf-token': csrf_token,
            'referer': 'https://passport.weibo.com/',
        })
        qr_response = await cls._get_resource_as_json(
            url=LoginUrl.QRCODE_IMAGE_URL,
            params={'entry': 'wapsso', 'size': '180'},
            headers=headers,
            cookies={'X-CSRF-TOKEN': csrf_token},
        )
        qr_image = WeiboQrCodeImage.model_validate(qr_response)
        if qr_image.retcode != LoginStatusCode.RETCODE_SUCCESS or qr_image.data is None:
            raise RuntimeError(f'获取登录二维码失败, 返回内容: {qr_response!r}')

        # 申请二维码后需等待片刻再获取 rid, 立即请求 bd 接口将无法通过校验
        await asyncio.sleep(3)
        rid = await cls._fetch_login_rid(csrf_token=csrf_token)

        return WeiboLoginQrCodeInfo.model_validate({
            'qrid': qr_image.data.qrid,
            'image_url': str(qr_image.data.image),
            'rid': rid,
            'csrf_token': csrf_token,
        })

    @classmethod
    async def generate_login_qrcode(cls, qrcode_info: WeiboLoginQrCodeInfo) -> 'TemporaryResource':
        """下载登录二维码图片到本地"""
        return await cls.download_resource(url=qrcode_info.image_url, subdir='login_qr')

    @classmethod
    async def check_qrcode_login(
            cls,
            qrcode_info: WeiboLoginQrCodeInfo,
    ) -> tuple[WeiboQrCodeCheck, dict[str, str] | None]:
        """检查二维码登录状态

        :param qrcode_info: 登录二维码信息
        :return: (WeiboQrCodeCheck, 登录成功时从重定向链收割的 Cookies, 未成功为 None)
        """
        headers = cls._get_omega_requests_default_headers()
        headers.update({
            'x-csrf-token': qrcode_info.csrf_token,
            'referer': 'https://passport.weibo.com/',
        })
        check_response = await cls._get_resource_as_json(
            url=LoginUrl.QRCODE_CHECK_URL,
            params={
                'entry': 'wapsso',
                'source': 'wapssowb',
                'url': 'https://m.weibo.cn/',
                'qrid': qrcode_info.qrid,
                'rid': qrcode_info.rid,
                'ver': '20250520',
            },
            headers=headers,
            cookies={'X-CSRF-TOKEN': qrcode_info.csrf_token},
        )
        check_data = WeiboQrCodeCheck.model_validate(check_response)

        if (
                check_data.retcode != LoginStatusCode.RETCODE_SUCCESS
                or check_data.data is None
                or check_data.data.url is None
        ):
            return check_data, None

        chain_headers = cls._get_omega_requests_default_headers()
        chain_headers.update({'referer': 'https://passport.weibo.com/'})
        login_cookies = await cls._request_harvesting_cookies(str(check_data.data.url), headers=chain_headers)
        return check_data, login_cookies

    @classmethod
    async def login_with_qrcode(cls, qrcode_info: WeiboLoginQrCodeInfo) -> bool:
        """轮询扫码登录状态直至登录成功, 成功后将收割的登录 Cookies 并入全局凭据并落库"""
        attempt = 0
        while True:
            check_data, login_cookies = await cls.check_qrcode_login(qrcode_info=qrcode_info)

            if check_data.retcode == LoginStatusCode.RETCODE_SUCCESS and login_cookies is not None:
                logger.opt(colors=True).success('<lc>Weibo</lc> | 扫码登录: 成功')
                break
            elif attempt >= cls._LOGIN_QR_MAX_ATTEMPT:
                logger.opt(colors=True).error(f'<lc>Weibo</lc> | 扫码登录: {check_data.msg}, 等待超时')
                raise RuntimeError('等待超时')
            elif check_data.retcode == LoginStatusCode.RETCODE_QR_WAIT_SCAN:
                logger.opt(colors=True).debug(f'<lc>Weibo</lc> | 扫码登录: {check_data.msg}, 待扫码')
                attempt += 1
            elif check_data.retcode == LoginStatusCode.RETCODE_QR_WAIT_CONFIRM:
                logger.opt(colors=True).debug(f'<lc>Weibo</lc> | 扫码登录: {check_data.msg}, 待确认')
                attempt += 1
            elif check_data.retcode == LoginStatusCode.RETCODE_QR_EXPIRED:
                logger.opt(colors=True).error(f'<lc>Weibo</lc> | 扫码登录: {check_data.msg}, 二维码过期')
                raise RuntimeError('登录二维码过期')
            else:
                logger.opt(colors=True).warning(f'<lc>Weibo</lc> | 扫码登录: {check_data.msg}')
                attempt += 1
            await asyncio.sleep(cls._LOGIN_QR_POLL_INTERVAL)

        # 登录成功, 收割的登录 Cookies 并入现有凭据, 一次性替换并落库
        merged_cookies = {**WEIBO_CREDENTIAL_MANAGER.cookies, **login_cookies}
        WEIBO_CREDENTIAL_MANAGER.replace_cookies(WeiboCookiesData.model_validate(merged_cookies))
        await WEIBO_CREDENTIAL_MANAGER.rebuild_to_database()
        return await cls.check_login()

    @classmethod
    async def check_login(cls) -> bool:
        """检查当前凭据登录状态"""
        headers = cls._get_default_headers()
        if xsrf_token := WEIBO_CREDENTIAL_MANAGER.get_cookie('XSRF-TOKEN'):
            headers.update({'x-xsrf-token': xsrf_token})

        try:
            config_response = await cls._get_resource_as_json(url=f'{cls._get_root_url()}/api/config', headers=headers)
            config_data = WeiboApiConfig.model_validate(config_response)
        except Exception as e:
            logger.opt(colors=True).error(f'<lc>Weibo</lc> | <r>登录状态检查失败</r>, 访问异常, {e}')
            return False

        if config_data.data is None:
            logger.opt(colors=True).warning(f'<lc>Weibo</lc> | 登录状态检查返回异常, {config_response!r}')
            return False
        elif config_data.data.login:
            logger.opt(colors=True).success(
                f'<lc>Weibo</lc> | <lg>登录已验证</lg>, 登录用户 uid: {config_data.data.uid}'
            )
            return True
        else:
            logger.opt(colors=True).debug('<lc>Weibo</lc> | 当前凭据为访客状态, 未登录')
            return False


__all__ = [
    'WeiboCredential',
]
