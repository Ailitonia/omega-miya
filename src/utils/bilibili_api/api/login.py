"""
@Author         : Ailitonia
@Date           : 2024/11/4 16:49:50
@FileName       : login.py
@Project        : omega-miya
@Description    : bilibili 用户凭据相关 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

Reference:
https://socialsisteryi.github.io/bilibili-API-collect/docs/login/cookie_refresh.html
"""

import asyncio
import binascii
import time
from typing import TYPE_CHECKING

import qrcode
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA
from lxml import etree
from nonebot.log import logger
from nonebot.utils import run_sync

from .base import BilibiliCommon
from ..config import bilibili_api_config
from ..credential_manager import BILIBILI_CREDENTIAL_MANAGER, BilibiliCookiesData, BilibiliLoginCookiesData
from ..models import (
    WebConfirmRefreshInfo,
    WebCookieInfo,
    WebCookieRefreshInfo,
    WebInterfaceNav,
    WebQrcodeGenerateInfo,
    WebQrcodePollInfo,
)

if TYPE_CHECKING:
    from src.resource import TemporaryResource
    from src.utils.omega_common_api.types import CookieTypes

_PUB_KEY = RSA.importKey("""\
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLgd2OAkcGVtoE3ThUREbio0Eg
Uc/prcajMKXvkCKFCWhJYJcLkcM2DKKcSeFpD/j6Boy538YXnR6VhcuUJOhH2x71
nzPjfdTcqMz7djHum0qSZA0AyCBDABUqCrfNgCiJ00Ra7GmRj+YCK1NJEuewlb40
JNrRuoEUXpabUzGB8QIDAQAB
-----END PUBLIC KEY-----""")


class BilibiliCredential(BilibiliCommon):
    """Bilibili 凭据操作类"""

    @staticmethod
    def _get_correspond_path() -> str:
        """根据时间生成 CorrespondPath"""
        ts = round(time.time() * 1000)
        cipher = PKCS1_OAEP.new(_PUB_KEY, SHA256)
        encrypted = cipher.encrypt(f'refresh_{ts}'.encode())
        return binascii.b2a_hex(encrypted).decode()

    @staticmethod
    @run_sync
    def _make_qrcode(content: str) -> 'TemporaryResource':
        qrcode_filename = f'{SHA256.new(content.encode()).hexdigest()}.png'
        qrcode_file = bilibili_api_config.get_temporary_file_path('login_qr', qrcode_filename)
        with qrcode_file.open('wb') as f:
            qrcode.make(data=content).save(f)
        return qrcode_file

    @classmethod
    async def get_login_qrcode(cls) -> WebQrcodeGenerateInfo:
        """获取登录二维码信息"""
        url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate'
        data = await cls._get_resource_as_json(url=url)
        return WebQrcodeGenerateInfo.model_validate(data)

    @classmethod
    async def generate_login_qrcode(cls, qrcode_info: WebQrcodeGenerateInfo) -> 'TemporaryResource':
        """生成登录二维码"""
        return await cls._make_qrcode(qrcode_info.data.url)

    @classmethod
    async def check_qrcode_login(
            cls,
            qrcode_info: WebQrcodeGenerateInfo
    ) -> tuple[WebQrcodePollInfo, dict[str, str]]:
        """检查二维码登录状态

        :param qrcode_info: 登录二维码信息
        :return: (WebQrcodePollInfo, SetCookiesDict)
        """
        url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll'
        params = {'qrcode_key': qrcode_info.data.qrcode_key}
        login_response = await cls._request_get(url=url, params=params)

        login_data = WebQrcodePollInfo.model_validate(cls._parse_content_as_json(login_response))
        login_set_cookies = cls._extra_set_cookies_from_response(response=login_response)

        return login_data, login_set_cookies

    @classmethod
    async def login_with_qrcode(cls, qrcode_info: WebQrcodeGenerateInfo) -> bool:
        attempt = 0
        while True:
            login_info, login_set_cookies = await cls.check_qrcode_login(qrcode_info=qrcode_info)

            if login_info.data.code == 0:
                logger.opt(colors=True).success('<lc>Bilibili</lc> | 扫码登录: 成功')
                break
            elif attempt >= 10:
                logger.opt(colors=True).error(f'<lc>Bilibili</lc> | 扫码登录: {login_info.data.message}, 等待超时')
                raise RuntimeError('等待超时')
            elif login_info.data.code == 86101:
                logger.opt(colors=True).debug(f'<lc>Bilibili</lc> | 扫码登录: {login_info.data.message}, 待扫码')
                attempt += 1
            elif login_info.data.code == 86090:
                logger.opt(colors=True).debug(f'<lc>Bilibili</lc> | 扫码登录: {login_info.data.message}, 待确认')
                attempt += 1
            elif login_info.data.code == 86038:
                logger.opt(colors=True).error(f'<lc>Bilibili</lc> | 扫码登录: {login_info.data.message}, 二维码过期')
                raise RuntimeError('登录二维码过期')
            else:
                logger.opt(colors=True).warning(f'<lc>Bilibili</lc> | 扫码登录: {login_info.data.message}')
                attempt += 1
            await asyncio.sleep(6)

        login_set_cookies.update({'ac_time_value': login_info.data.refresh_token})
        BILIBILI_CREDENTIAL_MANAGER.clear_cookies()
        BILIBILI_CREDENTIAL_MANAGER.update_cookies(**login_set_cookies)

        await BILIBILI_CREDENTIAL_MANAGER.rebuild_to_database()
        return await cls.check_valid()

    @classmethod
    async def check_need_refresh(cls) -> bool:
        """检查 Cookies 是否需要刷新"""
        if (bili_jct := BILIBILI_CREDENTIAL_MANAGER.get_cookie('bili_jct')) is None:
            return True

        url = 'https://passport.bilibili.com/x/passport-login/web/cookie/info'
        params = {'csrf': bili_jct}

        data = await cls._get_resource_as_json(url=url, params=params)
        return WebCookieInfo.model_validate(data).data.refresh

    @classmethod
    async def check_valid(cls) -> bool:
        """检查 cookies 是否有效"""
        url = 'https://api.bilibili.com/x/web-interface/nav'

        try:
            data = await cls._get_resource_as_json(url=url, cookies=BILIBILI_CREDENTIAL_MANAGER.login_cookies)
            verify = WebInterfaceNav.model_validate(data)
        except Exception as e:
            logger.opt(colors=True).error(f'<lc>Bilibili</lc> | <r>登录验证失败</r>, 访问失败, {e}')
            return False

        if verify.code == -101 or (verify.code == 0 and not verify.data.isLogin):
            # 明确的未登录/凭据失效状态, 清除凭据
            BILIBILI_CREDENTIAL_MANAGER.clear_cookies()
            logger.opt(colors=True).warning(f'<lc>Bilibili</lc> | <r>登录验证失败</r>, 状态异常, {verify.message}')
            return False
        elif verify.code != 0:
            # 其他异常状态码 (如风控 -412) 视为临时状态, 保留凭据
            logger.opt(colors=True).warning(
                f'<lc>Bilibili</lc> | 登录验证请求返回异常状态码: {verify.code}, {verify.message}, 保留当前凭据'
            )
            return False
        elif verify.data.mid != BILIBILI_CREDENTIAL_MANAGER.get_cookie('DedeUserID'):
            BILIBILI_CREDENTIAL_MANAGER.clear_cookies()
            logger.opt(colors=True).warning('<lc>Bilibili</lc> | <r>登录验证失败</r>, 状态异常, 用户 UID 不匹配')
            return False
        else:
            logger.opt(colors=True).success(f'<lc>Bilibili</lc> | <lg>登录已验证</lg>, 登录用户: {verify.data.uname}')
            return True

    @classmethod
    async def get_refresh_csrf(cls) -> str:
        """获取 refresh_csrf"""
        url = f'https://www.bilibili.com/correspond/1/{cls._get_correspond_path()}'

        # 不知道什么原因, 这里不暂停等一下就只会返回 404, 明明时间是同步的,
        # 另外这里只 sleep(1) 也不行, 必须等待足够长的时间
        await asyncio.sleep(3)

        content = await cls._get_resource_as_text(url=url, cookies=BILIBILI_CREDENTIAL_MANAGER.login_cookies)

        try:
            refresh_csrf_item = etree.HTML(content).xpath('/html/body/div[@id="1-name"]').pop(0)
            refresh_csrf = refresh_csrf_item.text
        except Exception as e:
            raise RuntimeError(f'parsing API refresh_csrf not found, {e}') from e
        # 解析失败或未解析到都抛出 RuntimeError
        if not refresh_csrf:
            raise RuntimeError('parsing API refresh_csrf failed')

        return refresh_csrf

    @classmethod
    async def confirm_cookies_refresh(
            cls,
            csrf: str,
            refresh_token: str | None,
            *,
            cookies: 'CookieTypes' = None,
    ) -> WebConfirmRefreshInfo:
        """确认 Cookies 更新, 该步操作将让旧的 refresh_token 对应的 Cookie 失效

        :param csrf: 从新的 Cookies 中获取, 位于 Cookies 中的 bili_jct 字段
        :param refresh_token: 在刷新前配置中的 ac_time_value 获取, 并非刷新后返回的值
        :param cookies: 请求使用的 Cookies, 默认使用全局凭据缓存
        """
        url = 'https://passport.bilibili.com/x/passport-login/web/confirm/refresh'
        params = {'csrf': csrf, 'refresh_token': refresh_token or ''}

        data = await cls._post_acquire_as_json(url=url, params=params, cookies=cookies)
        return WebConfirmRefreshInfo.model_validate(data)

    @classmethod
    async def refresh_cookies(cls) -> bool:
        """刷新用户 Cookies

        先在局部构造候选凭据并以其执行全部刷新步骤, 全部成功后一次性替换全局凭据缓存并落库;
        任一步失败或异常时全局凭据保持原状
        """
        url = 'https://passport.bilibili.com/x/passport-login/web/cookie/refresh'

        # refresh spm_prefix, 刷新失败时降级为使用回退值, 不中断激活流程
        try:
            await cls._init_spm_prefix()
        except Exception as e:
            logger.opt(colors=True).warning(f'<lc>Bilibili</lc> | 刷新 spm_prefix 失败, 将使用回退值, {e}')

        try:
            refresh_csrf = await cls.get_refresh_csrf()
            old_refresh_token = BILIBILI_CREDENTIAL_MANAGER.get_cookie('ac_time_value')
            params = {
                'csrf': BILIBILI_CREDENTIAL_MANAGER.get_cookie('bili_jct'),
                'refresh_csrf': refresh_csrf,
                'refresh_token': old_refresh_token,
                'source': 'main_web',
            }

            response = await cls._request_post(
                url=url, params=params, cookies=BILIBILI_CREDENTIAL_MANAGER.login_cookies
            )
            refresh_info = WebCookieRefreshInfo.model_validate(cls._parse_content_as_json(response))

            if refresh_info.code != 0:
                logger.opt(colors=True).error(f'<lc>Bilibili</lc> | 刷新用户 Cookies 失败, {refresh_info}')
                return False

            # 构造候选凭据 (新的 set-cookies 及 refresh_token), 后续步骤均基于候选凭据执行, 不更新全局缓存
            new_cookies = cls._extra_set_cookies_from_response(response=response)
            candidate_data = BilibiliCookiesData.model_validate({
                **BILIBILI_CREDENTIAL_MANAGER.cookies,
                **new_cookies,
                'ac_time_value': refresh_info.data.refresh_token,
            })

            # 更新 wbi
            ticket_cookies = await cls._fetch_ticket_wbi_cookies(
                bili_jct=candidate_data.bilibili_api_jct,
                cookies=BilibiliLoginCookiesData.model_validate(candidate_data.as_dict).as_dict,
            )
            candidate_data = BilibiliCookiesData.model_validate({**candidate_data.as_dict, **ticket_cookies})

            # 激活 buvid
            buvid_cookies = await cls._fetch_buvid_cookies(base_cookies=candidate_data.as_dict)
            candidate_data = BilibiliCookiesData.model_validate({**candidate_data.as_dict, **buvid_cookies})

            # 确认更新并注销旧 token
            confirm_result = await cls.confirm_cookies_refresh(
                csrf=new_cookies['bili_jct'],
                refresh_token=old_refresh_token,
                cookies=BilibiliLoginCookiesData.model_validate(candidate_data.as_dict).as_dict,
            )
            if confirm_result.code != 0:
                logger.opt(colors=True).error(
                    f'<lc>Bilibili</lc> | 确认更新用户 Cookies 失败, {confirm_result.message}'
                )
                return False
        except Exception as e:
            # 刷新流程异常, 全局凭据未被修改, 保持原状
            logger.opt(colors=True).error(f'<lc>Bilibili</lc> | 刷新用户 Cookies 异常, {e}')
            return False

        # 全部步骤成功, 一次性替换全局凭据并落库
        BILIBILI_CREDENTIAL_MANAGER.replace_cookies(candidate_data)
        await BILIBILI_CREDENTIAL_MANAGER.rebuild_to_database()
        return await cls.check_valid()


__all__ = [
    'BilibiliCredential',
]
