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
import time
from base64 import b64encode
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import ujson
from Cryptodome.Cipher import AES, PKCS1_OAEP
from Cryptodome.Hash import SHA256
from Cryptodome.PublicKey import RSA
from Cryptodome.Util.Padding import pad

from src.utils import OmegaRequests
from .consts import (
    LOGIN_FLOW_STEP_HEADERS,
    RISK_FLOW_STEP_HEADERS,
    UMD_PUBLIC_KEY_DER,
    LoginFlowStep,
    RiskFlowStep,
    VisitorUrl,
)
from .model import WeiboVisitorPageParams

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
_FINGERPRINT_ERROR_STACK: str = (
    "TypeError: Cannot read properties of null (reading '0')\n"
    '    at W (https://passport.sinaimg.cn/js/fp/1.2.1.umd.js:1:14066)\n'
    '    at Object.NiOqR (https://passport.sinaimg.cn/js/fp/1.2.1.umd.js:1:3108)\n'
    '    at https://passport.sinaimg.cn/js/fp/1.2.1.umd.js:1:29253\n'
    '    at Array.map (<anonymous>)\n'
    '    at je (https://passport.sinaimg.cn/js/fp/1.2.1.umd.js:1:29193)\n'
    '    at Object.Qhlex (https://passport.sinaimg.cn/js/fp/1.2.1.umd.js:1:5250)\n'
    '    at Ie (https://passport.sinaimg.cn/js/fp/1.2.1.umd.js:1:25296)\n'
    '    at Object.NsuAP (https://passport.sinaimg.cn/js/fp/1.2.1.umd.js:1:4977)\n'
    '    at Pe (https://passport.sinaimg.cn/js/fp/1.2.1.umd.js:1:24928)\n'
    '    at Module.Ve [as get] (https://passport.sinaimg.cn/js/fp/1.2.1.umd.js:1:24667)'
)
"""bd 接口风控校验结构化指纹 4 号采集项 (错误堆栈), 模拟 UMD 脚本在真实浏览器中的采集结果"""


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


def build_login_flow_step_headers(
        step: LoginFlowStep,
        default_headers: 'HeaderTypes',
        *,
        referer: str | None = None,
) -> dict[str, str]:
    """构造扫码登录流程各步骤请求头 (基于默认请求头按步骤覆盖)

    :param step: 流程步骤编号 (LoginFlowStep, 对应 consts.LOGIN_FLOW_STEP_HEADERS)
    :param default_headers: 作为基础的默认请求头
    :param referer: 可选, 覆盖 referer 请求头
    """
    headers: dict[str, str] = dict(default_headers or {})
    headers.update(LOGIN_FLOW_STEP_HEADERS.get(step, {}))
    if referer is not None:
        headers['referer'] = referer
    return headers


def _gen_mouse_track() -> list[list[int]]:
    """生成模拟鼠标轨迹 (贝塞尔曲线)

    对齐 UMD 脚本 getBehaviourData 的输出格式: 首个轨迹点保留绝对坐标与时间戳, 后续点为相对前一点的 [x, y, t] 增量
    """
    now = int(time.time() * 1000)
    start_time = now - 5 * 60 * 1000

    start_x, start_y = random.randint(0, 199), random.randint(0, 199)
    end_x, end_y = 200 + random.randint(0, 799), 100 + random.randint(0, 599)
    control_x = start_x + (end_x - start_x) * 0.3 + random.uniform(-100, 100)
    control_y = start_y + (end_y - start_y) * 0.7 + random.uniform(-100, 100)

    point_count = 30 + random.randint(0, 39)
    time_step = (now - start_time) / point_count

    points: list[list[int]] = []
    current_time = float(start_time)
    for index in range(point_count + 1):
        t = index / point_count
        x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * control_x + t ** 2 * end_x
        y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * control_y + t ** 2 * end_y
        points.append([round(x), round(y), int(current_time)])
        current_time += time_step + random.uniform(-100, 100)

    return [points[0]] + [
        [curr[0] - prev[0], curr[1] - prev[1], curr[2] - prev[2]]
        for prev, curr in pairwise(points)
    ]


def build_fingerprint() -> str:
    """构造 bd 接口风控校验指纹

    结构化指纹, 对齐 https://passport.sinaimg.cn/js/fp/1.2.1.umd.js 采集器输出:
    fp 为 0-23 号采集项, bh 为行为数据 (鼠标轨迹/键盘统计), meta 为行为追踪开关;
    UA 相关采集项取自 OmegaRequests 默认请求头, 保证指纹与实际请求一致
    """
    user_agent = OmegaRequests.get_default_headers().get('user-agent', '')
    return ujson.dumps({
        'fp': {
            '0': '1.2.1',  # 指纹脚本版本
            '1': {'s': 1, 'v': False},  # navigator.webdriver
            '2': {'s': 1, 'v': ['lang']},  # documentElement.getAttributeNames()
            '3': {'s': 1, 'v': user_agent.replace('Mozilla/', '')},  # navigator.appVersion
            '4': {'s': 1, 'v': _FINGERPRINT_ERROR_STACK},  # 错误堆栈采集
            '5': {'s': 1, 'v': 33},  # eval.toString().length
            '6': {'s': 1, 'v': 'function bind() { [native code] }'},  # Function.prototype.bind
            '7': {'s': 1, 'v': [['zh-CN']]},  # navigator.languages
            '8': {'s': 1, 'v': True},  # mimeTypes 原型链检查
            '9': {'s': 1, 'v': False},  # 通知权限状态
            '10': {'s': 1, 'v': True},  # plugins 原型链检查
            '11': {'s': 1, 'v': 5},  # navigator.plugins.length
            '12': {'s': -1, 'e': ''},  # window.process 不存在
            '13': {'s': 1, 'v': '20030107'},  # navigator.productSub
            '14': {'s': 1, 'v': 50},  # navigator.connection.rtt
            '15': {'s': 1, 'v': user_agent},  # navigator.userAgent
            '16': {'s': 1, 'v': {'vendor': 'WebKit', 'renderer': 'WebKit WebGL'}},  # WebGL 信息
            '17': {'s': 1, 'v': '[object External]'},  # window.external
            '18': {'s': 1, 'v': {'ow': 1920, 'oh': 1152, 'iw': 257, 'ih': 1031}},  # 窗口尺寸
            '19': {'s': 1, 'v': 'chrome'},  # 浏览器名称
            '20': {'s': 1, 'v': 'chromium'},  # 浏览器内核
            '21': {'s': 1, 'v': False},  # document.hasFocus()
            '22': {'s': 1, 'v': True},  # window.crypto.subtle 可用
            '23': {'s': 1, 'v': {'ots': False, 'mtp': 0, 'mmtp': -1}},  # 触摸支持
        },
        'bh': {
            'mt': _gen_mouse_track(),
            'kt': {'down': 0, 'up': 0},
        },
        'meta': {'isTraceKeyboard': True, 'isTraceMouse': True},
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
    """生成 enter 接口的 _rand 参数 (10 位数字字符串)"""
    return f'{random.randrange(10 ** 10):010d}'


__all__ = [
    'build_fingerprint',
    'build_login_flow_step_headers',
    'build_risk_flow_step_headers',
    'extract_params_from_html',
    'gen_rand_param',
    'make_bd_payload',
    'merge_cookies',
    'parse_callback_js',
    'parse_loose_json_object',
]
