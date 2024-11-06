"""
@Author         : Ailitonia
@Date           : 2024/10/31 16:53:25
@FileName       : wbi.py
@Project        : omega-miya
@Description    : wbi 接口签名及验证
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import time
import urllib.parse
from functools import reduce
from hashlib import md5
from typing import Any, Optional

from ..models import WebInterfaceNav

__MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def get_mixin_key(orig: str) -> str:
    """对 imgKey 和 subKey 进行字符顺序打乱编码"""
    return reduce(lambda s, i: s + orig[i], __MIXIN_KEY_ENC_TAB, '')[:32]


def enc_wbi(params: Optional[dict[str, Any]], img_key: str, sub_key: str) -> dict[str, Any]:
    """为请求参数进行 wbi 签名"""
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    _params: dict[str, Any] = {} if params is None else params
    # 添加 wts 字段
    _params.update({'wts': curr_time})
    # 按照 key 重排参数
    _params = dict(sorted(_params.items()))
    # 过滤 value 中的 "!'()*" 字符
    _params = {
        k: ''.join(filter(lambda x: x not in "!'()*", str(v)))
        for k, v
        in _params.items()
    }
    # 序列化参数
    query = urllib.parse.urlencode(_params)
    # 计算 w_rid
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()
    _params.update({'w_rid': wbi_sign})
    return _params


def extract_key_from_wbi_image(url: Any) -> str:
    """从 img_key 与 sub_key 字段中提取 Token"""
    return str(url).rsplit('/', 1)[-1].split('.')[0]


def sign_wbi_params(params: Optional[dict[str, Any]], img_key: str, sub_key: str) -> dict[str, Any]:
    """使用 img_key 与 sub_key 数据签名请求参数"""
    return enc_wbi(params=params, img_key=img_key, sub_key=sub_key)


def sign_wbi_params_nav(nav_data: WebInterfaceNav, params: Optional[dict[str, Any]]) -> dict[str, Any]:
    """使用 WebInterfaceNav 原始数据签名请求参数"""
    img_key = extract_key_from_wbi_image(url=nav_data.data.wbi_img.img_url)
    sub_key = extract_key_from_wbi_image(url=nav_data.data.wbi_img.sub_url)
    return enc_wbi(params=params, img_key=img_key, sub_key=sub_key)


__all__ = [
    'extract_key_from_wbi_image',
    'sign_wbi_params',
    'sign_wbi_params_nav',
]
