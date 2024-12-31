"""
@Author         : Ailitonia
@Date           : 2023/6/27 22:23
@FileName       : interface
@Project        : nonebot2_miya
@Description    : Bilibili interface model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.compat import AnyHttpUrlStr as AnyHttpUrl

from .base_model import BaseBilibiliModel


class WbiImg(BaseBilibiliModel):
    img_url: AnyHttpUrl
    sub_url: AnyHttpUrl


class BilibiliWebInterfaceNavData(BaseBilibiliModel):
    isLogin: bool
    wbi_img: WbiImg
    uname: str | None = None
    mid: str | None = None


class BilibiliWebInterfaceNav(BaseBilibiliModel):
    """api.bilibili.com/x/web-interface/nav 返回值"""
    code: int
    message: str
    data: BilibiliWebInterfaceNavData


class BilibiliWebInterfaceSpiData(BaseBilibiliModel):
    b_3: str
    b_4: str


class BilibiliWebInterfaceSpi(BaseBilibiliModel):
    """api.bilibili.com/x/frontend/finger/spi 返回值"""
    code: int
    message: str
    data: BilibiliWebInterfaceSpiData


class BilibiliWebCookieInfoData(BaseBilibiliModel):
    """
    - refresh: 是否应该刷新 Cookie, true: 需要刷新 Cookie, false: 无需刷新 Cookie
    - timestamp: 当前毫秒时间戳, 用于获取 refresh_csrf
    """
    refresh: bool
    timestamp: int


class BilibiliWebCookieInfo(BaseBilibiliModel):
    """passport.bilibili.com/x/passport-login/web/cookie/info 返回值"""
    code: int
    message: str
    ttl: int
    data: BilibiliWebCookieInfoData


class BilibiliWebQrcodeGenerateData(BaseBilibiliModel):
    url: str
    qrcode_key: str


class BilibiliWebQrcodeGenerateInfo(BaseBilibiliModel):
    """passport.bilibili.com/x/passport-login/web/qrcode/generate 返回值"""
    code: int
    message: str
    ttl: int
    data: BilibiliWebQrcodeGenerateData


class BilibiliWebQrcodePollData(BaseBilibiliModel):
    """
    code:
    - 86101: 未扫码
    - 86090: 已扫描未确认
    - 86038: 二维码过期
    - 0: 成功
    """
    url: str
    refresh_token: str
    timestamp: int
    code: int
    message: str


class BilibiliWebQrcodePollInfo(BaseBilibiliModel):
    """passport.bilibili.com/x/passport-login/web/qrcode/poll 返回值"""
    code: int
    message: str
    ttl: int
    data: BilibiliWebQrcodePollData


class BilibiliWebCookieRefreshData(BaseBilibiliModel):
    """
    - refresh_token: 新的持久化刷新口令, 用于更新配置中的 ac_time_value 字段, 以便下次使用
    """
    status: int
    message: str
    refresh_token: str


class BilibiliWebCookieRefreshInfo(BaseBilibiliModel):
    """passport.bilibili.com/x/passport-login/web/cookie/refresh 返回值

    code:
    - 0: 成功
    - -101: 账号未登录
    - -111: csrf 校验失败
    - 86095: refresh_csrf 错误或 refresh_token 与 cookie 不匹配
    """
    code: int
    message: str
    ttl: int
    data: BilibiliWebCookieRefreshData


class BilibiliWebConfirmRefreshInfo(BaseBilibiliModel):
    """passport.bilibili.com/x/passport-login/web/confirm/refresh 返回值

    code:
    - 0: 成功
    - -101: 账号未登录
    - -111: csrf 校验失败
    - -400: 请求错误
    """
    code: int
    message: str
    ttl: int


__all__ = [
    'BilibiliWebInterfaceNav',
    'BilibiliWebInterfaceSpi',
    'BilibiliWebCookieInfo',
    'BilibiliWebQrcodeGenerateInfo',
    'BilibiliWebQrcodePollData',
    'BilibiliWebQrcodePollInfo',
    'BilibiliWebCookieRefreshInfo',
    'BilibiliWebConfirmRefreshInfo',
]
