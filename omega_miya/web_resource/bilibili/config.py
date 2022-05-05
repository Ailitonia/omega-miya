"""
@Author         : Ailitonia
@Date           : 2022/04/11 19:12
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Bilibili Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError

from omega_miya.local_resource import TmpResource
from omega_miya.web_resource import HttpFetcher


class BilibiliConfig(BaseModel):
    """Bilibili 配置"""
    bili_uid: str | None = None
    bili_sessdata: str | None = None
    bili_csrf: str | None = None

    class Config:
        extra = "ignore"

    @property
    def bili_cookie(self) -> dict[str, str] | None:
        return {
            'SESSDATA': self.bili_sessdata,
            'bili_jct': self.bili_csrf
        } if all([self.bili_uid, self.bili_sessdata, self.bili_csrf]) else None

    def clear(self) -> None:
        self.bili_uid = None
        self.bili_sessdata = None
        self.bili_csrf = None


@dataclass
class BilibiliLocalResourceConfig:
    # 默认的缓存资源保存路径
    default_tmp_folder: TmpResource = TmpResource('bilibili')
    default_download_folder: TmpResource = default_tmp_folder('download')


async def verify_bilibili_cookie() -> None:
    """验证 Bilibili cookie 是否有效

    :return: valid, message
    """
    class _VerifyData(BaseModel):
        isLogin: bool
        uname: str | None
        mid: str | None

    class _VerifyResult(BaseModel):
        code: int
        message: str
        data: _VerifyData

    default_headers = HttpFetcher.get_default_headers()
    default_headers.update({'referer': 'https://www.bilibili.com/'})
    fetcher = HttpFetcher(timeout=10, headers=default_headers, cookies=bilibili_config.bili_cookie)
    verify_url = 'https://api.bilibili.com/x/web-interface/nav'
    result = await fetcher.get_json_dict(url=verify_url)
    if result.status != 200:
        bilibili_config.clear()
        logger.opt(colors=True).warning(f'<lc>Bilibili</lc> | <r>Cookie 验证失败</r>, 访问失败, status: {result.status}')

    verify = _VerifyResult.parse_obj(result.result)
    if verify.code != 0 or not verify.data.isLogin:
        bilibili_config.clear()
        logger.opt(colors=True).warning(f'<lc>Bilibili</lc> | <r>Cookie 验证失败</r>, 登录状态异常, {verify.message}')
    elif verify.data.mid != bilibili_config.bili_uid:
        bilibili_config.clear()
        logger.opt(colors=True).warning(f'<lc>Bilibili</lc> | <r>Cookie 验证失败</r>, 登录状态异常, 用户 mid 不匹配')
    else:
        logger.opt(colors=True).success(f'<lc>Bilibili</lc> | <lg>Cookie 已验证</lg>, 登录用户: {verify.data.uname}')


try:
    bilibili_resource_config = BilibiliLocalResourceConfig()
    bilibili_config = BilibiliConfig.parse_obj(get_driver().config)
    if not bilibili_config.bili_cookie:
        bilibili_config.clear()
        logger.opt(colors=True).warning(f'<lc>Bilibili</lc> | <y>未配置 Bilibili Cookie</y>, 已忽略')
    else:
        get_driver().on_startup(verify_bilibili_cookie)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Bilibili 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Bilibili 配置格式验证失败, {e}')


__all__ = [
    'bilibili_config',
    'bilibili_resource_config'
]
