"""
@Author         : Ailitonia
@Date           : 2024/10/31 16:55:52
@FileName       : sign.py
@Project        : omega-miya
@Description    : sign models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseBilibiliModel


class TicketNav(BaseBilibiliModel):
    img: str
    sub: str


class TicketData(BaseBilibiliModel):
    ticket: str
    created_at: int
    ttl: int
    context: Optional[dict]
    nav: TicketNav


class Ticket(BaseBilibiliModel):
    """api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket 返回值"""
    code: int
    message: str
    ttl: int
    data: TicketData


class WbiImg(BaseBilibiliModel):
    img_url: AnyHttpUrl
    sub_url: AnyHttpUrl


class WebInterfaceNavData(BaseBilibiliModel):
    isLogin: bool
    wbi_img: WbiImg
    uname: Optional[str] = None
    mid: Optional[str] = None


class WebInterfaceNav(BaseBilibiliModel):
    """api.bilibili.com/x/web-interface/nav 返回值"""
    code: int
    message: str
    data: WebInterfaceNavData


class WebInterfaceSpiData(BaseBilibiliModel):
    b_3: str
    b_4: str


class WebInterfaceSpi(BaseBilibiliModel):
    """api.bilibili.com/x/frontend/finger/spi 返回值"""
    code: int
    message: str
    data: WebInterfaceSpiData


class WebCookieInfoData(BaseBilibiliModel):
    """
    - refresh: 是否应该刷新 Cookie, true: 需要刷新 Cookie, false: 无需刷新 Cookie
    - timestamp: 当前毫秒时间戳, 用于获取 refresh_csrf
    """
    refresh: bool
    timestamp: int


class WebCookieInfo(BaseBilibiliModel):
    """passport.bilibili.com/x/passport-login/web/cookie/info 返回值"""
    code: int
    message: str
    ttl: int
    data: WebCookieInfoData


class WebQrcodeGenerateData(BaseBilibiliModel):
    url: str
    qrcode_key: str


class WebQrcodeGenerateInfo(BaseBilibiliModel):
    """passport.bilibili.com/x/passport-login/web/qrcode/generate 返回值"""
    code: int
    message: str
    ttl: int
    data: WebQrcodeGenerateData


class WebQrcodePollData(BaseBilibiliModel):
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


class WebQrcodePollInfo(BaseBilibiliModel):
    """passport.bilibili.com/x/passport-login/web/qrcode/poll 返回值"""
    code: int
    message: str
    ttl: int
    data: WebQrcodePollData


class WebCookieRefreshData(BaseBilibiliModel):
    """
    - refresh_token: 新的持久化刷新口令, 用于更新配置中的 ac_time_value 字段, 以便下次使用
    """
    status: int
    message: str
    refresh_token: str


class WebCookieRefreshInfo(BaseBilibiliModel):
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
    data: WebCookieRefreshData


class WebConfirmRefreshInfo(BaseBilibiliModel):
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
    'Ticket',
    'WebInterfaceNav',
    'WebInterfaceSpi',
    'WebCookieInfo',
    'WebQrcodeGenerateInfo',
    'WebQrcodePollData',
    'WebQrcodePollInfo',
    'WebCookieRefreshInfo',
    'WebConfirmRefreshInfo',
]
