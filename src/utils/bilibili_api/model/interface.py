"""
@Author         : Ailitonia
@Date           : 2023/6/27 22:23
@FileName       : interface
@Project        : nonebot2_miya
@Description    : Bilibili interface model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import AnyHttpUrl
from typing import Optional

from .base_model import BaseBilibiliModel


class WbiImg(BaseBilibiliModel):
    img_url: AnyHttpUrl
    sub_url: AnyHttpUrl


class BilibiliWebInterfaceNavData(BaseBilibiliModel):
    isLogin: bool
    wbi_img: WbiImg
    uname: Optional[str]
    mid: Optional[str]


class BilibiliWebInterfaceNav(BaseBilibiliModel):
    """api.bilibili.com/x/web-interface/nav 返回值"""
    code: int
    message: str
    data: BilibiliWebInterfaceNavData


__all__ = [
    'BilibiliWebInterfaceNav'
]
