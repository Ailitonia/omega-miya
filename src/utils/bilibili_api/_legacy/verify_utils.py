"""
@Author         : Ailitonia
@Date           : 2023/6/27 22:13
@FileName       : wbi_utils
@Project        : nonebot2_miya
@Description    : Bilibili 接口签名及验证模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import time
import urllib.parse
from functools import reduce
from hashlib import md5
from typing import Any

from .model import BilibiliWebInterfaceNav

__MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def get_mixin_key(orig: str) -> str:
    """对 imgKey 和 subKey 进行字符顺序打乱编码"""
    return reduce(lambda s, i: s + orig[i], __MIXIN_KEY_ENC_TAB, '')[:32]


def enc_wbi(params: dict[str, Any] | None, img_key: str, sub_key: str) -> dict[str, Any]:
    """为请求参数进行 wbi 签名"""
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    params = {} if params is None else params
    # 添加 wts 字段
    params.update({'wts': curr_time})
    # 按照 key 重排参数
    params = dict(sorted(params.items()))
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k: ''.join(filter(lambda x: x not in "!'()*", str(v)))
        for k, v
        in params.items()
    }
    # 序列化参数
    query = urllib.parse.urlencode(params)
    # 计算 w_rid
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()
    params.update({'w_rid': wbi_sign})
    return params


def extract_key_from_wbi_image(url: Any) -> str:
    return str(url).rsplit('/', 1)[-1].split('.')[0]


def sign_wbi_params(nav_data: BilibiliWebInterfaceNav, params: dict[str, Any] | None) -> dict[str, Any]:
    img_key = extract_key_from_wbi_image(url=nav_data.data.wbi_img.img_url)
    sub_key = extract_key_from_wbi_image(url=nav_data.data.wbi_img.sub_url)
    return enc_wbi(params=params, img_key=img_key, sub_key=sub_key)


__all__ = [
    'sign_wbi_params',
]
