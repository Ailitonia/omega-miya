"""
@Author         : Ailitonia
@Date           : 2026/9/25 22:38
@FileName       : test_007_weibo_api
@Project        : omega-miya
@Description    : weibo api 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
import json
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from tests.test_003_web.helpers import (
    make_response,
    patch_module_asyncio_sleep,
    patch_system_setting_dal,
    require_env_flag,
)

if TYPE_CHECKING:
    from src.utils.weibo_api.credential_manager import _WeiboCredentialManager
    from src.utils.weibo_api.model import WeiboQrCodeCheck

requires_live = require_env_flag('WEIBO_API_REAL_TEST')
"""真实请求验证类门禁: 日常运行 (含全量套件) 一律跳过, 由用户手动设置环境变量后发起"""

require_force_refresh_test = require_env_flag(
    'WEIBO_API_FORCE_REFRESH_TEST',
    reason='会重建数据库 cookies 覆盖登录态, 需手动设置 WEIBO_API_FORCE_REFRESH_TEST=1 环境变量后运行',
)
"""访客流程强制刷新验证门禁: 常规真实请求验证 (WEIBO_API_REAL_TEST=1) 不执行"""

# ------------------------------------------------------------------ #
# 接口模拟响应
# ------------------------------------------------------------------ #

_VISITOR_HTML = (
    '<html><head></head><body><script>'
    'var request_id = "req_id_value";'
    'var return_url = "https://m.weibo.cn/u/7643376782";'
    'var from = "weibo";'
    'location.replace("https://visitor.passport.weibo.cn/visitor/visitor?ver=20260925&a=enter");'
    '</script></body></html>'
)
"""含风控参数的模拟起始页面 HTML"""

_GENVISITOR_JSONP = (
    'visitor_gray_callback({"retcode":20000000,"msg":"succ",'
    '"data":{"tid":"tid_value","new_tid":true,"confidence":95,"scene":"gray"}});'
)
"""genvisitor2 接口模拟 JSONP 成功响应"""

_BD_PAYLOAD = {'retcode': 20000000, 'msg': 'ok', 'data': {'rid': 'rid_value'}}
"""bd 接口模拟成功响应"""

_BD_ERROR_JSON = '{"retcode": 50000000, "msg": "error"}'
"""bd 接口模拟错误响应 (JSON 文本)"""

_QRCODE_IMAGE_PAYLOAD = {
    'retcode': 20000000, 'msg': 'ok',
    'data': {'qrid': 'qrid_value', 'image': 'https://passport.weibo.com/sso/v2/qrcode/qr.png'},
}
"""qrcode/image 接口模拟响应"""

_QRCODE_CHECK_SUCCESS_PAYLOAD = {
    'retcode': 20000000, 'msg': 'ok',
    'data': {'url': 'https://passport.weibo.com/wbsso/login?ticket=ST-xxx'},
}
"""qrcode/check 接口模拟登录成功响应"""

_QRCODE_CHECK_PENDING_PAYLOAD = {'retcode': 50114001, 'msg': '未扫码'}
"""qrcode/check 接口模拟待扫码响应"""

_QRCODE_CHECK_CONFIRM_PAYLOAD = {'retcode': 50114002, 'msg': '已扫码未确认'}
"""qrcode/check 接口模拟已扫码未确认响应"""

_QRCODE_CHECK_EXPIRED_PAYLOAD = {'retcode': 50114003, 'msg': '二维码已失效'}
"""qrcode/check 接口模拟二维码过期响应"""


# ------------------------------------------------------------------ #
# 测试基建
# ------------------------------------------------------------------ #


@pytest.fixture
def credential_manager_sandbox() -> '_WeiboCredentialManager':
    """全局凭据管理器状态沙箱: 测试前快照, 测试结束后恢复"""
    from src.utils.weibo_api.credential_manager import WEIBO_CREDENTIAL_MANAGER, WeiboCookiesData

    snapshot = WeiboCookiesData.model_validate(WEIBO_CREDENTIAL_MANAGER.cookies)
    yield WEIBO_CREDENTIAL_MANAGER
    WEIBO_CREDENTIAL_MANAGER._cookies_data = snapshot


@pytest.fixture
def clean_manager(credential_manager_sandbox: '_WeiboCredentialManager') -> '_WeiboCredentialManager':
    """全局凭据管理器状态沙箱 (已预清空 cookies)"""
    credential_manager_sandbox.clear_cookies()
    return credential_manager_sandbox


def _make_qrcode_info():
    """构造登录二维码信息"""
    from src.utils.weibo_api.model import WeiboLoginQrCodeInfo

    return WeiboLoginQrCodeInfo.model_validate({
        'qrid': 'qrid_value',
        'image_url': 'https://passport.weibo.com/sso/v2/qrcode/qr.png',
        'rid': 'rid_value',
        'csrf_token': 'csrf_value',
    })


def _make_check_result(payload: dict) -> 'WeiboQrCodeCheck':
    from src.utils.weibo_api.model import WeiboQrCodeCheck

    return WeiboQrCodeCheck.model_validate(payload)


def _make_user_data() -> dict:
    """构造最小有效微博用户数据"""
    return {
        'id': 1934183965, 'screen_name': '微博管理员',
        'profile_image_url': 'https://tvax1.sinaimg.cn/a.jpg', 'profile_url': 'https://m.weibo.cn/u/1934183965',
        'statuses_count': 100, 'verified': True, 'verified_type': 0, 'close_blue_v': False,
        'description': 'desc', 'gender': 'f', 'mbtype': 2, 'svip': 7, 'urank': 48, 'mbrank': 7,
        'follow_me': False, 'following': False, 'follow_count': 1,
        'followers_count': '1000', 'followers_count_str': '1000',
        'cover_image_phone': 'https://wx1.sinaimg.cn/cover.jpg', 'avatar_hd': 'https://wx1.sinaimg.cn/avatar.jpg',
        'like': False, 'like_me': False,
    }


def _make_mblog_data() -> dict:
    """构造最小有效单条微博 mblog 数据"""
    return {
        'visible': {'type': 0, 'list_id': 0}, 'created_at': 'Thu Sep 25 12:00:00 +0800 2025',
        'id': 5212345678901234, 'mid': '5212345678901234', 'can_edit': False,
        'text': 'test <b>content</b>', 'source': '微博网页版', 'favorited': False, 'pic_ids': [],
        'is_paid': False, 'mblog_vip_type': 0, 'user': _make_user_data(),
        'reposts_count': 1, 'comments_count': 2, 'reprint_cmt_count': 0, 'attitudes_count': 3,
        'pending_approval_count': 0, 'isLongText': False, 'mlevel': 0, 'show_mlevel': 0,
        'pic_num': 0, 'bid': 'QaBcDeFgH',
    }


def _make_user_info_response() -> dict:
    """构造最小有效用户信息接口响应"""
    return {
        'ok': 1,
        'data': {
            'fans_scheme': 'https://m.weibo.cn/p/index?containerid=231032',
            'follow_scheme': 'https://m.weibo.cn/p/index?containerid=231093',
            'isStarStyle': 0,
            'profile_ext': '',
            'scheme': 'https://m.weibo.cn/u/1934183965',
            'showAppTips': 0,
            'userInfo': _make_user_data(),
        },
    }


def _make_cards_response(cards: list | None = None) -> dict:
    """构造最小有效用户微博列表接口响应"""
    if cards is None:
        cards = [{'card_type': 9, 'mblog': _make_mblog_data()}]
    return {
        'ok': 1,
        'data': {
            'cardlistInfo': {
                'containerid': '1076031934183965', 'v_p': 42, 'show_style': 1,
                'total': 100, 'autoLoadMoreIndex': 0, 'since_id': 0,
            },
            'cards': cards,
            'scheme': 'https://m.weibo.cn/u/1934183965',
            'showAppTips': 0,
        },
    }


def _make_realtime_hot_response() -> dict:
    """构造最小有效实时热搜接口响应"""
    return {
        'ok': 1,
        'data': {
            'cardlistInfo': {
                'starttime': 1700000000, 'can_shared': 1, 'config': {}, 'page_type': '01',
                'cardlist_head_cards': [], 'nick': '热搜', 'page_title': '微博热搜',
                'search_request_id': 'req_id_value', 'v_p': '42', 'containerid': '106003type=25',
                'refresh_configs': {}, 'total': 50, 'page_size': 10, 'select_id': '001',
                'title_top': '热搜榜', 'show_style': 1,
            },
            'cards': [{
                'itemid': 'hot_group',
                'show_type': 0,
                'card_type': 4,
                'card_group': [{'card_type': 4, 'scheme': 'https://m.weibo.cn/search?word=x', 'desc': '热搜词'}],
            }],
        },
    }


def _make_top_feed_response() -> dict:
    """构造最小有效首页 feed 接口响应"""
    return {
        'ok': 1,
        'data': {
            'statuses': [_make_mblog_data()],
            'hasvisible': False,
            'previous_cursor': 0,
            'next_cursor': 0,
            'previous_cursor_str': '0',
            'next_cursor_str': '0',
            'total_number': 1,
            'interval': 0,
            'since_id': 0,
            'since_id_str': '0',
            'max_id': 0,
            'max_id_str': '0',
            'has_unread': 0,
        },
    }


def _patch_post(monkeypatch: pytest.MonkeyPatch, content: str = '', *, headers: list | None = None) -> AsyncMock:
    """mock credential 请求层 _request_post, 返回携带给定文本内容与响应头的固定响应"""
    from src.utils.weibo_api.credential import WeiboCredential

    post_mock = AsyncMock(return_value=make_response(headers=headers, content=content))
    monkeypatch.setattr(WeiboCredential, '_request_post', post_mock)
    return post_mock


def _patch_query_layer(monkeypatch: pytest.MonkeyPatch, response) -> tuple[AsyncMock, AsyncMock]:
    """mock 查询方法请求层: 跳过凭据确保流程并以给定响应替换 _get_api_json

    :return: (ensure_cookies mock, _get_api_json mock)
    """
    from src.utils.weibo_api import Weibo, WeiboCredential

    ensure_mock = AsyncMock()
    monkeypatch.setattr(WeiboCredential, 'ensure_cookies', ensure_mock)
    get_json_mock = AsyncMock(return_value=response)
    monkeypatch.setattr(Weibo, '_get_api_json', get_json_mock)
    return ensure_mock, get_json_mock


# ------------------------------------------------------------------ #
# misc 纯函数测试
# ------------------------------------------------------------------ #


class TestConsts:
    """模块常量与枚举测试"""

    def test_start_url_derived_from_sample_uid(self) -> None:
        """访客流程起始页面地址由固定探测样本用户 uid 派生"""
        from src.utils.weibo_api.consts import WEIBO_DETECTION_SAMPLE_UID, VisitorUrl

        assert isinstance(VisitorUrl.START_URL, str)
        assert VisitorUrl.START_URL == f'https://m.weibo.cn/u/{WEIBO_DETECTION_SAMPLE_UID}'

    def test_step_headers_covers_all_steps(self) -> None:
        from src.utils.weibo_api.consts import RISK_FLOW_STEP_HEADERS, RiskFlowStep

        assert set(RISK_FLOW_STEP_HEADERS.keys()) == set(RiskFlowStep)

    def test_login_step_headers_covers_all_steps(self) -> None:
        from src.utils.weibo_api.consts import LOGIN_FLOW_STEP_HEADERS, LoginFlowStep

        assert set(LOGIN_FLOW_STEP_HEADERS.keys()) == set(LoginFlowStep)

    def test_login_flow_constants(self) -> None:
        """登录流程常量挂载于 LoginUrl 且值符合预期"""
        from src.utils.weibo_api.consts import LoginUrl

        assert LoginUrl.LOGIN_QRCODE_CHECK_VER == '20250520'
        assert LoginUrl.LOGIN_SIGNIN_REFERER.startswith('https://passport.weibo.com/sso/signin?')
        assert 'source=wapsso&' in LoginUrl.LOGIN_SIGNIN_REFERER
        assert 'source=wapssowb' in LoginUrl.LOGIN_SIGNIN_WB_REFERER
        assert 'jumpfrom%3Dweibocom' in LoginUrl.LOGIN_CHAIN_REFERER


class TestBuildLoginFlowStepHeaders:
    """扫码登录流程各步骤请求头构建测试"""

    def test_step2_qrcode_image(self) -> None:
        from src.utils.weibo_api.consts import LoginFlowStep, LoginUrl
        from src.utils.weibo_api.misc import build_login_flow_step_headers

        headers = build_login_flow_step_headers(LoginFlowStep.S2_QRCODE_IMAGE, {'user-agent': 'test_ua'})

        assert headers['user-agent'] == 'test_ua'
        assert headers['accept'] == 'application/json, text/plain, */*'
        assert headers['x-requested-with'] == 'XMLHttpRequest'
        assert headers['referer'] == LoginUrl.LOGIN_SIGNIN_WB_REFERER

    def test_step3_bd_form(self) -> None:
        from src.utils.weibo_api.consts import LoginFlowStep, LoginUrl
        from src.utils.weibo_api.misc import build_login_flow_step_headers

        headers = build_login_flow_step_headers(LoginFlowStep.S3_FETCH_LOGIN_RID, {})

        assert headers['content-type'] == 'application/x-www-form-urlencoded'
        assert headers['origin'] == 'https://passport.weibo.com'
        assert headers['referer'] == LoginUrl.LOGIN_SIGNIN_REFERER

    def test_step5_cookie_chain_referer(self) -> None:
        """重定向链请求头 Referer 带 jumpfrom=weibocom"""
        from src.utils.weibo_api.consts import LoginFlowStep, LoginUrl
        from src.utils.weibo_api.misc import build_login_flow_step_headers

        headers = build_login_flow_step_headers(LoginFlowStep.S5_COOKIE_CHAIN, {})

        assert headers['referer'] == LoginUrl.LOGIN_CHAIN_REFERER
        assert 'jumpfrom%3Dweibocom' in headers['referer']
        assert headers['sec-fetch-mode'] == 'navigate'

    def test_referer_override(self) -> None:
        """传入 referer 时覆盖步骤默认 referer"""
        from src.utils.weibo_api.consts import LoginFlowStep
        from src.utils.weibo_api.misc import build_login_flow_step_headers

        headers = build_login_flow_step_headers(
            LoginFlowStep.S4_QRCODE_CHECK, {}, referer='https://example.com/'
        )

        assert headers['referer'] == 'https://example.com/'


class TestBuildRiskFlowStepHeaders:
    """风控流程各步骤请求头构建测试"""

    def test_step1_document_navigate(self) -> None:
        from src.utils.weibo_api.consts import RiskFlowStep
        from src.utils.weibo_api.misc import build_risk_flow_step_headers

        headers = build_risk_flow_step_headers(
            RiskFlowStep.S1_INIT_PAGE, {'user-agent': 'test_ua', 'accept': '*/*'}
        )

        assert headers['user-agent'] == 'test_ua'
        assert headers['accept'].startswith('text/html')
        assert headers['sec-fetch-dest'] == 'document'
        assert headers['sec-fetch-mode'] == 'navigate'
        assert headers['sec-fetch-site'] == 'none'

    def test_step5_bd_form(self) -> None:
        from src.utils.weibo_api.consts import RiskFlowStep
        from src.utils.weibo_api.misc import build_risk_flow_step_headers

        headers = build_risk_flow_step_headers(RiskFlowStep.S5_GENE_VISITOR_RID, {})

        assert headers['content-type'] == 'application/x-www-form-urlencoded'
        assert headers['origin'] == 'https://visitor.passport.weibo.cn'
        assert headers['sec-fetch-site'] == 'cross-site'

    def test_referer_injection(self) -> None:
        from src.utils.weibo_api.consts import RiskFlowStep
        from src.utils.weibo_api.misc import build_risk_flow_step_headers

        headers = build_risk_flow_step_headers(
            RiskFlowStep.S3_PRELOAD_MINI_SCRIPTS, {}, referer='https://example.com/'
        )

        assert headers['referer'] == 'https://example.com/'
        assert headers['sec-fetch-site'] == 'same-origin'

    def test_none_default_headers(self) -> None:
        """default_headers 为 None 时仅使用步骤增量请求头"""
        from src.utils.weibo_api.consts import RiskFlowStep
        from src.utils.weibo_api.misc import build_risk_flow_step_headers

        headers = build_risk_flow_step_headers(RiskFlowStep.S6_GENVISITOR_TID, None)

        assert headers['content-type'] == 'application/x-www-form-urlencoded'
        assert 'user-agent' not in headers

    def test_unknown_step_fallback(self) -> None:
        """未知步骤不注入增量, 仅返回默认请求头"""
        from src.utils.weibo_api.misc import build_risk_flow_step_headers

        headers = build_risk_flow_step_headers(99, {'user-agent': 'test_ua'})

        assert headers == {'user-agent': 'test_ua'}


class TestBuildFingerprint:
    """指纹构造测试 (结构化指纹, 对齐 1.2.1.umd.js 采集器输出)"""

    def test_fingerprint_structure(self) -> None:
        from src.utils.omega_requests import OmegaRequests
        from src.utils.weibo_api.misc import build_fingerprint

        fingerprint = json.loads(build_fingerprint())

        # 顶层结构: fp(采集项) / bh(行为数据) / meta(追踪开关)
        assert set(fingerprint.keys()) == {'fp', 'bh', 'meta'}
        assert fingerprint['meta'] == {'isTraceKeyboard': True, 'isTraceMouse': True}
        assert fingerprint['bh']['kt'] == {'down': 0, 'up': 0}

        # fp 采集项 0-23 齐全
        fp = fingerprint['fp']
        assert set(fp.keys()) == {str(i) for i in range(24)}
        assert fp['0'] == '1.2.1'
        assert fp['6']['v'] == 'function bind() { [native code] }'
        assert fp['13']['v'] == '20030107'

        # UA 相关采集项与默认请求头 UA 一致
        user_agent = OmegaRequests.get_default_headers()['user-agent']
        assert fp['15']['v'] == user_agent
        assert fp['3']['v'] == user_agent.replace('Mozilla/', '')

    def test_fingerprint_mouse_track_delta_format(self) -> None:
        """鼠标轨迹首个点为绝对值, 后续点为相对前一点的 [x, y, t] 增量"""
        from src.utils.weibo_api.misc import build_fingerprint

        track = json.loads(build_fingerprint())['bh']['mt']

        assert len(track) >= 30
        assert all(len(point) == 3 for point in track)
        assert all(isinstance(value, int) for value in track[0])
        # 增量点 x/y 为相对偏移 (量级远小于绝对坐标), t 为正向时间差
        for x_delta, y_delta, t_delta in track[1:]:
            assert abs(x_delta) < 1000
            assert abs(y_delta) < 1000
            assert t_delta > 0


class TestMakeBdPayload:
    """bd 加密载荷测试 (随机 key/iv, 仅校验结构不变量)"""

    def test_payload_structure(self) -> None:
        from src.utils.weibo_api.misc import make_bd_payload

        payload = make_bd_payload('{"ua":"test"}')

        assert payload.startswith('01')
        inner = base64.b64decode(payload[2:])
        assert inner[:2] == b'01'
        # RSA-1024 加密输出 128 字节
        assert len(inner[2:130]) == 128
        assert inner[130:132] == b'02'
        # AES-CBC 输出为 16 字节整数倍
        aes_part = inner[132:]
        assert len(aes_part) > 0
        assert len(aes_part) % 16 == 0

    def test_payload_not_deterministic(self) -> None:
        """随机 key/iv, 相同输入产出不同载荷"""
        from src.utils.weibo_api.misc import make_bd_payload

        assert make_bd_payload('{"ua":"test"}') != make_bd_payload('{"ua":"test"}')

    def test_umd_public_key_der_importable(self) -> None:
        """内置公钥 DER 应可导入为 1024 位 RSA 公钥"""
        from Cryptodome.PublicKey import RSA

        from src.utils.weibo_api.consts import UMD_PUBLIC_KEY_DER

        key = RSA.import_key(UMD_PUBLIC_KEY_DER)

        assert key.size_in_bits() == 1024
        assert not key.has_private()


class TestExtractParamsFromHtml:
    """起始页面风控参数提取测试"""

    def test_extract_all_params(self) -> None:
        from src.utils.weibo_api.misc import extract_params_from_html

        params = extract_params_from_html(_VISITOR_HTML)

        assert params.request_id == 'req_id_value'
        assert params.return_url == 'https://m.weibo.cn/u/7643376782'
        assert params.ver == '20260925'
        assert params.from_ == 'weibo'

    def test_extract_fallback_defaults(self) -> None:
        """未命中参数时使用默认值回退"""
        from src.utils.weibo_api.consts import VisitorUrl
        from src.utils.weibo_api.misc import extract_params_from_html

        params = extract_params_from_html('<html><body>nothing here</body></html>')

        assert params.request_id == ''
        assert params.return_url == VisitorUrl.START_URL
        assert params.ver == '20250916'
        assert params.from_ == 'weibo'


class TestParseCallbackJs:
    """JSONP 回调解析测试"""

    def test_parse_standard_jsonp(self) -> None:
        from src.utils.weibo_api.misc import parse_callback_js

        parsed = parse_callback_js(_GENVISITOR_JSONP)

        assert parsed is not None
        assert parsed['retcode'] == 20000000
        assert parsed['data']['tid'] == 'tid_value'

    def test_parse_fallback_to_loose_json(self) -> None:
        """回调名不匹配时回退为宽松 JSON 对象提取"""
        from src.utils.weibo_api.misc import parse_callback_js

        parsed = parse_callback_js('other_callback({"retcode": 1});', cb_name='visitor_gray_callback')

        assert parsed == {'retcode': 1}

    def test_parse_garbage_returns_none(self) -> None:
        from src.utils.weibo_api.misc import parse_callback_js

        assert parse_callback_js('not a jsonp at all') is None

    def test_parse_non_dict_returns_none(self) -> None:
        from src.utils.weibo_api.misc import parse_callback_js

        assert parse_callback_js('visitor_gray_callback([1, 2, 3]);') is None


class TestParseLooseJsonObject:
    """宽松 JSON 对象解析测试"""

    def test_parse_json_with_prefix(self) -> None:
        from src.utils.weibo_api.misc import parse_loose_json_object

        assert parse_loose_json_object('garbage prefix {"retcode": 0} suffix') == {'retcode': 0}

    def test_parse_non_dict_returns_none(self) -> None:
        from src.utils.weibo_api.misc import parse_loose_json_object

        assert parse_loose_json_object('[1, 2]') is None
        assert parse_loose_json_object('nothing') is None


class TestMergeCookies:
    """Cookies 合并测试"""

    def test_merge_and_overwrite(self) -> None:
        from src.utils.weibo_api.misc import merge_cookies

        jar = {'SUB': 'old_sub', 'tid': 'tid_value'}

        merge_cookies(jar, {'SUB': 'new_sub', 'SUBP': 'subp_value'})

        assert jar == {'SUB': 'new_sub', 'SUBP': 'subp_value', 'tid': 'tid_value'}

    def test_deleted_value_removes_key(self) -> None:
        from src.utils.weibo_api.misc import merge_cookies

        jar = {'SUB': 'sub_value', 'tid': 'tid_value'}

        merge_cookies(jar, {'SUB': 'deleted', 'tid': ''})

        assert jar == {}

    def test_merge_empty_keeps_jar(self) -> None:
        from src.utils.weibo_api.misc import merge_cookies

        jar = {'SUB': 'sub_value'}

        merge_cookies(jar, {})

        assert jar == {'SUB': 'sub_value'}


class TestGenRandParam:
    """enter 接口 _rand 参数生成测试"""

    def test_fixed_length_digits(self) -> None:
        """返回值应为 10 位纯数字字符串 (不得落入科学计数法)"""
        from src.utils.weibo_api.misc import gen_rand_param

        samples = [gen_rand_param() for _ in range(100)]

        assert all(len(sample) == 10 and sample.isdigit() for sample in samples)
        assert len(set(samples)) > 1


class TestWeiboMbLog:
    """单条微博 mblog 模型测试"""

    def test_parse_success(self) -> None:
        from src.utils.weibo_api.model import WeiboMbLog

        mblog = WeiboMbLog.model_validate(_make_mblog_data())

        assert mblog.id == 5212345678901234
        assert mblog.mid == '5212345678901234'
        # text 字段的 HTML 标签应被剥除
        assert mblog.text == 'test content'
        assert mblog.user.screen_name == '微博管理员'
        assert mblog.is_retweeted is False
        assert mblog.format_created_at == '09-25 12:00'

    @pytest.mark.parametrize('retweeted_status', [{'id': 1}, None, 'deleted'], ids=['missing_user', 'none', 'non_dict'])
    def test_invalid_retweeted_status_filtered(self, retweeted_status: dict | None | str) -> None:
        """retweeted_status 缺 user / 为 None / 非 dict 时均按非转发处理, 不得抛出 AttributeError"""
        from src.utils.weibo_api.model import WeiboMbLog

        mblog = WeiboMbLog.model_validate(_make_mblog_data() | {'retweeted_status': retweeted_status})

        assert mblog.is_retweeted is False

    @pytest.mark.parametrize('text', ['', '<br/>'], ids=['empty', 'html_tags_only'])
    def test_blank_text_stripped(self, text: str) -> None:
        """空 text 直接返回, 纯标签 text 剥除后为空串"""
        from src.utils.weibo_api.model import WeiboMbLog

        mblog = WeiboMbLog.model_validate(_make_mblog_data() | {'text': text})

        assert mblog.text == ''


class TestWeiboExtendModel:
    """微博展开全文模型边界测试"""

    def test_empty_long_text_content(self) -> None:
        """空 longTextContent 不触发 lxml 空文档异常"""
        from src.utils.weibo_api.model import WeiboExtend

        extend = WeiboExtend.model_validate({
            'ok': 1,
            'data': {'ok': 1, 'longTextContent': '', 'reposts_count': 0, 'comments_count': 0, 'attitudes_count': 0},
        })

        assert extend.data is not None
        assert extend.data.longTextContent == ''

    def test_missing_data_allowed(self) -> None:
        """错误响应缺 data 时模型可校验, 由业务层统一判断 ok"""
        from src.utils.weibo_api.model import WeiboExtend

        extend = WeiboExtend.model_validate({'ok': -100})

        assert extend.ok == -100
        assert extend.data is None


# ------------------------------------------------------------------ #
# 凭据管理器与 Cookies 模型测试
# ------------------------------------------------------------------ #


class TestCookiesData:
    """Cookies 数据模型边界测试"""

    def test_as_dict_filters_none(self) -> None:
        from src.utils.weibo_api.credential_manager import WeiboCookiesData

        data = WeiboCookiesData.model_validate({'SUB': 'sub_value'})

        assert data.as_dict == {'SUB': 'sub_value'}

    def test_iter_items_contains_none(self) -> None:
        """iter_items 覆盖全部字段 (含 None 值), 用于持久化时识别缺失键"""
        from src.utils.weibo_api.credential_manager import WeiboCookiesData

        items = dict(WeiboCookiesData().iter_items)

        assert 'SUB' in items
        assert items['SUB'] is None
        assert 'tid' in items
        assert 'XSRF-TOKEN' in items

    def test_number_coerced_to_str(self) -> None:
        """coerce_numbers_to_str: 数字 cookie 值被强转为字符串"""
        from src.utils.weibo_api.credential_manager import WeiboCookiesData

        data = WeiboCookiesData.model_validate({'un': 12345})

        assert data.as_dict['un'] == '12345'

    def test_unknown_key_ignored(self) -> None:
        from src.utils.weibo_api.credential_manager import WeiboCookiesData

        data = WeiboCookiesData.model_validate({'SUB': 'sub_value', 'unknown_cookie': 'x'})

        assert 'unknown_cookie' not in data.as_dict


class TestCredentialManagerOps:
    """凭据管理器内存操作语义测试"""

    def test_update_cookies_merges(self, clean_manager: '_WeiboCredentialManager') -> None:
        """update_cookies 覆盖同名键, 保留未提供的既有键"""
        clean_manager.update_cookies(SUB='sub_value', tid='tid_value')

        clean_manager.update_cookies(SUB='new_sub')

        assert clean_manager.get_cookie('SUB') == 'new_sub'
        assert clean_manager.get_cookie('tid') == 'tid_value'

    def test_update_cookies_ignores_unknown_keys(self, clean_manager: '_WeiboCredentialManager') -> None:
        clean_manager.update_cookies(SUB='sub_value', unknown_cookie='x')

        assert 'unknown_cookie' not in clean_manager.cookies

    def test_replace_cookies(self, clean_manager: '_WeiboCredentialManager') -> None:
        """replace_cookies 一次性全量替换, 未包含的既有键被丢弃"""
        from src.utils.weibo_api.credential_manager import WeiboCookiesData

        clean_manager.update_cookies(SUB='old_sub', tid='old_tid')

        clean_manager.replace_cookies(WeiboCookiesData.model_validate({'SUB': 'new_sub'}))

        assert clean_manager.cookies == {'SUB': 'new_sub'}

    def test_clear_cookies(self, clean_manager: '_WeiboCredentialManager') -> None:
        clean_manager.update_cookies(SUB='sub_value')

        clean_manager.clear_cookies()

        assert clean_manager.cookies == {}

    def test_get_cookie_by_field_name(self, clean_manager: '_WeiboCredentialManager') -> None:
        clean_manager.update_cookies(SUB='sub_value')

        assert clean_manager.get_cookie('weibo_api_sub', alias=False) == clean_manager.get_cookie('SUB')


class TestCredentialManagerPersistence:
    """凭据落库测试 (刷新/登录后应重建数据库系列, 清除陈旧键)"""

    async def test_rebuild_removes_stale_keys(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        clean_manager.update_cookies(SUB='sub_value')

        fake_dal = patch_system_setting_dal(monkeypatch, series=[
            SimpleNamespace(setting_name='weibo_api_config', setting_key='SUB'),
            SimpleNamespace(setting_name='weibo_api_config', setting_key='STALE_KEY'),
        ])

        await clean_manager.rebuild_to_database()

        assert set(fake_dal.deleted) == {'SUB', 'STALE_KEY'}
        assert fake_dal.saved == {'SUB': 'sub_value'}

    async def test_save_skips_none_values(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """save_to_database 仅写入非 None 值且不删除既有键"""
        clean_manager.update_cookies(SUB='sub_value')

        fake_dal = patch_system_setting_dal(monkeypatch)

        await clean_manager.save_to_database()

        assert fake_dal.saved == {'SUB': 'sub_value'}
        assert not fake_dal.deleted

    async def test_load_from_database(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """load_from_database 先清空再加载: 命中键写入, 未命中键置 None"""
        clean_manager.update_cookies(SUB='stale_sub', tid='stale_tid')

        patch_system_setting_dal(monkeypatch, unique={'SUB': 'db_sub'})

        await clean_manager.load_from_database()

        assert clean_manager.get_cookie('SUB') == 'db_sub'
        assert clean_manager.get_cookie('tid') is None


# ------------------------------------------------------------------ #
# 访客风控流程测试
# ------------------------------------------------------------------ #


class TestVisitorFlowSteps:
    """访客风控流程各步骤测试"""

    async def test_fetch_initial_page(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """起始页面解析风控参数并合并响应 Cookies"""
        from src.utils.weibo_api.consts import VisitorUrl
        from src.utils.weibo_api.credential import WeiboCredential

        response = make_response(
            headers=[('set-cookie', '_T_WM=twm_value; path=/')],
            content=_VISITOR_HTML,
        )
        get_mock = AsyncMock(return_value=response)
        monkeypatch.setattr(WeiboCredential, '_request_get', get_mock)

        cookies: dict[str, str] = {}
        params = await WeiboCredential._fetch_initial_page(cookies=cookies)

        assert get_mock.call_args.kwargs['url'] == VisitorUrl.START_URL
        assert params.request_id == 'req_id_value'
        assert params.ver == '20260925'
        assert cookies == {'_T_WM': 'twm_value'}

    async def test_post_visitor_enter(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """enter 接口表单参数与 Cookies 合并"""
        from src.utils.weibo_api.consts import VisitorUrl
        from src.utils.weibo_api.credential import WeiboCredential

        post_mock = _patch_post(monkeypatch, headers=[('set-cookie', 'SUB=sub_value; path=/')])

        cookies: dict[str, str] = {}
        rand = await WeiboCredential._post_visitor_enter(cookies=cookies)

        call_kwargs = post_mock.call_args.kwargs
        assert call_kwargs['url'] == VisitorUrl.VISITOR_ENTER_URL
        assert call_kwargs['data']['entry'] == 'sinawap'
        assert call_kwargs['data']['a'] == 'enter'
        assert call_kwargs['data']['url'] == VisitorUrl.START_URL
        assert call_kwargs['data']['domain'] == '.weibo.cn'
        assert call_kwargs['data']['ua'] == 'php-sso_sdk_client-0.6.36'
        assert call_kwargs['data']['_rand'] == rand
        assert cookies == {'SUB': 'sub_value'}

    async def test_preload_risk_scripts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """风控脚本按顺序模拟加载并携带 referer"""
        from src.utils.weibo_api.consts import VisitorUrl
        from src.utils.weibo_api.credential import WeiboCredential

        get_mock = AsyncMock(return_value=make_response())
        monkeypatch.setattr(WeiboCredential, '_request_get', get_mock)

        await WeiboCredential._preload_risk_scripts(rand='1234567890', cookies={})

        requested_urls = [call.kwargs['url'] for call in get_mock.call_args_list]
        assert requested_urls == [VisitorUrl.VISITOR_MINI_JS_URL, VisitorUrl.VISITOR_UMD_JS_URL]
        mini_headers = get_mock.call_args_list[0].kwargs['headers']
        assert mini_headers['referer'] == f'{VisitorUrl.VISITOR_ENTER_URL}?_rand=1234567890'

    async def test_fetch_visitor_rid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """bd 接口以 android-visitor 身份获取 rid"""
        from src.utils.weibo_api.consts import VisitorUrl
        from src.utils.weibo_api.credential import WeiboCredential

        post_mock = _patch_post(monkeypatch, json.dumps(_BD_PAYLOAD))

        cookies: dict[str, str] = {}
        rid = await WeiboCredential._fetch_visitor_rid(cookies=cookies)

        assert rid == 'rid_value'
        call_kwargs = post_mock.call_args.kwargs
        assert call_kwargs['url'] == VisitorUrl.BD_PAYLOAD_URL
        assert call_kwargs['data']['from'] == 'android-visitor'
        assert call_kwargs['data']['data'].startswith('01')

    async def test_fetch_visitor_rid_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """bd 未返回 rid 时回退为毫秒时间戳"""
        from src.utils.weibo_api.credential import WeiboCredential

        _patch_post(monkeypatch, _BD_ERROR_JSON)

        rid = await WeiboCredential._fetch_visitor_rid(cookies={})

        assert rid.isdigit()

    async def test_post_genvisitor_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """genvisitor2 成功签发 tid 并合并 Cookies"""
        from src.utils.weibo_api.consts import VisitorUrl
        from src.utils.weibo_api.credential import WeiboCredential
        from src.utils.weibo_api.model import WeiboVisitorPageParams

        post_mock = _patch_post(monkeypatch, _GENVISITOR_JSONP)

        page_params = WeiboVisitorPageParams.model_validate({
            'request_id': 'req_id_value', 'return_url': 'https://m.weibo.cn/', 'ver': '20260925', 'from': 'weibo',
        })
        cookies: dict[str, str] = {'tid': 'old_tid'}
        await WeiboCredential._post_genvisitor(page_params=page_params, rid='rid_value', rand='123', cookies=cookies)

        call_kwargs = post_mock.call_args.kwargs
        assert call_kwargs['url'] == VisitorUrl.GENVISITOR_URL
        assert call_kwargs['data']['cb'] == 'visitor_gray_callback'
        assert call_kwargs['data']['tid'] == 'old_tid'
        assert call_kwargs['data']['webdriver'] == 'false'
        assert call_kwargs['data']['rid'] == 'rid_value'
        assert cookies == {'tid': 'tid_value'}

    @pytest.mark.parametrize(
        ('content', 'match'),
        [
            ('visitor_gray_callback({"retcode": 50000000, "msg": "error"});', '签发访客 tid 失败'),
            ('<html>error</html>', '解析 genvisitor2 返回失败'),
        ],
        ids=['failure_retcode', 'unparsable'],
    )
    async def test_post_genvisitor_failure(
            self, monkeypatch: pytest.MonkeyPatch, content: str, match: str,
    ) -> None:
        """genvisitor2 返回异常 retcode / 非标准 JSONP 时抛出异常"""
        from src.utils.weibo_api.credential import WeiboCredential
        from src.utils.weibo_api.model import WeiboVisitorPageParams

        _patch_post(monkeypatch, content)

        page_params = WeiboVisitorPageParams.model_validate({
            'request_id': '', 'return_url': 'https://m.weibo.cn/', 'ver': '20260925', 'from': 'weibo',
        })
        with pytest.raises(RuntimeError, match=match):
            await WeiboCredential._post_genvisitor(page_params=page_params, rid='rid_value', rand='123', cookies={})


class TestRefreshVisitorCookies:
    """访客 Cookies 刷新流程测试 (先算后换, 成功一次性替换, 失败全局凭据保持原状)"""

    async def test_refresh_success_swaps_atomically(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """HTTP 层模拟完整访客流程, 成功后全量替换凭据并落库"""
        from src.utils.weibo_api.consts import VisitorUrl
        from src.utils.weibo_api.credential import WeiboCredential

        def _dispatch_get(*_args, **kwargs):
            if kwargs['url'] == VisitorUrl.START_URL:
                return make_response(headers=[('set-cookie', '_T_WM=twm_value; path=/')], content=_VISITOR_HTML)
            return make_response()

        def _dispatch_post(*_args, **kwargs):
            url = kwargs['url']
            if url == VisitorUrl.VISITOR_ENTER_URL:
                return make_response(headers=[
                    ('set-cookie', 'SUB=sub_value; path=/'),
                    ('set-cookie', 'SUBP=subp_value; path=/'),
                ])
            if url == VisitorUrl.BD_PAYLOAD_URL:
                return make_response(content=json.dumps(_BD_PAYLOAD))
            if url == VisitorUrl.GENVISITOR_URL:
                return make_response(content=_GENVISITOR_JSONP)
            raise AssertionError(f'unexpected url {url}')

        monkeypatch.setattr(WeiboCredential, '_request_get', AsyncMock(side_effect=_dispatch_get))
        monkeypatch.setattr(WeiboCredential, '_request_post', AsyncMock(side_effect=_dispatch_post))
        fake_dal = patch_system_setting_dal(monkeypatch, series=[
            SimpleNamespace(setting_name='weibo_api_config', setting_key='SUB'),
        ])

        clean_manager.update_cookies(SUB='stale_sub')

        result = await WeiboCredential.refresh_visitor_cookies()

        assert result is True
        assert clean_manager.cookies == {
            '_T_WM': 'twm_value',
            'SUB': 'sub_value',
            'SUBP': 'subp_value',
            'tid': 'tid_value',
        }
        assert fake_dal.deleted == ['SUB']
        assert fake_dal.saved == {
            '_T_WM': 'twm_value',
            'SUB': 'sub_value',
            'SUBP': 'subp_value',
            'tid': 'tid_value',
        }

    async def test_refresh_failure_keeps_manager_untouched(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """中间步骤异常: 返回 False 且全局凭据不变, 不落库"""
        from src.utils.weibo_api.credential import WeiboCredential
        from src.utils.weibo_api.credential_manager import _WeiboCredentialManager
        from src.utils.weibo_api.model import WeiboVisitorPageParams

        monkeypatch.setattr(
            WeiboCredential,
            '_fetch_initial_page',
            AsyncMock(return_value=WeiboVisitorPageParams.model_validate({
                'request_id': '', 'return_url': 'https://m.weibo.cn/', 'ver': '20260925', 'from': 'weibo',
            })),
        )
        monkeypatch.setattr(
            WeiboCredential,
            '_post_visitor_enter',
            AsyncMock(side_effect=RuntimeError('enter failed')),
        )
        rebuild_mock = AsyncMock()
        monkeypatch.setattr(_WeiboCredentialManager, 'rebuild_to_database', rebuild_mock)

        clean_manager.update_cookies(SUB='old_sub')

        result = await WeiboCredential.refresh_visitor_cookies()

        assert result is False
        assert clean_manager.get_cookie('SUB') == 'old_sub'
        rebuild_mock.assert_not_awaited()


class TestEnsureCookies:
    """ensure_cookies 逐级回退测试"""

    @staticmethod
    def _mock_load_refresh(
            monkeypatch: pytest.MonkeyPatch,
            load_mock: AsyncMock | None = None,
            refresh_mock: AsyncMock | None = None,
    ) -> tuple[AsyncMock, AsyncMock]:
        """mock 凭据数据库加载与访客刷新流程

        :return: (load_from_database mock, refresh_visitor_cookies mock)
        """
        from src.utils.weibo_api.credential import WeiboCredential
        from src.utils.weibo_api.credential_manager import _WeiboCredentialManager

        load_mock = load_mock or AsyncMock()
        refresh_mock = refresh_mock or AsyncMock()
        monkeypatch.setattr(_WeiboCredentialManager, 'load_from_database', load_mock)
        monkeypatch.setattr(WeiboCredential, 'refresh_visitor_cookies', refresh_mock)
        return load_mock, refresh_mock

    @pytest.mark.parametrize('cookies', [{'SUB': 'sub_value'}, {'SUBP': 'subp_value'}], ids=['sub', 'subp'])
    async def test_memory_hit_short_circuit(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
            cookies: dict,
    ) -> None:
        """内存缓存已有 SUB/SUBP 时直接返回, 不加载数据库也不刷新"""
        from src.utils.weibo_api.credential import WeiboCredential

        load_mock, refresh_mock = self._mock_load_refresh(monkeypatch)

        clean_manager.update_cookies(**cookies)

        await WeiboCredential.ensure_cookies()

        load_mock.assert_not_awaited()
        refresh_mock.assert_not_awaited()

    async def test_database_fallback(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """内存缺失时从数据库加载, 命中后不触发刷新"""
        from src.utils.weibo_api.credential import WeiboCredential

        async def _fake_load():
            clean_manager.clear_cookies()
            clean_manager.update_cookies(SUBP='db_subp')

        load_mock, refresh_mock = self._mock_load_refresh(monkeypatch, load_mock=AsyncMock(side_effect=_fake_load))

        await WeiboCredential.ensure_cookies()

        load_mock.assert_awaited_once()
        refresh_mock.assert_not_awaited()

    async def test_refresh_when_missing(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """内存与数据库均缺失时触发完整访客风控流程"""
        from src.utils.weibo_api.credential import WeiboCredential

        async def _fake_refresh() -> bool:
            clean_manager.update_cookies(SUB='refreshed_sub')
            return True

        load_mock, refresh_mock = self._mock_load_refresh(
            monkeypatch,
            load_mock=AsyncMock(side_effect=lambda: None),
            refresh_mock=AsyncMock(side_effect=_fake_refresh),
        )

        await WeiboCredential.ensure_cookies()

        load_mock.assert_awaited_once()
        refresh_mock.assert_awaited_once()

    async def test_force_refresh(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """force_refresh 跳过内存与数据库检查直接刷新"""
        from src.utils.weibo_api.credential import WeiboCredential

        load_mock, refresh_mock = self._mock_load_refresh(monkeypatch)

        clean_manager.update_cookies(SUB='sub_value')

        await WeiboCredential.ensure_cookies(force_refresh=True)

        load_mock.assert_not_awaited()
        refresh_mock.assert_awaited_once()

    async def test_refresh_failure_raises(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """访客风控流程执行后仍无 SUB/SUBP 时抛出 RuntimeError (不得静默继续)"""
        from src.utils.weibo_api.credential import WeiboCredential

        load_mock, refresh_mock = self._mock_load_refresh(
            monkeypatch,
            load_mock=AsyncMock(side_effect=lambda: None),
            refresh_mock=AsyncMock(return_value=False),
        )

        with pytest.raises(RuntimeError, match='凭据不可用'):
            await WeiboCredential.ensure_cookies()

        load_mock.assert_awaited_once()
        refresh_mock.assert_awaited_once()


class TestCheckVisitorCookiesValid:
    """访客 Cookies 有效性探测测试"""

    async def test_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api.consts import WEIBO_DETECTION_SAMPLE_UID
        from src.utils.weibo_api.credential import WeiboCredential

        get_json_mock = AsyncMock(return_value={'ok': 1, 'data': {}})
        monkeypatch.setattr(WeiboCredential, '_get_api_json', get_json_mock)

        assert await WeiboCredential.check_visitor_cookies_valid() is True

        # 探测请求应使用固定探测样本用户 uid, referer 为样本用户主页
        call_kwargs = get_json_mock.call_args.kwargs
        params = call_kwargs['params']
        assert params['value'] == WEIBO_DETECTION_SAMPLE_UID
        assert params['containerid'] == f'100505{WEIBO_DETECTION_SAMPLE_UID}'
        assert call_kwargs['referer'] == f'https://m.weibo.cn/u/{WEIBO_DETECTION_SAMPLE_UID}'

    @pytest.mark.parametrize(
        'get_json_mock',
        [
            AsyncMock(return_value={'ok': -100}),
            AsyncMock(side_effect=RuntimeError('network error')),
        ],
        ids=['invalid_ok', 'request_exception'],
    )
    async def test_invalid(self, monkeypatch: pytest.MonkeyPatch, get_json_mock: AsyncMock) -> None:
        """响应 ok != 1 或请求异常时视为凭据无效"""
        from src.utils.weibo_api.credential import WeiboCredential

        monkeypatch.setattr(WeiboCredential, '_get_api_json', get_json_mock)

        assert await WeiboCredential.check_visitor_cookies_valid() is False


# ------------------------------------------------------------------ #
# 扫码登录流程测试
# ------------------------------------------------------------------ #


class TestFollowRedirectChain:
    """登录重定向链手动跟随测试 (auto_redirects=False 逐跳收割 set-cookie)"""

    @staticmethod
    def _mock_requests(monkeypatch: pytest.MonkeyPatch, responses: list) -> AsyncMock:
        from src.utils.weibo_api.credential import WeiboCredential

        get_mock = AsyncMock(side_effect=responses)
        monkeypatch.setattr(
            WeiboCredential, '_init_omega_requests', lambda *args, **kwargs: SimpleNamespace(get=get_mock)
        )
        return get_mock

    async def test_full_chain_harvests_each_hop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """逐跳收割 set-cookie, 相对 location 经 urljoin 解析, 每跳均禁用自动重定向"""
        from src.utils.weibo_api.credential import WeiboCredential

        get_mock = self._mock_requests(monkeypatch, [
            make_response(status_code=302, headers=[
                ('set-cookie', 'SUB=sub_hop1; path=/'),
                ('location', '/next'),
            ]),
            make_response(status_code=302, headers=[
                ('set-cookie', 'SUBP=subp_hop2; path=/'),
                ('location', 'https://m.weibo.cn/'),
            ]),
            make_response(status_code=200, headers=[('set-cookie', 'XSRF-TOKEN=xsrf_final; path=/')]),
        ])

        cookies = await WeiboCredential._follow_redirect_chain(
            'https://passport.weibo.com/wbsso/login?ticket=ST-xxx', cookies={}
        )

        assert cookies == {'SUB': 'sub_hop1', 'SUBP': 'subp_hop2', 'XSRF-TOKEN': 'xsrf_final'}
        assert get_mock.await_count == 3
        requested_urls = [call.kwargs['url'] for call in get_mock.call_args_list]
        assert requested_urls == [
            'https://passport.weibo.com/wbsso/login?ticket=ST-xxx',
            'https://passport.weibo.com/next',
            'https://m.weibo.cn/',
        ]
        for call in get_mock.call_args_list:
            assert call.kwargs['auto_redirects'] is False

    async def test_stops_on_non_redirect(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """首个响应非重定向时仅一跳即终止"""
        from src.utils.weibo_api.credential import WeiboCredential

        get_mock = self._mock_requests(monkeypatch, [
            make_response(status_code=200, headers=[('set-cookie', 'X-CSRF-TOKEN=csrf_value; path=/')]),
        ])

        cookies = await WeiboCredential._follow_redirect_chain('https://example.com/', cookies={})

        assert cookies == {'X-CSRF-TOKEN': 'csrf_value'}
        assert get_mock.await_count == 1

    async def test_stops_when_redirect_without_location(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """302 但缺失 location 头时立即终止"""
        from src.utils.weibo_api.credential import WeiboCredential

        get_mock = self._mock_requests(monkeypatch, [
            make_response(status_code=302, headers=[('set-cookie', 'tid=tid_value; path=/')]),
        ])

        cookies = await WeiboCredential._follow_redirect_chain('https://example.com/', cookies={})

        assert cookies == {'tid': 'tid_value'}
        assert get_mock.await_count == 1

    async def test_max_hops_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """重定向链超过 max_hops 时按上限截断"""
        from src.utils.weibo_api.credential import WeiboCredential

        redirect_response = make_response(status_code=302, headers=[('location', 'https://example.com/next')])
        get_mock = self._mock_requests(monkeypatch, [redirect_response] * 10)

        await WeiboCredential._follow_redirect_chain('https://example.com/', cookies={}, max_hops=2)

        assert get_mock.await_count == 2

    @pytest.mark.parametrize('status_code', [301, 303, 307, 308])
    async def test_other_redirect_status_codes_followed(
            self, monkeypatch: pytest.MonkeyPatch, status_code: int,
    ) -> None:
        """301/303/307/308 与 302 一样继续跟随重定向链"""
        from src.utils.weibo_api.credential import WeiboCredential

        get_mock = self._mock_requests(monkeypatch, [
            make_response(status_code=status_code, headers=[('location', 'https://m.weibo.cn/')]),
            make_response(status_code=200, headers=[('set-cookie', 'XSRF-TOKEN=xsrf_value; path=/')]),
        ])

        cookies = await WeiboCredential._follow_redirect_chain('https://example.com/', cookies={})

        assert get_mock.await_count == 2
        assert cookies == {'XSRF-TOKEN': 'xsrf_value'}


class TestFetchLoginCsrfToken:
    """登录 X-CSRF-TOKEN 获取测试"""

    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api.credential import WeiboCredential

        monkeypatch.setattr(
            WeiboCredential,
            '_follow_redirect_chain',
            AsyncMock(return_value={'X-CSRF-TOKEN': 'csrf_value'}),
        )

        assert await WeiboCredential._fetch_login_csrf_token() == 'csrf_value'

    async def test_missing_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api.credential import WeiboCredential

        monkeypatch.setattr(WeiboCredential, '_follow_redirect_chain', AsyncMock(return_value={}))

        with pytest.raises(RuntimeError, match='未获取到 X-CSRF-TOKEN'):
            await WeiboCredential._fetch_login_csrf_token()


class TestFetchLoginRid:
    """登录前 bd 接口 rid 获取测试"""

    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api.consts import LoginUrl, VisitorUrl
        from src.utils.weibo_api.credential import WeiboCredential

        post_mock = _patch_post(monkeypatch, json.dumps(_BD_PAYLOAD))

        rid = await WeiboCredential._fetch_login_rid(csrf_token='csrf_value')

        assert rid == 'rid_value'
        call_kwargs = post_mock.call_args.kwargs
        assert call_kwargs['url'] == VisitorUrl.BD_PAYLOAD_URL
        assert call_kwargs['data']['from'] == 'weibo'
        assert call_kwargs['cookies'] == {'X-CSRF-TOKEN': 'csrf_value'}
        assert call_kwargs['headers']['origin'] == 'https://passport.weibo.com'
        assert call_kwargs['headers']['referer'] == LoginUrl.LOGIN_SIGNIN_REFERER

    @pytest.mark.parametrize(
        ('content', 'match'),
        [
            (_BD_ERROR_JSON, '获取登录 rid 失败'),
            ('<html>error</html>', '解析 bd 接口返回失败'),
        ],
        ids=['failure_retcode', 'unparsable'],
    )
    async def test_failure_raises(self, monkeypatch: pytest.MonkeyPatch, content: str, match: str) -> None:
        """bd 接口返回异常 retcode / 非 JSON 文本时抛出异常"""
        from src.utils.weibo_api.credential import WeiboCredential

        _patch_post(monkeypatch, content)

        with pytest.raises(RuntimeError, match=match):
            await WeiboCredential._fetch_login_rid(csrf_token='csrf_value')


class TestGetLoginQrcode:
    """登录二维码信息获取测试"""

    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api import credential as credential_module
        from src.utils.weibo_api.consts import LoginUrl
        from src.utils.weibo_api.credential import WeiboCredential

        monkeypatch.setattr(WeiboCredential, '_fetch_login_csrf_token', AsyncMock(return_value='csrf_value'))
        get_json_mock = AsyncMock(return_value=_QRCODE_IMAGE_PAYLOAD)
        monkeypatch.setattr(WeiboCredential, '_get_resource_as_json', get_json_mock)
        monkeypatch.setattr(WeiboCredential, '_fetch_login_rid', AsyncMock(return_value='rid_value'))
        # 跳过 credential 模块内的固定 asyncio.sleep 等待
        patch_module_asyncio_sleep(monkeypatch, credential_module)

        qrcode_info = await WeiboCredential.get_login_qrcode()

        assert qrcode_info.qrid == 'qrid_value'
        assert qrcode_info.rid == 'rid_value'
        assert qrcode_info.csrf_token == 'csrf_value'
        assert qrcode_info.image_url == 'https://passport.weibo.com/sso/v2/qrcode/qr.png'

        call_kwargs = get_json_mock.call_args.kwargs
        assert call_kwargs['url'] == LoginUrl.QRCODE_IMAGE_URL
        assert call_kwargs['cookies'] == {'X-CSRF-TOKEN': 'csrf_value'}
        assert call_kwargs['headers']['x-csrf-token'] == 'csrf_value'
        assert call_kwargs['headers']['referer'] == LoginUrl.LOGIN_SIGNIN_WB_REFERER

    async def test_qrcode_failure_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api import credential as credential_module
        from src.utils.weibo_api.credential import WeiboCredential

        monkeypatch.setattr(WeiboCredential, '_fetch_login_csrf_token', AsyncMock(return_value='csrf_value'))
        monkeypatch.setattr(
            WeiboCredential,
            '_get_resource_as_json',
            AsyncMock(return_value={'retcode': 50000000, 'msg': 'error'}),
        )
        # 跳过 credential 模块内的固定 asyncio.sleep 等待
        patch_module_asyncio_sleep(monkeypatch, credential_module)

        with pytest.raises(RuntimeError, match='获取登录二维码失败'):
            await WeiboCredential.get_login_qrcode()


class TestCheckQrcodeLogin:
    """二维码登录状态检查测试"""

    async def test_success_harvests_cookies(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """登录成功时跟随重定向链收割登录 Cookies"""
        from src.utils.weibo_api.consts import LoginStatusCode, LoginUrl
        from src.utils.weibo_api.credential import WeiboCredential

        get_json_mock = AsyncMock(return_value=_QRCODE_CHECK_SUCCESS_PAYLOAD)
        monkeypatch.setattr(WeiboCredential, '_get_resource_as_json', get_json_mock)
        harvest_mock = AsyncMock(return_value={'SUB': 'login_sub', 'SUBP': 'login_subp'})
        monkeypatch.setattr(WeiboCredential, '_follow_redirect_chain', harvest_mock)

        check_data, login_cookies = await WeiboCredential.check_qrcode_login(qrcode_info=_make_qrcode_info())

        assert check_data.retcode == LoginStatusCode.RETCODE_SUCCESS
        assert login_cookies == {'SUB': 'login_sub', 'SUBP': 'login_subp'}
        call_kwargs = get_json_mock.call_args.kwargs
        assert call_kwargs['url'] == LoginUrl.QRCODE_CHECK_URL
        assert call_kwargs['params']['qrid'] == 'qrid_value'
        assert call_kwargs['params']['rid'] == 'rid_value'
        assert call_kwargs['params']['ver'] == LoginUrl.LOGIN_QRCODE_CHECK_VER
        harvest_mock.assert_awaited_once()
        assert harvest_mock.call_args.args[0] == 'https://passport.weibo.com/wbsso/login?ticket=ST-xxx'
        # 重定向链请求头 Referer 带 jumpfrom=weibocom
        assert 'jumpfrom%3Dweibocom' in harvest_mock.call_args.kwargs['headers']['referer']

    @pytest.mark.parametrize(
        'payload',
        [_QRCODE_CHECK_PENDING_PAYLOAD, _QRCODE_CHECK_EXPIRED_PAYLOAD],
        ids=['pending', 'expired'],
    )
    async def test_not_success_returns_none_cookies(self, monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
        """未扫码/二维码过期时不收割 Cookies (过期异常由 login_with_qrcode 轮询层抛出)"""
        from src.utils.weibo_api.credential import WeiboCredential

        monkeypatch.setattr(WeiboCredential, '_get_resource_as_json', AsyncMock(return_value=payload))
        harvest_mock = AsyncMock()
        monkeypatch.setattr(WeiboCredential, '_follow_redirect_chain', harvest_mock)

        check_data, login_cookies = await WeiboCredential.check_qrcode_login(qrcode_info=_make_qrcode_info())

        assert check_data.retcode == payload['retcode']
        assert login_cookies is None
        harvest_mock.assert_not_awaited()


class TestLoginWithQrcode:
    """扫码登录轮询流程测试"""

    def _mock_login_pipeline(
            self,
            monkeypatch: pytest.MonkeyPatch,
            poll_results: list,
    ) -> tuple[AsyncMock, AsyncMock]:
        """mock 扫码登录轮询管线: 固定轮询结果序列, 跳过凭据落库与登录态检查

        :return: (check_qrcode_login mock, rebuild_to_database mock)
        """
        from src.utils.weibo_api import credential as credential_module
        from src.utils.weibo_api.credential import WeiboCredential
        from src.utils.weibo_api.credential_manager import _WeiboCredentialManager

        check_mock = AsyncMock(side_effect=poll_results)
        monkeypatch.setattr(WeiboCredential, 'check_qrcode_login', check_mock)
        # 跳过 credential 模块内的固定 asyncio.sleep 等待
        patch_module_asyncio_sleep(monkeypatch, credential_module)
        rebuild_mock = AsyncMock()
        monkeypatch.setattr(_WeiboCredentialManager, 'rebuild_to_database', rebuild_mock)
        monkeypatch.setattr(WeiboCredential, 'check_login', AsyncMock(return_value=True))
        return check_mock, rebuild_mock

    async def test_login_success_merges_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """登录成功后收割的登录 Cookies 并入现有凭据并落库"""
        from src.utils.weibo_api.credential import WeiboCredential

        _, rebuild_mock = self._mock_login_pipeline(
            monkeypatch,
            [
                (_make_check_result(_QRCODE_CHECK_PENDING_PAYLOAD), None),
                (_make_check_result(_QRCODE_CHECK_CONFIRM_PAYLOAD), None),
                (_make_check_result(_QRCODE_CHECK_SUCCESS_PAYLOAD), {'SUB': 'login_sub', 'SUBP': 'login_subp'}),
            ],
        )

        clean_manager.update_cookies(tid='visitor_tid', SUB='stale_sub')

        result = await WeiboCredential.login_with_qrcode(qrcode_info=_make_qrcode_info())

        assert result is True
        rebuild_mock.assert_awaited_once()
        # 收割的登录 Cookies 覆盖同名键, 既有访客 Cookies 保留
        assert clean_manager.get_cookie('SUB') == 'login_sub'
        assert clean_manager.get_cookie('SUBP') == 'login_subp'
        assert clean_manager.get_cookie('tid') == 'visitor_tid'

    async def test_expired_qrcode_raises(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """50114003 二维码过期应立即抛出异常"""
        from src.utils.weibo_api.credential import WeiboCredential

        self._mock_login_pipeline(
            monkeypatch,
            [(_make_check_result(_QRCODE_CHECK_EXPIRED_PAYLOAD), None)],
        )

        with pytest.raises(RuntimeError, match='登录二维码过期'):
            await WeiboCredential.login_with_qrcode(qrcode_info=_make_qrcode_info())

    async def test_wait_timeout_raises(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """持续未扫码超过尝试上限应抛出等待超时异常"""
        from src.utils.weibo_api.credential import WeiboCredential

        monkeypatch.setattr(WeiboCredential, '_LOGIN_QR_MAX_ATTEMPT', 2)
        check_mock, _ = self._mock_login_pipeline(
            monkeypatch,
            [(_make_check_result(_QRCODE_CHECK_PENDING_PAYLOAD), None)] * 3,
        )

        with pytest.raises(RuntimeError, match='等待超时'):
            await WeiboCredential.login_with_qrcode(qrcode_info=_make_qrcode_info())

        assert check_mock.await_count == 3

    async def test_unknown_retcode_counts_attempt(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        """未知 retcode 计入尝试次数, 超过上限后抛出等待超时异常"""
        from src.utils.weibo_api.credential import WeiboCredential

        monkeypatch.setattr(WeiboCredential, '_LOGIN_QR_MAX_ATTEMPT', 2)
        check_mock, _ = self._mock_login_pipeline(
            monkeypatch,
            [(_make_check_result({'retcode': 50000000, 'msg': 'unknown'}), None)] * 3,
        )

        with pytest.raises(RuntimeError, match='等待超时'):
            await WeiboCredential.login_with_qrcode(qrcode_info=_make_qrcode_info())

        assert check_mock.await_count == 3


class TestCheckLogin:
    """登录状态检查测试"""

    async def test_logged_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api.credential import WeiboCredential

        get_json_mock = AsyncMock(return_value={
            'ok': 1, 'data': {'login': True, 'st': 'st_value', 'user_token': 'ut_value', 'uid': 12345},
        })
        monkeypatch.setattr(WeiboCredential, '_get_api_json', get_json_mock)

        result = await WeiboCredential.check_login()

        assert result is True
        assert get_json_mock.call_args.kwargs['url'] == 'https://m.weibo.cn/api/config'

    @pytest.mark.parametrize(
        'get_json_mock',
        [
            AsyncMock(return_value={'ok': 1, 'data': {'login': False}}),
            AsyncMock(return_value={'ok': 0}),
            AsyncMock(side_effect=RuntimeError('network error')),
        ],
        ids=['not_logged_in', 'missing_data', 'request_exception'],
    )
    async def test_returns_false(self, monkeypatch: pytest.MonkeyPatch, get_json_mock: AsyncMock) -> None:
        """未登录/响应缺 data/请求异常时均返回 False"""
        from src.utils.weibo_api.credential import WeiboCredential

        monkeypatch.setattr(WeiboCredential, '_get_api_json', get_json_mock)

        assert await WeiboCredential.check_login() is False


class TestBaseWeiboApi:
    """BaseWeiboAPI 风控请求头与响应 Cookies 回收测试"""

    @pytest.fixture
    def save_mock(self, monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
        """mock 凭据落库 save_to_database"""
        from src.utils.weibo_api.credential_manager import _WeiboCredentialManager

        mock = AsyncMock()
        monkeypatch.setattr(_WeiboCredentialManager, 'save_to_database', mock)
        return mock

    def test_api_headers_injects_xsrf_token(self, clean_manager: '_WeiboCredentialManager') -> None:
        """凭据缓存中存在 XSRF-TOKEN 时注入 x-xsrf-token 请求头"""
        from src.utils.weibo_api.api_base import BaseWeiboAPI

        clean_manager.update_cookies(**{'XSRF-TOKEN': 'xsrf_value'})

        headers = BaseWeiboAPI._get_api_headers(referer='https://m.weibo.cn/u/12345')

        assert headers['x-xsrf-token'] == 'xsrf_value'
        assert headers['referer'] == 'https://m.weibo.cn/u/12345'
        assert headers['x-requested-with'] == 'XMLHttpRequest'
        assert headers['mweibo-pwa'] == '1'

    def test_api_headers_without_xsrf_token(self, clean_manager: '_WeiboCredentialManager') -> None:
        """凭据缓存中不存在 XSRF-TOKEN 时不注入对应请求头"""
        from src.utils.weibo_api.api_base import BaseWeiboAPI

        headers = BaseWeiboAPI._get_api_headers()

        assert 'x-xsrf-token' not in headers
        assert headers['referer'] == 'https://m.weibo.cn/'

    async def test_sync_response_cookies_updates_and_saves(
            self,
            clean_manager: '_WeiboCredentialManager',
            save_mock: AsyncMock,
    ) -> None:
        """响应 set-cookie 有实际变化时回收进凭据缓存并落库"""
        from src.utils.weibo_api.api_base import BaseWeiboAPI

        clean_manager.update_cookies(SUB='sub_value')

        response = make_response(headers=[('set-cookie', 'XSRF-TOKEN=xsrf_new; path=/')])
        await BaseWeiboAPI._sync_response_cookies(response)

        assert clean_manager.get_cookie('XSRF-TOKEN') == 'xsrf_new'
        assert clean_manager.get_cookie('SUB') == 'sub_value'
        save_mock.assert_awaited_once()

    async def test_sync_response_cookies_skips_unchanged(
            self,
            clean_manager: '_WeiboCredentialManager',
            save_mock: AsyncMock,
    ) -> None:
        """响应 set-cookie 无实际变化时不落库"""
        from src.utils.weibo_api.api_base import BaseWeiboAPI

        clean_manager.update_cookies(SUB='sub_value')

        response = make_response(headers=[('set-cookie', 'SUB=sub_value; path=/')])
        await BaseWeiboAPI._sync_response_cookies(response)

        assert clean_manager.get_cookie('SUB') == 'sub_value'
        save_mock.assert_not_awaited()

    async def test_sync_response_cookies_ignores_unknown_cookies(
            self,
            clean_manager: '_WeiboCredentialManager',
            save_mock: AsyncMock,
    ) -> None:
        """凭据模型外的 Cookies 不入库也不触发落库"""
        from src.utils.weibo_api.api_base import BaseWeiboAPI

        response = make_response(headers=[('set-cookie', 'UNKNOWN_COOKIE=unknown_value; path=/')])
        await BaseWeiboAPI._sync_response_cookies(response)

        assert clean_manager.cookies == {}
        save_mock.assert_not_awaited()

    async def test_get_api_json_injects_headers_and_harvests_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
            save_mock: AsyncMock,
    ) -> None:
        """API 请求注入风控请求头并回收响应 set-cookie"""
        from src.utils.weibo_api.api_base import BaseWeiboAPI

        response = make_response(
            headers=[('set-cookie', 'XSRF-TOKEN=xsrf_value; path=/')],
            content='{"ok": 1}',
        )
        request_mock = AsyncMock(return_value=response)
        monkeypatch.setattr(BaseWeiboAPI, '_request_get', request_mock)

        result = await BaseWeiboAPI._get_api_json('https://m.weibo.cn/api/config', referer='https://m.weibo.cn/u/1')

        assert result == {'ok': 1}
        request_headers = request_mock.call_args.kwargs['headers']
        assert request_headers['x-requested-with'] == 'XMLHttpRequest'
        assert request_headers['referer'] == 'https://m.weibo.cn/u/1'
        assert clean_manager.get_cookie('XSRF-TOKEN') == 'xsrf_value'
        save_mock.assert_awaited_once()

    async def test_sync_response_cookies_deleted_value_removes_key(
            self,
            clean_manager: '_WeiboCredentialManager',
            save_mock: AsyncMock,
    ) -> None:
        """响应 set-cookie 值为 deleted 时移除对应键并触发落库"""
        from src.utils.weibo_api.api_base import BaseWeiboAPI

        clean_manager.update_cookies(SUB='sub_value', tid='tid_value')

        response = make_response(headers=[('set-cookie', 'SUB=deleted; path=/')])
        await BaseWeiboAPI._sync_response_cookies(response)

        assert clean_manager.get_cookie('SUB') is None
        assert clean_manager.get_cookie('tid') == 'tid_value'
        save_mock.assert_awaited_once()

    async def test_sync_response_cookies_save_failure_not_propagated(
            self,
            clean_manager: '_WeiboCredentialManager',
            save_mock: AsyncMock,
    ) -> None:
        """落库异常不得穿透业务请求, 内存缓存保持已更新状态"""
        from src.utils.weibo_api.api_base import BaseWeiboAPI

        save_mock.side_effect = RuntimeError('db down')

        response = make_response(headers=[('set-cookie', 'XSRF-TOKEN=xsrf_value; path=/')])
        await BaseWeiboAPI._sync_response_cookies(response)

        assert clean_manager.get_cookie('XSRF-TOKEN') == 'xsrf_value'
        save_mock.assert_awaited_once()


# ------------------------------------------------------------------ #
# Weibo 主类测试
# ------------------------------------------------------------------ #


class TestUpdateDefaultCookies:
    """Weibo.update_default_cookies 测试"""

    async def test_delegate_to_ensure_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            clean_manager: '_WeiboCredentialManager',
    ) -> None:
        from src.utils.weibo_api import Weibo
        from src.utils.weibo_api.credential import WeiboCredential

        ensure_mock = AsyncMock()
        monkeypatch.setattr(WeiboCredential, 'ensure_cookies', ensure_mock)

        clean_manager.update_cookies(SUB='sub_value')

        result = await Weibo.update_default_cookies()

        ensure_mock.assert_awaited_once()
        assert result == {'SUB': 'sub_value'}


class TestQueryUserData:
    """Weibo.query_user_data 测试 (mock 请求层)"""

    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api import Weibo

        ensure_mock, get_json_mock = _patch_query_layer(monkeypatch, _make_user_info_response())

        user = await Weibo.query_user_data(uid=1934183965)

        assert user.id == 1934183965
        assert user.screen_name == '微博管理员'
        ensure_mock.assert_awaited_once()
        call_kwargs = get_json_mock.call_args.kwargs
        assert call_kwargs['url'] == 'https://m.weibo.cn/api/container/getIndex'
        assert call_kwargs['params'] == {'type': 'uid', 'value': '1934183965', 'containerid': '1005051934183965'}
        assert call_kwargs['referer'] == 'https://m.weibo.cn/u/1934183965'


class TestQueryUserWeiboCards:
    """Weibo.query_user_weibo_cards 测试 (mock 请求层)"""

    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api import Weibo

        ensure_mock, get_json_mock = _patch_query_layer(monkeypatch, _make_cards_response())

        cards = await Weibo.query_user_weibo_cards(uid=1934183965)

        assert len(cards) == 1
        assert cards[0].mblog.id == 5212345678901234
        ensure_mock.assert_awaited_once()
        call_kwargs = get_json_mock.call_args.kwargs
        assert call_kwargs['params']['containerid'] == '1076031934183965'
        assert call_kwargs['referer'] == 'https://m.weibo.cn/u/1934183965'
        assert 'since_id' not in call_kwargs['params']

    async def test_since_id_param(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """传入 since_id 时应加入请求参数"""
        from src.utils.weibo_api import Weibo

        _, get_json_mock = _patch_query_layer(monkeypatch, _make_cards_response(cards=[]))

        cards = await Weibo.query_user_weibo_cards(uid=1934183965, since_id=12345)

        assert cards == []
        assert get_json_mock.call_args.kwargs['params']['since_id'] == '12345'


class TestQueryWeiboCard:
    """Weibo.query_weibo_card 测试 (mock 请求层)"""

    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api import Weibo

        ensure_mock, get_json_mock = _patch_query_layer(monkeypatch, {'ok': 1, 'data': _make_mblog_data()})

        card = await Weibo.query_weibo_card(mid=5212345678901234)

        assert card.id == 5212345678901234
        assert card.text == 'test content'
        ensure_mock.assert_awaited_once()
        call_args = get_json_mock.call_args
        assert call_args.args[0] == 'https://m.weibo.cn/statuses/show'
        assert call_args.args[1] == {'id': '5212345678901234'}
        assert call_args.kwargs['referer'] == 'https://m.weibo.cn/status/5212345678901234'


class TestQueryWeiboExtendText:
    """Weibo.query_weibo_extend_text 测试 (mock 请求层)"""

    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api import Weibo

        _patch_query_layer(monkeypatch, {
            'ok': 1,
            'data': {
                'ok': 1, 'longTextContent': 'full <b>text</b>',
                'reposts_count': 0, 'comments_count': 0, 'attitudes_count': 0,
            },
        })

        text = await Weibo.query_weibo_extend_text(mid=5212345678901234)

        assert text == 'full text'

    async def test_inner_not_ok_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """内层 data.ok != 1 时应抛出 WebSourceException"""
        from src.exception import WebSourceException
        from src.utils.weibo_api import Weibo

        _patch_query_layer(monkeypatch, {
            'ok': 1,
            'data': {'ok': -1, 'longTextContent': '', 'reposts_count': 0, 'comments_count': 0, 'attitudes_count': 0},
        })

        with pytest.raises(WebSourceException):
            await Weibo.query_weibo_extend_text(mid=5212345678901234)


class TestQueryRealtimeHot:
    """Weibo.query_realtime_hot 测试 (mock 请求层)"""

    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api import Weibo

        ensure_mock, get_json_mock = _patch_query_layer(monkeypatch, _make_realtime_hot_response())

        cards = await Weibo.query_realtime_hot()

        assert len(cards) == 1
        assert cards[0].card_group[0].desc == '热搜词'
        ensure_mock.assert_awaited_once()
        assert get_json_mock.call_args.kwargs['params']['containerid'] == (
            '106003type=25&t=3&disable_hot=1&filter_type=realtimehot'
        )


class TestQueryTopFeed:
    """Weibo.query_top_feed 测试 (mock 请求层)"""

    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.weibo_api import Weibo

        ensure_mock, get_json_mock = _patch_query_layer(monkeypatch, _make_top_feed_response())

        statuses = await Weibo.query_top_feed()

        assert len(statuses) == 1
        assert statuses[0].id == 5212345678901234
        ensure_mock.assert_awaited_once()
        assert get_json_mock.call_args.kwargs['url'] == 'https://m.weibo.cn/feed/friends'


class TestQueryErrorResponses:
    """Weibo.query_* 业务错误响应统一测试 (mock 请求层)"""

    @pytest.mark.parametrize(
        ('method_name', 'kwargs', 'response_cases'),
        [
            pytest.param(
                'query_user_data', {'uid': 1934183965},
                [{'ok': -100, 'msg': 'uid 不存在'}, {'ok': 1}],
                id='query_user_data',
            ),
            pytest.param(
                'query_user_weibo_cards', {'uid': 1934183965},
                [{'ok': -100}, {'ok': 1}],
                id='query_user_weibo_cards',
            ),
            pytest.param(
                'query_weibo_card', {'mid': 5212345678901234},
                [{'ok': -100, 'data': None}, {'ok': 1}, {'ok': 1, 'data': 'deleted'}, ['unexpected']],
                id='query_weibo_card',
            ),
            pytest.param(
                'query_weibo_extend_text', {'mid': 5212345678901234},
                [{'ok': -100}, {'ok': 1}],
                id='query_weibo_extend_text',
            ),
            pytest.param('query_realtime_hot', {}, [{'ok': 0}, {'ok': 1}], id='query_realtime_hot'),
            pytest.param('query_top_feed', {}, [{'ok': 0}, {'ok': 1}], id='query_top_feed'),
        ],
    )
    async def test_error_response_raises(
            self, monkeypatch: pytest.MonkeyPatch,
            method_name: str, kwargs: dict, response_cases: list,
    ) -> None:
        """业务错误响应 / data 缺失或非 dict / 整体响应非 dict 时应抛出 WebSourceException 而非 ValidationError"""
        from src.exception import WebSourceException
        from src.utils.weibo_api import Weibo

        for response in response_cases:
            _patch_query_layer(monkeypatch, response)

            with pytest.raises(WebSourceException):
                await getattr(Weibo, method_name)(**kwargs)


# ------------------------------------------------------------------ #
# 真实请求验证
# ------------------------------------------------------------------ #


@requires_live
class TestWeiboLive:
    """Weibo 真实请求验证

    前置条件: 数据库 (system_setting 表 weibo_api_config 系列) 中已配置已登录状态的 cookies;
    需手动设置环境变量 WEIBO_API_REAL_TEST=1 并以
    `pytest tests/test_003_web/test_007_weibo_api.py -k TestWeiboLive -v -s` 单独运行
    """

    @pytest.fixture(autouse=True)
    async def _load_db_cookies(self) -> None:
        """从数据库加载已配置的 weibo cookies 到全局凭据缓存 (幂等, 每个真实用例开头执行)"""
        from src.utils.weibo_api.credential_manager import WEIBO_CREDENTIAL_MANAGER

        await WEIBO_CREDENTIAL_MANAGER.load_from_database()

    async def test_check_login(self) -> None:
        """登录状态检查: 数据库中配置的 cookies 应为已登录状态"""
        from src.utils.weibo_api import WeiboCredential

        assert await WeiboCredential.check_login() is True, '数据库中配置的 weibo cookies 未处于已登录状态'

    async def test_update_default_cookies(self) -> None:
        """确保默认 Cookies 可用 (内存缓存/数据库命中, 不触发访客风控流程)"""
        from src.utils.weibo_api import Weibo

        cookies = await Weibo.update_default_cookies()
        assert cookies, '默认 Cookies 为空'
        assert cookies.get('SUB'), '默认 Cookies 缺少 SUB'

    async def test_query_realtime_hot(self) -> None:
        """获取微博热搜并校验 WeiboRealtimeHotCard 模型"""
        from src.utils.weibo_api import Weibo

        cards = await Weibo.query_realtime_hot()
        assert cards, '热搜查询结果为空'

        hot_card = next((card for card in cards if card.card_group), None)
        assert hot_card is not None, '热搜结果中无含 card_group 的卡片'
        assert any(group.desc for group in hot_card.card_group), '热搜 card_group 缺少 desc'

    async def test_query_user_data(self) -> None:
        """获取用户信息并校验 WeiboUserBase 模型"""
        from src.utils.weibo_api import Weibo
        from src.utils.weibo_api.consts import WEIBO_DETECTION_SAMPLE_UID

        user = await Weibo.query_user_data(uid=WEIBO_DETECTION_SAMPLE_UID)
        assert user.id == int(WEIBO_DETECTION_SAMPLE_UID)
        assert user.screen_name, '用户 screen_name 为空'

    async def test_query_user_weibo_cards(self) -> None:
        """获取用户微博并校验 WeiboCard 模型"""
        from src.utils.weibo_api import Weibo
        from src.utils.weibo_api.consts import WEIBO_DETECTION_SAMPLE_UID

        cards = await Weibo.query_user_weibo_cards(uid=WEIBO_DETECTION_SAMPLE_UID)
        assert cards, '用户微博查询结果为空'

        mblog = cards[0].mblog
        assert mblog.id > 0
        assert mblog.user.id == int(WEIBO_DETECTION_SAMPLE_UID)
        assert mblog.bid, '微博 bid 为空'

    async def test_query_weibo_card(self) -> None:
        """获取单条微博并校验 WeiboMbLog 模型"""
        from src.utils.weibo_api import Weibo
        from src.utils.weibo_api.consts import WEIBO_DETECTION_SAMPLE_UID

        cards = await Weibo.query_user_weibo_cards(uid=WEIBO_DETECTION_SAMPLE_UID)
        assert cards, '用户微博查询结果为空, 无法获取单条微博样本'
        mid = cards[0].mblog.id

        card = await Weibo.query_weibo_card(mid=mid)
        assert card.id == mid
        assert card.text, '单条微博 text 为空'

    async def test_query_weibo_extend_text(self) -> None:
        """获取微博展开全文 (需样本用户首页存在长微博)"""
        from src.utils.weibo_api import Weibo
        from src.utils.weibo_api.consts import WEIBO_DETECTION_SAMPLE_UID

        cards = await Weibo.query_user_weibo_cards(uid=WEIBO_DETECTION_SAMPLE_UID)
        long_text_mid = next((card.mblog.id for card in cards if card.mblog.isLongText), None)
        if long_text_mid is None:
            pytest.skip('样本用户首页无长微博, 跳过展开全文验证')

        extend_text = await Weibo.query_weibo_extend_text(mid=long_text_mid)
        assert isinstance(extend_text, str)
        assert extend_text, '微博展开全文为空'

    async def test_query_top_feed(self) -> None:
        """获取首页 feed 并校验 WeiboMbLog 模型 (需要已登录状态)"""
        from src.utils.weibo_api import Weibo

        statuses = await Weibo.query_top_feed()
        assert isinstance(statuses, list)
        assert statuses, '首页 feed 为空'
        assert statuses[0].id > 0
        assert statuses[0].user.id > 0


@require_force_refresh_test
class TestRefreshVisitorCookiesLive:
    """访客流程强制刷新真实验证 (会重建数据库 cookies 覆盖登录态)

    需手动设置环境变量 WEIBO_API_FORCE_REFRESH_TEST=1 并以
    `pytest tests/test_003_web/test_007_weibo_api.py -k TestRefreshVisitorCookiesLive -v -s` 单独运行
    """

    async def test_refresh_visitor_cookies_live(self) -> None:
        """访客风控流程强制刷新 Cookies 后业务查询可用"""
        from src.utils.weibo_api import Weibo, WeiboCredential

        await WeiboCredential.ensure_cookies(force_refresh=True)

        cards = await Weibo.query_realtime_hot()
        assert cards, '热搜查询为空, 访客 Cookies 可能未通过风控校验'
