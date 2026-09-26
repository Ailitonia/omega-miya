"""
@Author         : Ailitonia
@Date           : 2026/9/25 22:38
@FileName       : misc.py
@Project        : omega-miya
@Description    : weibo API 杂项工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import os
import random
import re
from base64 import b64encode
from typing import TYPE_CHECKING, Any

import ujson
from Cryptodome.Cipher import AES, PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA
from Cryptodome.Util.Padding import pad
from lxml import etree

from src.compat import parse_json_as
from .consts import RISK_FLOW_STEP_HEADERS, UMD_PUBLIC_KEY_DER, RiskFlowStep, VisitorUrl
from .model import WeiboCardStatus, WeiboVisitorPageParams

if TYPE_CHECKING:
    from src.utils.omega_requests.types import HeaderTypes


_REQUEST_ID_PATTERN = re.compile(r'request_id\s*=\s*["\']([\w\d]+)["\']', re.IGNORECASE)
"""起始页面 request_id 参数提取正则"""
_RETURN_URL_PATTERN = re.compile(r'var\s+return_url\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
"""起始页面 return_url 参数提取正则"""
_VER_PATTERN = re.compile(r'ver=(\d+)', re.IGNORECASE)
"""起始页面 ver 参数提取正则"""
_FROM_PATTERN = re.compile(r'var\s+from\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
"""起始页面 from 参数提取正则"""
_JSON_OBJECT_PATTERN = re.compile(r'\{[\s\S]*}')
"""宽松 JSON 对象提取正则"""


def _search_pattern(pattern: re.Pattern[str], content: str, default: str) -> str:
    """正则提取首个捕获组内容, 未命中时返回默认值"""
    matched = pattern.search(content)
    return matched.group(1) if matched else default


def build_risk_flow_step_headers(
        step: RiskFlowStep,
        default_headers: 'HeaderTypes',
        *,
        referer: str | None = None,
) -> dict[str, str]:
    """构造访客风控流程各步骤请求头 (基于默认请求头按步骤覆盖)

    :param step: 流程步骤编号 (RiskFlowStep, 对应 consts.RISK_FLOW_STEP_HEADERS)
    :param default_headers: 作为基础的默认请求头
    :param referer: 可选, 覆盖 referer 请求头
    """
    headers: dict[str, str] = dict(default_headers or {})
    headers.update(RISK_FLOW_STEP_HEADERS.get(step, {}))
    if referer is not None:
        headers['referer'] = referer
    return headers


def build_fingerprint() -> str:
    """构造访客风控校验指纹"""
    return ujson.dumps({
        'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'platform': 'Win32',
        'screen': '1920x1080x24',
        'fonts': ['Arial', 'SimSun'],
        'plugins': [],
    })


def make_bd_payload(fp: str) -> str:
    """根据 UMD::Aa 逻辑加密指纹并拼装 bd 接口的 payload

    流程: AES-128-CBC(随机 key/iv) 加密指纹 -> RSA-OAEP(SHA-256, 内置公钥) 加密 key+iv ->
    拼装 inner = b'01' + rsa_cipher + b'02' + aes_cipher, 最终 payload = '01' + base64(inner)
    """
    key = os.urandom(16)
    iv = os.urandom(16)

    # AES-CBC 加密指纹
    aes_cipher = AES.new(key, AES.MODE_CBC, iv)
    aes_encrypted = aes_cipher.encrypt(pad(fp.encode('utf-8'), AES.block_size))

    # RSA-OAEP(SHA-256) 加密 key+iv
    public_key = RSA.import_key(UMD_PUBLIC_KEY_DER)
    rsa_cipher = PKCS1_OAEP.new(public_key, SHA256)
    rsa_encrypted = rsa_cipher.encrypt(key + iv)

    inner = b'01' + rsa_encrypted + b'02' + aes_encrypted
    return '01' + b64encode(inner).decode(encoding='ascii')


def extract_params_from_html(html: str) -> WeiboVisitorPageParams:
    """从访客流程起始页面 HTML 中提取风控参数 (未提取到的参数使用默认值回退)"""
    return WeiboVisitorPageParams.model_validate({
        'request_id': _search_pattern(_REQUEST_ID_PATTERN, html, ''),
        'return_url': _search_pattern(_RETURN_URL_PATTERN, html, VisitorUrl.START_URL),
        'ver': _search_pattern(_VER_PATTERN, html, '20250916'),
        'from': _search_pattern(_FROM_PATTERN, html, 'weibo'),
    })


def parse_loose_json_object(text: str) -> dict[str, Any] | None:
    """宽松解析文本中的首个 JSON 对象, 解析失败返回 None"""
    matched = _JSON_OBJECT_PATTERN.search(text)
    if not matched:
        return None
    try:
        parsed = ujson.loads(matched.group(0))
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_callback_js(text: str, cb_name: str = VisitorUrl.VISITOR_CALLBACK_NAME) -> dict[str, Any] | None:
    """解析 JSONP 回调包裹的 JSON 内容, 回调匹配失败时回退为宽松 JSON 对象解析, 均失败返回 None"""
    callback_matched = re.search(re.escape(cb_name) + r'\s*\(\s*([\s\S]*?)\s*\)\s*;?', text)
    if callback_matched:
        try:
            parsed = ujson.loads(callback_matched.group(1))
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass
    return parse_loose_json_object(text)


def merge_cookies(jar: dict[str, str], new_cookies: dict[str, str]) -> dict[str, str]:
    """合并新 cookies 到现有 cookies 字典, 空值与 'deleted' 值视为删除对应 cookie"""
    for name, value in new_cookies.items():
        if not value or value.lower() == 'deleted':
            jar.pop(name, None)
        else:
            jar[name] = value
    return jar


def gen_rand_param() -> str:
    """生成 enter 接口的 _rand 参数 (10 位以内数字字符串)"""
    return str(random.random())[2:12]


def parse_weibo_card_from_status_page(content: str) -> WeiboCardStatus:
    """解析单条微博 Json 数据"""
    html = etree.HTML(content)
    render_data = html.xpath('/html/body/script[2]').pop(0)

    start_mark = 'var $render_data = [{'
    start_index = render_data.text.find(start_mark) + len(start_mark) - 1
    end_mark = '][0] || {};'
    end_index = render_data.text.find(end_mark)
    return parse_json_as(WeiboCardStatus, render_data.text[start_index:end_index])


__all__ = [
    'build_fingerprint',
    'build_risk_flow_step_headers',
    'extract_params_from_html',
    'gen_rand_param',
    'make_bd_payload',
    'merge_cookies',
    'parse_callback_js',
    'parse_loose_json_object',
    'parse_weibo_card_from_status_page',
]
