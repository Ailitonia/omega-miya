"""
@Author         : Ailitonia
@Date           : 2026/9/25 22:38
@FileName       : consts.py
@Project        : omega-miya
@Description    : weibo API 模块常量
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from enum import IntEnum, StrEnum, unique
from typing import Literal

WEIBO_API_SETTING_NAME: Literal['weibo_api_config'] = 'weibo_api_config'
"""存放 weibo API 相关配置的数据库系统配置表固定字段"""
UMD_PUBLIC_KEY_DER: bytes = bytes([
    48, 129, 159, 48, 13, 6, 9, 42, 134, 72, 134, 247, 13, 1, 1, 1, 5, 0, 3, 129, 141, 0, 48, 129, 137, 2, 129, 129, 0,
    180, 249, 101, 74, 227, 247, 222, 230, 24, 220, 10, 149, 183, 131, 164, 185, 20, 166, 164, 114, 158, 71, 46, 151,
    77, 71, 226, 23, 78, 67, 177, 246, 197, 249, 213, 39, 243, 55, 38, 112, 17, 64, 135, 155, 109, 50, 185, 61, 21,
    105, 106, 245, 148, 212, 127, 7, 18, 227, 255, 40, 199, 241, 65, 211, 167, 185, 232, 5, 186, 189, 245, 59, 161,
    214, 48, 160, 251, 21, 92, 187, 172, 83, 152, 11, 85, 72, 37, 137, 87, 104, 63, 39, 86, 6, 150, 84, 6, 178, 229,
    220, 144, 133, 131, 212, 47, 139, 232, 185, 192, 97, 89, 137, 170, 141, 39, 19, 85, 4, 153, 238, 75, 93, 243, 96,
    206, 72, 135, 91, 2, 3, 1, 0, 1
])
"""bd 接口指纹加密 RSA-1024 公钥 (来自 https://passport.sinaimg.cn/js/fp/1.2.1.umd.js 内置公钥, DER 格式)"""
WEIBO_DETECTION_SAMPLE_UID: Literal['1934183965'] = '1934183965'
"""固定探测样本用户(@微博管理员) UID"""


@unique
class VisitorUrl(StrEnum):
    """访客风控流程地址"""
    START_URL = f'https://m.weibo.cn/u/{WEIBO_DETECTION_SAMPLE_UID}'
    """访客风控流程起始页面地址(使用 @微博管理员 主页地址)"""
    VISITOR_ENTER_URL = 'https://visitor.passport.weibo.cn/visitor/visitor'
    """访客系统 enter 接口地址"""
    VISITOR_MINI_JS_URL = 'https://visitor.passport.weibo.cn/js/visitor/mini_original.js?v=20161116'
    """访客系统 mini_original.js 脚本地址(模拟加载)"""
    VISITOR_UMD_JS_URL = 'https://passport.sinaimg.cn/js/fp/1.2.1.umd.js'
    """指纹 umd.js 脚本地址(模拟加载)"""
    BD_PAYLOAD_URL = 'https://passport.weibo.com/sso/bd'
    """bd 指纹校验接口地址"""
    GENVISITOR_URL = 'https://visitor.passport.weibo.cn/visitor/genvisitor2'
    """genvisitor2 访客令牌签发接口地址"""
    VISITOR_CALLBACK_NAME = 'visitor_gray_callback'
    """genvisitor2 接口 JSONP 回调函数名"""


@unique
class LoginUrl(StrEnum):
    """扫码登录流程地址"""
    SSO_SIGNIN_URL = 'https://passport.weibo.com/sso/signin?entry=wapsso&source=wapssowb&url=https://m.weibo.cn/'
    """登录入口地址(获取 X-CSRF-TOKEN)"""
    QRCODE_IMAGE_URL = 'https://passport.weibo.com/sso/v2/qrcode/image'
    """登录二维码申请接口地址"""
    QRCODE_CHECK_URL = 'https://passport.weibo.com/sso/v2/qrcode/check'
    """二维码登录状态轮询接口地址"""


@unique
class LoginStatusCode(IntEnum):
    """passport 接口通用 retcode"""
    RETCODE_SUCCESS = 20000000
    """接口成功状态码"""
    RETCODE_QR_WAIT_SCAN = 50114001
    """二维码未扫码状态码"""
    RETCODE_QR_WAIT_CONFIRM = 50114002
    """二维码已扫码未确认状态码"""
    RETCODE_QR_EXPIRED = 50114003
    """二维码已失效状态码"""


@unique
class RiskFlowStep(IntEnum):
    """访客风控流程内部名称"""
    S1_INIT_PAGE = 1  # 访客流程起始页面
    S2_VISITOR_ENTER = 2  # 访客系统 enter 接口
    S3_PRELOAD_MINI_SCRIPTS = 3  # 模拟加载风控脚本
    S4_PRELOAD_UMD_SCRIPTS = 4  # 模拟加载风控脚本
    S5_GENE_VISITOR_RID = 5  # 构造指纹并请求 bd 接口
    S6_GENVISITOR_TID = 6  # 请求 genvisitor2 接口签发访客 tid


RISK_FLOW_STEP_HEADERS: dict[RiskFlowStep, dict[str, str]] = {
    # 步骤 1/2: GET 起始页面 / POST enter (document navigate)
    RiskFlowStep.S1_INIT_PAGE: {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.7',
        'priority': 'u=0, i',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    },
    RiskFlowStep.S2_VISITOR_ENTER: {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
                  'application/signed-exchange;v=b3;q=0.7',
        'priority': 'u=0, i',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
    },
    # 步骤 3: GET mini_original.js (script, same-origin)
    RiskFlowStep.S3_PRELOAD_MINI_SCRIPTS: {
        'accept': '*/*',
        'priority': 'u=1',
        'sec-fetch-dest': 'script',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'same-origin',
    },
    # 步骤 4: GET 1.2.1.umd.js (script, cross-site)
    RiskFlowStep.S4_PRELOAD_UMD_SCRIPTS: {
        'accept': '*/*',
        'priority': 'u=1',
        'sec-fetch-dest': 'script',
        'sec-fetch-mode': 'no-cors',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-storage-access': 'none',
    },
    # 步骤 5: POST bd (form, cross-site cors)
    RiskFlowStep.S5_GENE_VISITOR_RID: {
        'accept': '*/*',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://visitor.passport.weibo.cn',
        'priority': 'u=1, i',
        'referer': 'https://visitor.passport.weibo.cn/',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-storage-access': 'none',
    },
    # 步骤 6: POST genvisitor2 (form, same-origin cors)
    RiskFlowStep.S6_GENVISITOR_TID: {
        'accept': '*/*',
        'cache-control': 'max-age=0',
        'content-type': 'application/x-www-form-urlencoded',
        'if-modified-since': '0',
        'origin': 'https://visitor.passport.weibo.cn',
        'priority': 'u=1, i',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
    },
}
"""访客风控流程各步骤请求头增量 (基于默认请求头按步骤覆盖, referer 由构建函数注入)"""


__all__ = [
    'RISK_FLOW_STEP_HEADERS',
    'UMD_PUBLIC_KEY_DER',
    'WEIBO_API_SETTING_NAME',
    'WEIBO_DETECTION_SAMPLE_UID',
    'RiskFlowStep',
    'VisitorUrl',
    'LoginStatusCode',
    'LoginUrl',
]
