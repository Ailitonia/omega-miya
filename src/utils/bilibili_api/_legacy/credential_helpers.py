"""
@Author         : Ailitonia
@Date           : 2024/5/30 上午12:03
@FileName       : credential_helpers
@Project        : nonebot2_miya
@Description    : bilibili 凭据操作工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

Reference:
https://socialsisteryi.github.io/bilibili-API-collect/docs/login/cookie_refresh.html
"""

import asyncio
import binascii
import re
import time
from urllib.parse import parse_qs, urlparse

import qrcode
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA
from lxml import etree
from nonebot import get_driver, logger
from nonebot.utils import run_sync

from src.resource import TemporaryResource
from .api_base import BilibiliCommon
from .config import bilibili_config, bilibili_resource_config
from .model import (
    BilibiliWebConfirmRefreshInfo,
    BilibiliWebCookieInfo,
    BilibiliWebCookieRefreshInfo,
    BilibiliWebInterfaceNav,
    BilibiliWebQrcodeGenerateInfo,
    BilibiliWebQrcodePollInfo,
)

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
    async def save_cookies_to_db() -> None:
        await bilibili_config.save_to_database()

    @staticmethod
    async def load_cookies_from_db() -> None:
        await bilibili_config.load_from_database()

    @staticmethod
    def _get_correspond_path() -> str:
        """根据时间生成 CorrespondPath"""
        ts = round(time.time() * 1000)
        cipher = PKCS1_OAEP.new(_PUB_KEY, SHA256)
        encrypted = cipher.encrypt(f'refresh_{ts}'.encode())
        return binascii.b2a_hex(encrypted).decode()

    @staticmethod
    @run_sync
    def _make_qrcode(content: str) -> TemporaryResource:
        qrcode_filename = f'{SHA256.new(content.encode()).hexdigest()}.png'
        qrcode_file = bilibili_resource_config.default_tmp_folder('login_qr', qrcode_filename)
        with qrcode_file.open('wb') as f:
            qrcode.make(data=content).save(f)
        return qrcode_file

    @classmethod
    async def get_login_qrcode(cls) -> BilibiliWebQrcodeGenerateInfo:
        """获取登录二维码信息"""
        url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate?source=main-fe-header'
        data = await cls._get_json(url=url)
        return BilibiliWebQrcodeGenerateInfo.model_validate(data)

    @classmethod
    async def generate_login_qrcode(cls, qrcode_info: BilibiliWebQrcodeGenerateInfo) -> TemporaryResource:
        """生成登录二维码"""
        return await cls._make_qrcode(qrcode_info.data.url)

    @classmethod
    async def check_qrcode_login(cls, qrcode_info: BilibiliWebQrcodeGenerateInfo) -> BilibiliWebQrcodePollInfo:
        """检查二维码登录状态"""
        url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/poll'
        params = {'qrcode_key': qrcode_info.data.qrcode_key}
        data = await cls._get_json(url=url, params=params)
        return BilibiliWebQrcodePollInfo.model_validate(data)

    @classmethod
    async def login_with_qrcode(cls, qrcode_info: BilibiliWebQrcodeGenerateInfo) -> bool:
        attempt = 0
        while True:
            login_info = await cls.check_qrcode_login(qrcode_info=qrcode_info)
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

        cookies = parse_qs(urlparse(url=login_info.data.url).query)
        bilibili_config.clear_all()
        bilibili_config.bili_sessdata = cookies.get('SESSDATA', [])[0]
        bilibili_config.bili_jct = cookies.get('bili_jct', [])[0]
        bilibili_config.bili_dedeuserid = cookies.get('DedeUserID', [])[0]
        bilibili_config.bili_ac_time_value = login_info.data.refresh_token

        await cls.save_cookies_to_db()
        return await cls.check_valid()

    @classmethod
    async def check_need_refresh(cls) -> bool:
        """检查 Cookies 是否需要刷新"""
        if bilibili_config.bili_jct is None:
            return True

        url = 'https://passport.bilibili.com/x/passport-login/web/cookie/info'
        params = {'csrf': bilibili_config.bili_jct}

        data = await cls._get_json(url=url, params=params)
        return BilibiliWebCookieInfo.model_validate(data).data.refresh

    @classmethod
    async def check_valid(cls) -> bool:
        """检查 cookies 是否有效"""
        url = 'https://api.bilibili.com/x/web-interface/nav'

        try:
            data = await cls._get_json(url=url, cookies=bilibili_config.bili_cookies)
            verify = BilibiliWebInterfaceNav.model_validate(data)
        except Exception as e:
            logger.opt(colors=True).warning(f'<lc>Bilibili</lc> | <r>Cookie 验证失败</r>, 访问失败, {e}')
            return False

        if verify.code != 0 or not verify.data.isLogin:
            bilibili_config.clear_all()
            logger.opt(colors=True).warning(
                f'<lc>Bilibili</lc> | <r>Cookie 验证失败</r>, 登录状态异常, {verify.message}')
            return False
        elif verify.data.mid != bilibili_config.bili_dedeuserid:
            bilibili_config.clear_all()
            logger.opt(colors=True).warning('<lc>Bilibili</lc> | <r>Cookie 验证失败</r>, 登录状态异常, 用户 UID 不匹配')
            return False
        else:
            logger.opt(colors=True).success(
                f'<lc>Bilibili</lc> | <lg>Cookie 已验证</lg>, 登录用户: {verify.data.uname}')
            return True

    @classmethod
    async def get_refresh_csrf(cls) -> str:
        """获取 refresh_csrf"""
        url = f'https://www.bilibili.com/correspond/1/{cls._get_correspond_path()}'

        # 不知道什么原因, 这里不暂停等一下就只会返回 404, 明明时间是同步的, 另外这里只 sleep(1) 也不行, 必须等两秒及以上
        await asyncio.sleep(2)

        content = await cls._get_resource_as_text(url=url, cookies=bilibili_config.bili_cookies)
        refresh_csrf = etree.HTML(content).xpath('/html/body/div[@id="1-name"]').pop(0).text
        return refresh_csrf

    @classmethod
    async def confirm_cookies_refresh(cls, csrf: str, refresh_token: str | None) -> BilibiliWebConfirmRefreshInfo:
        """确认 Cookies 更新, 该步操作将让旧的 refresh_token 对应的 Cookie 失效

        :param csrf: 从新的 Cookies 中获取, 位于 Cookies 中的 bili_jct 字段
        :param refresh_token: 在刷新前配置中的 ac_time_value 获取, 并非刷新后返回的值
        """
        url = 'https://passport.bilibili.com/x/passport-login/web/confirm/refresh'
        params = {'csrf': csrf, 'refresh_token': refresh_token}

        data = await cls._post_json(url=url, params=params)
        return BilibiliWebConfirmRefreshInfo.model_validate(data)

    @classmethod
    async def refresh_cookies(cls) -> bool:
        """刷新用户 Cookies"""
        url = 'https://passport.bilibili.com/x/passport-login/web/cookie/refresh'

        refresh_csrf = await cls.get_refresh_csrf()
        old_refresh_token = bilibili_config.bili_ac_time_value
        params = {
            'csrf': bilibili_config.bili_jct,
            'refresh_csrf': refresh_csrf,
            'refresh_token': old_refresh_token,
            'source': 'main_web',
        }

        response = await cls._request_post(url=url, params=params, cookies=bilibili_config.bili_cookies)
        refresh_info = BilibiliWebCookieRefreshInfo.model_validate(cls._parse_content_as_json(response))

        if refresh_info.code != 0:
            logger.opt(colors=True).error(f'<lc>Bilibili</lc> | 刷新用户 Cookies 失败, {refresh_info}')
            return False

        new_cookies = {}
        for k, v in response.headers.items():
            if re.match(re.compile('set-cookie', re.IGNORECASE), k):
                item = v.split(';', maxsplit=1)[0].strip().split('=', maxsplit=1)
                if len(item) == 2:
                    new_cookies.update({item[0]: item[1]})

        if new_cookies['SESSDATA']:
            bilibili_config.bili_sessdata = new_cookies['SESSDATA']
        if new_cookies['bili_jct']:
            bilibili_config.bili_jct = new_cookies['bili_jct']
        if new_cookies['DedeUserID']:
            bilibili_config.bili_dedeuserid = new_cookies['DedeUserID']
        bilibili_config.bili_ac_time_value = refresh_info.data.refresh_token
        bilibili_config.update_cookies_cache(**new_cookies)

        # 激活 buvid
        await cls.update_buvid_params()

        # 确认更新并注销旧 token
        confirm_result = await cls.confirm_cookies_refresh(
            csrf=new_cookies['bili_jct'], refresh_token=old_refresh_token
        )
        if confirm_result.code != 0:
            logger.opt(colors=True).error(f'<lc>Bilibili</lc> | 确认更新用户 Cookies 失败, {confirm_result.message}')
            return False

        await cls.save_cookies_to_db()
        return await cls.check_valid()


async def _refresh_bilibili_login_status() -> None:
    """检查 bilibili 登录状态, 根据需要刷新 Cookies"""
    logger.opt(colors=True).debug('<lc>Bilibili</lc> | 开始检查用户 Cookies 状态')
    bc = BilibiliCredential()

    is_valid = await bc.check_valid()
    if not is_valid:
        logger.opt(colors=True).warning('<lc>Bilibili</lc> | <r>用户 Cookies 未配置或验证失败</r>, 部分功能可能不可用')
        return

    await bc.update_buvid_params()
    need_refresh = await bc.check_need_refresh()
    if need_refresh:
        logger.opt(colors=True).warning('<lc>Bilibili</lc> | <ly>用户 Cookies 需要刷新</ly>, 正在尝试刷新中')
        refresh_result = await bc.refresh_cookies()
        if refresh_result:
            logger.opt(colors=True).warning('<lc>Bilibili</lc> | <lg>用户 Cookies 刷新成功</lg>')
        else:
            logger.opt(colors=True).error('<lc>Bilibili</lc> | <r>用户 Cookies 刷新失败</r>')
    else:
        logger.opt(colors=True).debug('<lc>Bilibili</lc> | <lg>用户 Cookies 有效, 无需刷新</lg>')


@get_driver().on_startup
async def _load_and_refresh_bilibili_login_status() -> None:
    try:
        await BilibiliCredential.load_cookies_from_db()
        await _refresh_bilibili_login_status()
    except Exception as e:
        logger.opt(colors=True).error(f'<lc>Bilibili</lc> | <r>用户 Cookies 刷新失败</r>, 请尝试重新登录, {e}')


__all__ = [
    'BilibiliCredential',
]
