"""
@Author         : Ailitonia
@Date           : 2026/9/13 16:29
@FileName       : test_003_bilibili_api
@Project        : omega-miya
@Description    : bilibili api 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
import json
import re
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import quote

import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from src.utils.bilibili_api.credential_manager import _BilibiliCredentialManager

# ------------------------------------------------------------------ #
# wbi 签名已知答案向量 (本地按参考算法预计算, 不依赖网络)
# ------------------------------------------------------------------ #

_WBI_KEY_IMG = '7cd084941338484aae1ad9425b84077c'
_WBI_KEY_SUB = '4932caff0ff746eab6f01bf08b70ac45'
_WBI_KEY_MIXIN = 'ea1db124af3c7062474693fa704f4ff8'
_WBI_WTS = 1700000000
_WBI_FOO_BAR_W_RID = 'cc9a14300aec84d78d84e6c5ca73aa74'
_WBI_FILTERED_W_RID = 'ce1c759c3011f7a96c6577959e01a7fd'

_HMAC_SHA256_KNOWN_ANSWER = 'bb79f0d980ffbb51597aa1a3e8b55603025cc1322ac766f4c1a98852e6182514'
"""hmac_sha256('XgwSnGZ1p', 'ts1700000000') 的已知答案"""

# ------------------------------------------------------------------ #
# 接口模拟响应
# ------------------------------------------------------------------ #

_SPI_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {'b_3': 'buvid3_value', 'b_4': 'buvid4_value'},
}
"""finger/spi 接口模拟响应"""

_EXCLIMBWUZHI_SUCCESS_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1, 'data': {},
}
"""ExClimbWuzhi 接口模拟成功响应"""

_DYNAMICS_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {'has_more': False, 'items': [], 'offset': '', 'update_baseline': '0', 'update_num': 0},
}
"""动态列表接口模拟响应"""

_WBI_IMG = {
    'img_url': f'https://i0.hdslb.com/bfs/wbi/{_WBI_KEY_IMG}.png',
    'sub_url': f'https://i0.hdslb.com/bfs/wbi/{_WBI_KEY_SUB}.png',
}
"""nav 接口 wbi_img 字段模拟数据 (键长需满足 mixin_key 索引要求)"""

_TICKET_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {
        'ticket': 'ticket_value',
        'created_at': _WBI_WTS,
        'ttl': 86400,
        'context': {},
        'nav': {
            'img': f'https://i0.hdslb.com/bfs/wbi/{_WBI_KEY_IMG}.png',
            'sub': f'https://i0.hdslb.com/bfs/wbi/{_WBI_KEY_SUB}.png',
        },
    },
}
"""BiliTicket 接口模拟响应"""

_DYNAMIC_AUTHOR = {
    'face': 'https://i0.hdslb.com/bfs/face/face.jpg',
    'face_nft': False,
    'jump_url': '//space.bilibili.com/12345',
    'label': '',
    'mid': '12345',
    'name': 'test_up',
    'pub_ts': _WBI_WTS,
    'type': 'AUTHOR_TYPE_NORMAL',
}
"""动态 module_author 模拟数据"""

_DYNAMIC_ITEM = {
    'basic': {'like_icon': {}},
    'id_str': '1001',
    'modules': {'module_author': _DYNAMIC_AUTHOR, 'module_dynamic': {}},
    'type': 'DYNAMIC_TYPE_AV',
    'visible': True,
}
"""单条动态模拟数据 (DynCommonItem 最小有效载荷)"""

_DYNAMIC_DETAIL_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {'item': _DYNAMIC_ITEM},
}
"""动态详情接口模拟响应"""

_DYNAMIC_OPUS_DETAIL_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {'item': {'basic': {'like_icon': {}}, 'id_str': '1002', 'modules': [], 'type': 2}},
}
"""图文详情接口模拟响应 (_DynOpusItem 最小有效载荷)"""

_REFRESH_SUCCESS_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {'status': 0, 'message': 'ok', 'refresh_token': 'new_rt'},
}
"""cookie/refresh 接口模拟成功响应"""

_QRCODE_GENERATE_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {'url': 'https://passport.bilibili.com/h5-app/passport/login', 'qrcode_key': 'qrcode_key_value'},
}
"""qrcode/generate 接口模拟响应"""


def _make_qrcode_poll_payload(code: int, message: str) -> dict:
    """构造 qrcode/poll 接口模拟响应"""
    return {
        'code': 0, 'message': '0', 'ttl': 1,
        'data': {
            'url': 'https://space.bilibili.com',
            'refresh_token': 'login_rt' if code == 0 else '',
            'timestamp': 1700000000000,
            'code': code,
            'message': message,
        },
    }


_QRCODE_POLL_SUCCESS_PAYLOAD = _make_qrcode_poll_payload(0, 'ok')
"""qrcode/poll 接口模拟登录成功响应"""

_QRCODE_POLL_PENDING_PAYLOAD = _make_qrcode_poll_payload(86101, '未扫码')
"""qrcode/poll 接口模拟待扫码响应"""

_QRCODE_POLL_EXPIRED_PAYLOAD = _make_qrcode_poll_payload(86038, '二维码已失效')
"""qrcode/poll 接口模拟二维码过期响应"""

_ROOM_INFO_DATA = {
    'uid': '2165572',
    'room_id': '1234567',
    'short_id': '0',
    'live_status': 1,
    'title': 'test room',
    'live_time': '2024-01-01 12:00:00',
}
"""直播间信息模拟数据"""

_ROOM_INFO_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': _ROOM_INFO_DATA,
}
"""Room/get_info 接口模拟响应"""

_ROOM_BASE_INFO_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {'by_room_ids': {'1234567': _ROOM_INFO_DATA}},
}
"""getRoomBaseInfo 接口模拟响应"""

_USERS_ROOM_INFO_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {'2165572': _ROOM_INFO_DATA, '12345': _ROOM_INFO_DATA},
}
"""get_status_info_by_uids 接口模拟响应 (JSON 键为字符串, 模型应强转为 int)"""

_ROOM_USER_INFO_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {
        'info': {
            'uid': 2165572,
            'uname': 'test_anchor',
            'face': 'https://i0.hdslb.com/bfs/face/face.jpg',
            'rank': '10000',
            'gender': 0,
        },
        'san': 12,
    },
}
"""get_anchor_in_room 接口模拟响应"""

_ACCOUNT_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {
        'mid': 2165572, 'uname': 'test_uname', 'userid': '', 'sign': '',
        'birthday': '05-05', 'sex': '保密', 'nick_free': True, 'rank': '10000',
    },
}
"""member/web/account 接口模拟响应"""

_VIP_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {
        'mid': 2165572, 'vip_type': 2, 'vip_status': 1,
        'vip_due_date': 2000000000000, 'vip_pay_type': 1, 'theme_type': 0,
    },
}
"""vip/web/user/info 接口模拟响应"""

_USER_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {
        'mid': 12345, 'name': 'test_up', 'sex': '保密',
        'face': 'https://i0.hdslb.com/bfs/face/face.jpg', 'sign': '',
        'rank': 10000, 'level': 6, 'jointime': 0, 'is_followed': False,
        'top_photo': '/bfs/space/cb1c3c50cb22d4a3c32b4ff2f9e8b6e2.png',
        'live_room': None, 'birthday': '05-05',
    },
}
"""space/wbi/acc/info 接口模拟响应"""

_USER_SEARCH_RESULT_ITEM = {
    'type': 'bili_user', 'mid': 12345, 'uname': 'test_up', 'usign': '', 'fans': 100,
    'videos': 10, 'upic': 'https://i0.hdslb.com/bfs/face/upic.jpg', 'level': 6, 'gender': 0,
    'is_upuser': 1, 'is_live': 0, 'room_id': 0, 'res': [],
    'official_verify': {'type': 0, 'desc': ''}, 'hit_columns': ['uname'],
}
"""用户搜索结果项模拟数据"""

_VIDEO_SEARCH_RESULT_ITEM = {
    'type': 'video', 'id': 1001, 'author': 'test_up', 'mid': 12345, 'typeid': '0',
    'typename': '', 'arcurl': '', 'aid': 1001, 'bvid': 'BV1xx411c7mD', 'title': 'test_video',
    'description': '', 'pic': '', 'play': 0, 'video_review': 0, 'favorites': 0,
    'tag': '', 'review': 0, 'pubdate': 0, 'senddate': 0, 'duration': '0:00',
    'is_union_video': 0, 'rank_score': 0, 'hit_columns': [],
}
"""视频搜索结果项模拟数据"""

_SEARCH_TYPE_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {
        'seid': '1', 'suggest_keyword': '', 'rqt_type': 'search', 'show_column': 0,
        'result': [_USER_SEARCH_RESULT_ITEM, _VIDEO_SEARCH_RESULT_ITEM],
    },
}
"""search/type 接口模拟响应 (混合用户与视频结果)"""

_COOKIE_INFO_PAYLOAD = {
    'code': 0, 'message': '0', 'ttl': 1,
    'data': {'refresh': True, 'timestamp': 1700000000000},
}
"""cookie/info 接口模拟响应"""

_SPM_HTML = '<html><head><meta name="spm_prefix" content="333.999"></head><body></body></html>'
"""含 spm_prefix 的模拟首页 HTML"""

_SPM_HTML_NO_META = '<html><head></head><body></body></html>'
"""缺少 spm_prefix 的模拟首页 HTML"""

_SPM_HTML_EMPTY_CONTENT = '<html><head><meta name="spm_prefix" content=""></head><body></body></html>'
"""spm_prefix 内容为空的模拟首页 HTML"""

_REFRESH_CSRF_HTML = '<html><body><div id="1-name">refresh_csrf_value</div></body></html>'
"""含 refresh_csrf 的模拟 correspond HTML"""

_REFRESH_CSRF_HTML_NO_DIV = '<html><body></body></html>'
"""缺少 refresh_csrf 节点的模拟 correspond HTML"""

_REFRESH_CSRF_HTML_EMPTY = '<html><body><div id="1-name"></div></body></html>'
"""refresh_csrf 内容为空的模拟 correspond HTML"""

_USER_SPACE_HTML = (
    '<html><head><script id="__RENDER_DATA__">'
    '%7B%22access_id%22%3A%22access_id_value%22%7D'
    '</script></head><body></body></html>'
)
"""含 __RENDER_DATA__ 的模拟用户空间页 HTML"""


def _make_search_all_payload() -> dict:
    """构造 search/all 接口模拟响应 (pageinfo/top_tlist 字段繁多, 程序化生成)"""
    pageinfo_keys = (
        'pgc', 'live_room', 'topic', 'video', 'user', 'bili_user', 'media_ft', 'article', 'media_bangumi',
        'special', 'operation_card', 'upuser', 'movie', 'live_all', 'tv', 'live', 'bangumi', 'activity',
        'live_master', 'live_user',
    )
    top_tlist_keys = (
        'pgc', 'live_room', 'topic', 'video', 'user', 'bili_user', 'media_ft', 'article', 'media_bangumi',
        'card', 'operation_card', 'upuser', 'movie', 'tv', 'live', 'special', 'bangumi', 'activity',
        'live_master', 'live_user',
    )
    return {
        'code': 0, 'message': '0', 'ttl': 1,
        'data': {
            'seid': '1', 'suggest_keyword': '', 'rqt_type': 'search',
            'pageinfo': {k: {'numResults': 0, 'total': 0, 'pages': 0} for k in pageinfo_keys},
            'top_tlist': dict.fromkeys(top_tlist_keys, 0),
            'show_column': 0, 'show_module_list': [],
            'result': [{'result_type': 'bili_user', 'data': [_USER_SEARCH_RESULT_ITEM]}],
        },
    }


def _make_nav_payload(code: int, *, is_login: bool = True, mid: str = '12345') -> dict:
    """构造 nav 接口模拟响应"""
    return {
        'code': code, 'message': f'message_of_code_{code}', 'ttl': 1,
        'data': {'isLogin': is_login, 'wbi_img': _WBI_IMG, 'uname': 'test_uname', 'mid': mid},
    }


def _make_room_info_dict(**overrides) -> dict:
    """构造 RoomInfoData 最小有效输入"""
    data = {'uid': '1001', 'room_id': '2002', 'short_id': '0', 'live_status': 1, 'title': 'test room'}
    data.update(overrides)
    return data


# ------------------------------------------------------------------ #
# 测试基建
# ------------------------------------------------------------------ #


def _patch_system_setting_dal(
        monkeypatch: pytest.MonkeyPatch,
        series: list | None = None,
        unique: dict[str, str] | None = None,
) -> SimpleNamespace:
    """以记录调用的伪 DAL 替换 SystemSettingDAL.create

    :param series: query_series 返回的配置项列表
    :param unique: query_unique 的键值表, 未命中键抛出 NoResultFound
    :return: SimpleNamespace(deleted=[被删除的 setting_key], saved={setting_key: setting_value})
    """
    from sqlalchemy.exc import NoResultFound

    from src.database import SystemSettingDAL

    fake_dal = SimpleNamespace(deleted=[], saved={}, _series=series or [], _unique=unique or {})

    async def _query_series(setting_name: str, **_kwargs):
        return fake_dal._series

    async def _query_unique(setting_name: str, setting_key: str, **_kwargs):
        if setting_key not in fake_dal._unique:
            raise NoResultFound(f'no row for {setting_key!r}')
        return SimpleNamespace(
            setting_name=setting_name, setting_key=setting_key, setting_value=fake_dal._unique[setting_key]
        )

    async def _delete(setting_name: str, setting_key: str) -> None:
        fake_dal.deleted.append(setting_key)

    async def _add_update_exist(setting_name: str, setting_key: str, setting_value: str, **_kwargs) -> None:
        fake_dal.saved[setting_key] = setting_value

    fake_dal.query_series = _query_series
    fake_dal.query_unique = _query_unique
    fake_dal.delete = _delete
    fake_dal.add_update_exist = _add_update_exist

    @asynccontextmanager
    async def _fake_create(_cls):
        yield fake_dal

    monkeypatch.setattr(SystemSettingDAL, 'create', classmethod(_fake_create))
    return fake_dal


@pytest.fixture
def credential_manager_sandbox() -> '_BilibiliCredentialManager':
    """全局凭据管理器状态沙箱: 测试前快照, 测试结束后恢复"""
    from src.utils.bilibili_api.credential_manager import (
        BILIBILI_CREDENTIAL_MANAGER,
        BilibiliCookiesData,
    )

    snapshot = BilibiliCookiesData.model_validate(BILIBILI_CREDENTIAL_MANAGER.cookies)
    yield BILIBILI_CREDENTIAL_MANAGER
    BILIBILI_CREDENTIAL_MANAGER._cookies_data = snapshot


@pytest.fixture
def bilibili_common_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """复位 BilibiliCommon 及各子类的类级缓存 (_api_uuid/_api_spm_prefix), 防止跨用例泄漏

    被测代码会直接对类属性赋值 (不经 monkeypatch), 故测试结束后需手动删除残留属性
    """
    from src.utils.bilibili_api.api.base import BilibiliCommon

    classes = [BilibiliCommon, *BilibiliCommon.__subclasses__()]
    for cls in classes:
        monkeypatch.delattr(cls, '_api_uuid', raising=False)
        monkeypatch.delattr(cls, '_api_spm_prefix', raising=False)
        monkeypatch.setattr(cls, '_api_spm_prefix_is_init', False)
    yield
    for cls in classes:
        for attr in ('_api_uuid', '_api_spm_prefix'):
            try:
                delattr(cls, attr)
            except AttributeError:
                pass


# ------------------------------------------------------------------ #
# misc 纯函数测试
# ------------------------------------------------------------------ #


class TestWbiSign:
    """wbi 签名纯函数测试 (已知答案向量)"""

    def test_get_mixin_key_known_answer(self) -> None:
        from src.utils.bilibili_api.misc.wbi import get_mixin_key

        assert get_mixin_key(_WBI_KEY_IMG + _WBI_KEY_SUB) == _WBI_KEY_MIXIN

    def test_enc_wbi_known_answer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api.misc import wbi

        monkeypatch.setattr(wbi.time, 'time', lambda: _WBI_WTS)
        signed = wbi.enc_wbi(params={'foo': 'bar'}, img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)

        assert signed == {'foo': 'bar', 'wts': str(_WBI_WTS), 'w_rid': _WBI_FOO_BAR_W_RID}

    def test_enc_wbi_filters_special_chars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """参数值中的 !'()* 字符在签名前被过滤"""
        from src.utils.bilibili_api.misc import wbi

        monkeypatch.setattr(wbi.time, 'time', lambda: _WBI_WTS)
        signed = wbi.enc_wbi(params={'text': "a!b'c(d)e*f"}, img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)

        assert signed['text'] == 'abcdef'
        assert signed['w_rid'] == _WBI_FILTERED_W_RID

    def test_enc_wbi_params_order_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """参数按 key 排序后签名, 传入顺序不影响 w_rid"""
        from src.utils.bilibili_api.misc import wbi

        monkeypatch.setattr(wbi.time, 'time', lambda: _WBI_WTS)
        signed_ab = wbi.enc_wbi(params={'a': '1', 'b': '2'}, img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)
        signed_ba = wbi.enc_wbi(params={'b': '2', 'a': '1'}, img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)

        assert signed_ab == signed_ba

    def test_enc_wbi_none_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """None 参数仅注入 wts/w_rid"""
        from src.utils.bilibili_api.misc import wbi

        monkeypatch.setattr(wbi.time, 'time', lambda: _WBI_WTS)
        signed = wbi.enc_wbi(params=None, img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)

        assert set(signed.keys()) == {'wts', 'w_rid'}

    def test_enc_wbi_does_not_mutate_params(self) -> None:
        """签名不得修改传入的 dict"""
        from src.utils.bilibili_api.misc import wbi

        original = {'foo': 'bar'}
        wbi.enc_wbi(params=original, img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)

        assert original == {'foo': 'bar'}

    def test_extract_key_from_wbi_image(self) -> None:
        from src.utils.bilibili_api.misc.wbi import extract_key_from_wbi_image

        assert extract_key_from_wbi_image('https://i0.hdslb.com/bfs/wbi/abc123.png') == 'abc123'
        assert extract_key_from_wbi_image('https://i0.hdslb.com/bfs/wbi/abc123') == 'abc123'

    def test_sign_wbi_params_nav(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """从 nav 响应提取 img_key/sub_key 并签名"""
        from src.utils.bilibili_api.misc import wbi
        from src.utils.bilibili_api.models import WebInterfaceNav

        monkeypatch.setattr(wbi.time, 'time', lambda: _WBI_WTS)
        nav = WebInterfaceNav.model_validate({
            'code': 0, 'message': '0', 'ttl': 1,
            'data': {
                'isLogin': True,
                'wbi_img': {
                    'img_url': f'https://i0.hdslb.com/bfs/wbi/{_WBI_KEY_IMG}.png',
                    'sub_url': f'https://i0.hdslb.com/bfs/wbi/{_WBI_KEY_SUB}.png',
                },
            },
        })

        signed = wbi.sign_wbi_params_nav(nav_data=nav, params={'foo': 'bar'})

        assert signed['w_rid'] == _WBI_FOO_BAR_W_RID


class TestWebTicket:
    """BiliTicket 参数生成测试"""

    def test_hmac_sha256_known_answer(self) -> None:
        from src.utils.bilibili_api.misc.web_ticket import hmac_sha256

        assert hmac_sha256('XgwSnGZ1p', 'ts1700000000') == _HMAC_SHA256_KNOWN_ANSWER

    def test_create_params_without_bili_jct(self) -> None:
        from src.utils.bilibili_api.misc.web_ticket import create_gen_web_ticket_params

        params = create_gen_web_ticket_params()

        assert params['key_id'] == 'ec02'
        assert params['csrf'] == ''
        assert re.fullmatch(r'[0-9a-f]{64}', params['hexsign'])
        assert params['context[ts]'].isdigit()

    def test_create_params_with_bili_jct(self) -> None:
        from src.utils.bilibili_api.misc.web_ticket import create_gen_web_ticket_params

        params = create_gen_web_ticket_params(bili_jct='jct_value')

        assert params['csrf'] == 'jct_value'

    def test_hexsign_matches_timestamp(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """hexsign 与 context[ts] 必须对应同一时间戳"""
        from src.utils.bilibili_api.misc import web_ticket

        monkeypatch.setattr(web_ticket.time, 'time', lambda: 1700000000.0)
        params = web_ticket.create_gen_web_ticket_params()

        assert params['context[ts]'] == '1700000000'
        assert params['hexsign'] == _HMAC_SHA256_KNOWN_ANSWER


class TestExclimbwuzhi:
    """buvid 指纹与激活载荷生成测试"""

    def test_gen_uuid_infoc_format(self) -> None:
        from src.utils.bilibili_api.misc.exclimbwuzhi import gen_uuid_infoc

        uuid_value = gen_uuid_infoc()

        assert uuid_value.endswith('infoc')
        assert uuid_value.count('-') == 4
        assert re.fullmatch(r'[0-9A-F-]+infoc', uuid_value)

    def test_gen_uuid_infoc_unique(self) -> None:
        from src.utils.bilibili_api.misc.exclimbwuzhi import gen_uuid_infoc

        assert gen_uuid_infoc() != gen_uuid_infoc()

    def test_gen_buvid_fp_deterministic(self) -> None:
        from src.utils.bilibili_api.misc.exclimbwuzhi import gen_buvid_fp

        fp_first = gen_buvid_fp('test_key', 31)
        fp_second = gen_buvid_fp('test_key', 31)

        assert fp_first == fp_second
        assert re.fullmatch(r'[0-9a-f]+', fp_first)

    def test_gen_buvid_fp_seed_sensitive(self) -> None:
        from src.utils.bilibili_api.misc.exclimbwuzhi import gen_buvid_fp

        assert gen_buvid_fp('test_key', 31) != gen_buvid_fp('test_key', 32)

    def test_gen_payload_structure(self) -> None:
        """激活载荷为双层 JSON, 关键字段正确插值"""
        from src.utils.bilibili_api.misc.exclimbwuzhi import gen_payload

        payload = gen_payload(
            post_url='https://www.bilibili.com',
            spm_prefix='333.999',
            uuid='uuid_value',
            user_agent='test_ua',
        )

        outer = json.loads(payload)
        assert set(outer.keys()) == {'payload'}

        content = json.loads(outer['payload'])
        assert content['03bf'] == 'https%3A%2F%2Fwww.bilibili.com'
        assert content['39c8'] == '333.999.fp.risk'
        assert content['df35'] == 'uuid_value'
        assert content['3c43']['b8ce'] == 'test_ua'


# ------------------------------------------------------------------ #
# 凭据管理器与 Cookies 模型测试
# ------------------------------------------------------------------ #


class TestQuoteSessdata:
    """SESSDATA 编码测试 (对原始值与已编码值均应幂等)"""

    def test_raw_value_quoted(self) -> None:
        from src.utils.bilibili_api.credential_manager import BilibiliCookiesData

        data = BilibiliCookiesData.model_validate({'SESSDATA': 'a,b*c'})

        assert data.bilibili_api_sessdata == quote('a,b*c')

    def test_quoted_value_idempotent(self) -> None:
        from src.utils.bilibili_api.credential_manager import BilibiliCookiesData

        quoted = quote('a,b*c')
        data = BilibiliCookiesData.model_validate({'SESSDATA': quoted})

        assert data.bilibili_api_sessdata == quoted

    def test_invalid_percent_sequence_normalized(self) -> None:
        """含非法 % 序列的原始值应被正确编码而非误判为已编码"""
        from src.utils.bilibili_api.credential_manager import BilibiliCookiesData

        data = BilibiliCookiesData.model_validate({'SESSDATA': 'a%b'})

        assert data.bilibili_api_sessdata == 'a%25b'

    def test_none_passthrough(self) -> None:
        from src.utils.bilibili_api.credential_manager import BilibiliCookiesData

        data = BilibiliCookiesData.model_validate({})

        assert data.bilibili_api_sessdata is None


class TestCookiesData:
    """Cookies 数据模型边界测试"""

    def test_as_dict_filters_none(self) -> None:
        from src.utils.bilibili_api.credential_manager import BilibiliCookiesData

        data = BilibiliCookiesData.model_validate({'SESSDATA': 'sess_value'})

        assert data.as_dict == {'SESSDATA': 'sess_value'}

    def test_iter_items_contains_none(self) -> None:
        """iter_items 覆盖全部字段 (含 None 值), 用于持久化时识别缺失键"""
        from src.utils.bilibili_api.credential_manager import BilibiliCookiesData

        items = dict(BilibiliCookiesData().iter_items)

        assert 'SESSDATA' in items
        assert items['SESSDATA'] is None
        assert 'img_key' in items

    def test_login_cookies_subset(self) -> None:
        """登录用 cookies 不含 wbi 签名键与 refresh_token"""
        from src.utils.bilibili_api.credential_manager import BilibiliCookiesData, BilibiliLoginCookiesData

        full = BilibiliCookiesData.model_validate({
            'SESSDATA': 'sess_value',
            'img_key': 'img_key_value',
            'sub_key': 'sub_key_value',
            'ac_time_value': 'rt_value',
        })
        login = BilibiliLoginCookiesData.model_validate(full.as_dict)

        assert login.as_dict == {'SESSDATA': 'sess_value'}

    def test_number_coerced_to_str(self) -> None:
        """coerce_numbers_to_str: 数字 cookie 值被强转为字符串"""
        from src.utils.bilibili_api.credential_manager import BilibiliCookiesData

        data = BilibiliCookiesData.model_validate({'DedeUserID': 12345, 'b_nut': 1700000000})

        assert data.as_dict['DedeUserID'] == '12345'
        assert data.as_dict['b_nut'] == '1700000000'


class TestCredentialManagerOps:
    """凭据管理器内存操作语义测试"""

    def test_update_cookies_merges(self, credential_manager_sandbox: '_BilibiliCredentialManager') -> None:
        """update_cookies 覆盖同名键, 保留未提供的既有键"""
        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value', bili_jct='jct_value')

        manager.update_cookies(SESSDATA='new_sess')

        assert manager.get_cookie('SESSDATA') == 'new_sess'
        assert manager.get_cookie('bili_jct') == 'jct_value'

    def test_update_cookies_ignores_unknown_keys(
            self, credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        manager = credential_manager_sandbox
        manager.clear_cookies()

        manager.update_cookies(SESSDATA='sess_value', unknown_cookie='x')

        assert 'unknown_cookie' not in manager.cookies

    def test_replace_cookies(self, credential_manager_sandbox: '_BilibiliCredentialManager') -> None:
        """replace_cookies 一次性全量替换, 未包含的既有键被丢弃"""
        from src.utils.bilibili_api.credential_manager import BilibiliCookiesData

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='old_sess', bili_jct='old_jct')

        manager.replace_cookies(BilibiliCookiesData.model_validate({'SESSDATA': 'new_sess'}))

        assert manager.cookies == {'SESSDATA': 'new_sess'}

    def test_clear_cookies(self, credential_manager_sandbox: '_BilibiliCredentialManager') -> None:
        manager = credential_manager_sandbox
        manager.update_cookies(SESSDATA='sess_value')

        manager.clear_cookies()

        assert manager.cookies == {}

    def test_get_cookie_by_field_name(self, credential_manager_sandbox: '_BilibiliCredentialManager') -> None:
        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value')

        assert manager.get_cookie('bilibili_api_sessdata', alias=False) == manager.get_cookie('SESSDATA')


class TestCredentialManagerPersistence:
    """凭据落库测试 (登录/刷新后应重建数据库系列, 清除陈旧键)"""

    async def test_rebuild_removes_stale_keys(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value')

        fake_dal = _patch_system_setting_dal(monkeypatch, series=[
            SimpleNamespace(setting_name='bilibili_api_config', setting_key='SESSDATA'),
            SimpleNamespace(setting_name='bilibili_api_config', setting_key='STALE_KEY'),
        ])

        await manager.rebuild_to_database()

        assert set(fake_dal.deleted) == {'SESSDATA', 'STALE_KEY'}
        assert fake_dal.saved == {'SESSDATA': 'sess_value'}

    async def test_save_skips_none_values(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """save_to_database 仅写入非 None 值且不删除既有键"""
        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value')

        fake_dal = _patch_system_setting_dal(monkeypatch)

        await manager.save_to_database()

        assert fake_dal.saved == {'SESSDATA': 'sess_value'}
        assert not fake_dal.deleted

    async def test_load_from_database(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """load_from_database 先清空再加载: 命中键写入, 未命中键置 None"""
        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='stale_sess', bili_jct='stale_jct')

        _patch_system_setting_dal(monkeypatch, unique={'SESSDATA': 'db_sess'})

        await manager.load_from_database()

        assert manager.get_cookie('SESSDATA') == 'db_sess'
        assert manager.get_cookie('bili_jct') is None


# ------------------------------------------------------------------ #
# api/base.py 测试
# ------------------------------------------------------------------ #


class TestBilibiliCommonBase:
    """BilibiliCommon 基础行为测试"""

    def test_root_url(self) -> None:
        from src.utils.bilibili_api.api.base import BilibiliCommon

        assert BilibiliCommon._get_root_url() == 'https://www.bilibili.com'

    def test_default_header(self) -> None:
        from src.utils.bilibili_api.api.base import BilibiliCommon

        default_headers = BilibiliCommon._get_default_headers()

        assert default_headers['origin'] == 'https://www.bilibili.com'
        assert default_headers['referer'] == 'https://www.bilibili.com/'

    def test_get_uuid_lazy_cached(self, bilibili_common_state: None) -> None:
        """uuid 惰性初始化并缓存, 多次调用返回同一值"""
        from src.utils.bilibili_api.api.base import BilibiliCommon

        first = BilibiliCommon._get_uuid()
        second = BilibiliCommon._get_uuid()

        assert first == second
        assert first.endswith('infoc')

    def test_get_spm_prefix_fallback(self, bilibili_common_state: None) -> None:
        """未初始化时返回回退值 333.1387"""
        from src.utils.bilibili_api.api.base import BilibiliCommon

        assert BilibiliCommon._get_spm_prefix() == '333.1387'

    async def test_init_spm_prefix_success(
            self, monkeypatch: pytest.MonkeyPatch, bilibili_common_state: None,
    ) -> None:
        from src.utils.bilibili_api.api.base import BilibiliCommon

        get_text_mock = AsyncMock(return_value=_SPM_HTML)
        monkeypatch.setattr(BilibiliCommon, '_get_resource_as_text', get_text_mock)

        assert await BilibiliCommon._init_spm_prefix() == '333.999'
        assert BilibiliCommon._get_spm_prefix() == '333.999'

        # 已初始化后短路, 不再发起请求
        get_text_mock.reset_mock()
        assert await BilibiliCommon._init_spm_prefix() == '333.999'
        get_text_mock.assert_not_awaited()

    async def test_init_spm_prefix_missing_meta(
            self, monkeypatch: pytest.MonkeyPatch, bilibili_common_state: None,
    ) -> None:
        from src.utils.bilibili_api.api.base import BilibiliCommon

        monkeypatch.setattr(BilibiliCommon, '_get_resource_as_text', AsyncMock(return_value=_SPM_HTML_NO_META))

        with pytest.raises(RuntimeError, match='parsing API spm_prefix not found'):
            await BilibiliCommon._init_spm_prefix()

    async def test_init_spm_prefix_empty_content(
            self, monkeypatch: pytest.MonkeyPatch, bilibili_common_state: None,
    ) -> None:
        from src.utils.bilibili_api.api.base import BilibiliCommon

        monkeypatch.setattr(
            BilibiliCommon, '_get_resource_as_text', AsyncMock(return_value=_SPM_HTML_EMPTY_CONTENT)
        )

        with pytest.raises(RuntimeError, match='parsing API spm_prefix failed'):
            await BilibiliCommon._init_spm_prefix()


class TestSignWbiParams:
    """类级 wbi 签名分支测试"""

    async def test_uses_cached_keys(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """凭据中已有 img_key/sub_key 时直接本地签名, 不请求 nav 接口"""
        from src.utils.bilibili_api.api.base import BilibiliCommon
        from src.utils.bilibili_api.misc import wbi

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)

        nav_mock = AsyncMock()
        monkeypatch.setattr(BilibiliCommon, '_sign_wbi_params_nav', nav_mock)
        monkeypatch.setattr(wbi.time, 'time', lambda: _WBI_WTS)

        signed = await BilibiliCommon.sign_wbi_params(params={'foo': 'bar'})

        assert signed['w_rid'] == _WBI_FOO_BAR_W_RID
        nav_mock.assert_not_called()

    async def test_fallback_to_nav(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """凭据缺少 wbi 键时从 nav 接口获取签名参数"""
        from src.utils.bilibili_api.api.base import BilibiliCommon

        manager = credential_manager_sandbox
        manager.clear_cookies()

        get_json_mock = AsyncMock(return_value=_make_nav_payload(0))
        monkeypatch.setattr(BilibiliCommon, '_get_resource_as_json', get_json_mock)

        signed = await BilibiliCommon.sign_wbi_params(params={'foo': 'bar'})

        get_json_mock.assert_awaited_once()
        assert 'w_rid' in signed
        assert 'wts' in signed


class TestTicketWbiCookies:
    """BiliTicket 获取与更新测试"""

    async def test_fetch_ticket_wbi_cookies(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api.api.base import BilibiliCommon

        post_mock = AsyncMock(return_value=_TICKET_PAYLOAD)
        monkeypatch.setattr(BilibiliCommon, '_post_acquire_as_json', post_mock)

        new_cookies = await BilibiliCommon._fetch_ticket_wbi_cookies(bili_jct='jct_value')

        assert new_cookies['bili_ticket'] == 'ticket_value'
        assert new_cookies['bili_ticket_expires'] == _WBI_WTS + 86400
        assert new_cookies['img_key'] == _WBI_KEY_IMG
        assert new_cookies['sub_key'] == _WBI_KEY_SUB
        assert post_mock.call_args.kwargs['params']['csrf'] == 'jct_value'

    async def test_fetch_ticket_wbi_cookies_anonymous(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """未登录 (bili_jct=None) 时 csrf 为空字符串"""
        from src.utils.bilibili_api.api.base import BilibiliCommon

        post_mock = AsyncMock(return_value=_TICKET_PAYLOAD)
        monkeypatch.setattr(BilibiliCommon, '_post_acquire_as_json', post_mock)

        await BilibiliCommon._fetch_ticket_wbi_cookies(bili_jct=None)

        assert post_mock.call_args.kwargs['params']['csrf'] == ''

    async def test_update_ticket_wbi_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """update_ticket_wbi_cookies 将新值写入全局凭据并返回登录用 cookies"""
        from src.utils.bilibili_api.api.base import BilibiliCommon

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(bili_jct='jct_value')

        monkeypatch.setattr(BilibiliCommon, '_post_acquire_as_json', AsyncMock(return_value=_TICKET_PAYLOAD))

        result = await BilibiliCommon.update_ticket_wbi_cookies()

        assert manager.get_cookie('bili_ticket') == 'ticket_value'
        assert manager.get_cookie('img_key') == _WBI_KEY_IMG
        assert result['bili_ticket'] == 'ticket_value'


class TestUpdateBuvidCookies:
    """buvid 激活流程测试 (响应校验必须按 dict 处理, 成功路径不得抛异常)"""

    def _mock_network(self, monkeypatch: pytest.MonkeyPatch, exclimbwuzhi_payload: dict) -> None:
        from src.utils.bilibili_api.api.base import BilibiliCommon

        monkeypatch.setattr(BilibiliCommon, '_init_spm_prefix', AsyncMock(return_value='333.1387'))
        monkeypatch.setattr(BilibiliCommon, '_get_resource_as_json', AsyncMock(return_value=_SPI_PAYLOAD))
        monkeypatch.setattr(
            BilibiliCommon, '_post_acquire_as_json', AsyncMock(return_value=exclimbwuzhi_payload)
        )

    async def test_update_buvid_cookies_success(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
            bilibili_common_state: None,
    ) -> None:
        from src.utils.bilibili_api import BilibiliDynamic

        self._mock_network(monkeypatch, _EXCLIMBWUZHI_SUCCESS_PAYLOAD)
        manager = credential_manager_sandbox
        manager.clear_cookies()

        result = await BilibiliDynamic.update_buvid_cookies()

        assert isinstance(result, dict)
        assert manager.get_cookie('buvid3') == 'buvid3_value'
        assert manager.get_cookie('buvid4') == 'buvid4_value'
        assert manager.get_cookie('buvid_fp') is not None

    async def test_update_buvid_cookies_failure_raises(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
            bilibili_common_state: None,
    ) -> None:
        from src.utils.bilibili_api import BilibiliDynamic

        self._mock_network(monkeypatch, {'code': -400, 'message': 'request error', 'ttl': 1})

        with pytest.raises(RuntimeError, match='active buvid failed'):
            await BilibiliDynamic.update_buvid_cookies()

    async def test_update_buvid_cookies_spm_prefix_failure_degrades(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
            bilibili_common_state: None,
    ) -> None:
        """spm_prefix 刷新失败应降级为回退值, 不应中断 buvid 激活流程"""
        from src.utils.bilibili_api import BilibiliDynamic
        from src.utils.bilibili_api.api.base import BilibiliCommon

        self._mock_network(monkeypatch, _EXCLIMBWUZHI_SUCCESS_PAYLOAD)
        monkeypatch.setattr(
            BilibiliCommon, '_init_spm_prefix', AsyncMock(side_effect=RuntimeError('spm fetch failed'))
        )

        result = await BilibiliDynamic.update_buvid_cookies()

        assert isinstance(result, dict)
        assert credential_manager_sandbox.get_cookie('buvid3') == 'buvid3_value'


class TestGlobalSearch:
    """综合/分类搜索接口测试"""

    async def test_global_search_all(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """综合搜索参数需经 wbi 签名, 结果跨 result_type 打平"""
        from src.utils.bilibili_api.api.base import BilibiliCommon

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)

        get_json_mock = AsyncMock(return_value=_make_search_all_payload())
        monkeypatch.setattr(BilibiliCommon, '_get_resource_as_json', get_json_mock)

        result = await BilibiliCommon.global_search_all(keyword='test')

        params = get_json_mock.call_args.kwargs['params']
        assert params['keyword'] == 'test'
        assert 'w_rid' in params
        assert len(result.all_results) == 1
        assert result.all_results[0].mid == 12345

    async def test_global_search_by_type(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """分类搜索不强制 wbi 签名, 参数原样透传"""
        from src.utils.bilibili_api.api.base import BilibiliCommon

        get_json_mock = AsyncMock(return_value=_SEARCH_TYPE_PAYLOAD)
        monkeypatch.setattr(BilibiliCommon, '_get_resource_as_json', get_json_mock)

        result = await BilibiliCommon.global_search_by_type(search_type='bili_user', keyword='test', page=2)

        assert get_json_mock.call_args.kwargs['params'] == {
            'search_type': 'bili_user', 'keyword': 'test', 'page': 2,
        }
        assert len(result.all_results) == 2


# ------------------------------------------------------------------ #
# api/dynamic.py 测试
# ------------------------------------------------------------------ #


class TestDynamicQueryParams:
    """动态查询请求参数测试 (update_baseline 必须写入正确参数键)"""

    def _mock_request(self, monkeypatch: pytest.MonkeyPatch, payload: dict) -> AsyncMock:
        from src.utils.bilibili_api import BilibiliDynamic
        from src.utils.bilibili_api.api.base import BilibiliCommon

        monkeypatch.setattr(BilibiliCommon, '_init_spm_prefix', AsyncMock(return_value='333.1387'))
        get_json_mock = AsyncMock(return_value=payload)
        monkeypatch.setattr(BilibiliDynamic, '_get_resource_as_json', get_json_mock)
        return get_json_mock

    async def test_update_baseline_param_key(
            self, monkeypatch: pytest.MonkeyPatch, bilibili_common_state: None,
    ) -> None:
        from src.utils.bilibili_api import BilibiliDynamic

        get_json_mock = self._mock_request(monkeypatch, _DYNAMICS_PAYLOAD)

        await BilibiliDynamic.query_my_following_dynamics(type_='video', update_baseline=123456)

        params = get_json_mock.call_args.kwargs['params']
        assert params.get('update_baseline') == '123456'
        assert params.get('type') == 'video'

    async def test_offset_and_baseline_accept_str(
            self, monkeypatch: pytest.MonkeyPatch, bilibili_common_state: None,
    ) -> None:
        """分页参数与模型字段 (str) 对齐, 支持直接回传"""
        from src.utils.bilibili_api import BilibiliDynamic

        get_json_mock = self._mock_request(monkeypatch, _DYNAMICS_PAYLOAD)

        await BilibiliDynamic.query_user_space_dynamics(host_mid=123, offset='offset_str_value')

        params = get_json_mock.call_args.kwargs['params']
        assert params.get('offset') == 'offset_str_value'

    async def test_optional_params_omitted(
            self, monkeypatch: pytest.MonkeyPatch, bilibili_common_state: None,
    ) -> None:
        """缺省参数不应出现在请求参数中"""
        from src.utils.bilibili_api import BilibiliDynamic

        get_json_mock = self._mock_request(monkeypatch, _DYNAMICS_PAYLOAD)

        await BilibiliDynamic.query_my_following_dynamics()

        params = get_json_mock.call_args.kwargs['params']
        assert 'type' not in params
        assert 'host_mid' not in params
        assert 'offset' not in params
        assert 'update_baseline' not in params

    async def test_space_dynamics_params(
            self, monkeypatch: pytest.MonkeyPatch, bilibili_common_state: None,
    ) -> None:
        from src.utils.bilibili_api import BilibiliDynamic

        get_json_mock = self._mock_request(monkeypatch, _DYNAMICS_PAYLOAD)

        await BilibiliDynamic.query_user_space_dynamics(host_mid=123, timezone_offset=-480)

        params = get_json_mock.call_args.kwargs['params']
        assert params.get('host_mid') == '123'
        assert params.get('timezone_offset') == '-480'
        assert 'offset' not in params

    async def test_query_dynamic_detail_params(
            self, monkeypatch: pytest.MonkeyPatch, bilibili_common_state: None,
    ) -> None:
        from src.utils.bilibili_api import BilibiliDynamic

        get_json_mock = self._mock_request(monkeypatch, _DYNAMIC_DETAIL_PAYLOAD)

        detail = await BilibiliDynamic.query_dynamic_detail(id_=1001, timezone_offset=-480)

        params = get_json_mock.call_args.kwargs['params']
        assert params.get('id') == '1001'
        assert params.get('web_location') == '333.1387'
        assert params.get('timezone_offset') == '-480'
        assert 'features' in params
        assert detail.data.item.id_str == '1001'

    async def test_query_dynamic_opus_detail_params(
            self, monkeypatch: pytest.MonkeyPatch, bilibili_common_state: None,
    ) -> None:
        from src.utils.bilibili_api import BilibiliDynamic

        get_json_mock = self._mock_request(monkeypatch, _DYNAMIC_OPUS_DETAIL_PAYLOAD)

        detail = await BilibiliDynamic.query_dynamic_opus_detail(id_=1002)

        params = get_json_mock.call_args.kwargs['params']
        assert params.get('id') == '1002'
        assert 'features' in params
        assert detail.data.item.id_str == '1002'


# ------------------------------------------------------------------ #
# api/live.py 测试
# ------------------------------------------------------------------ #


class TestLiveQueryParams:
    """直播查询请求参数测试"""

    async def test_query_room_info_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api import BilibiliLive

        get_json_mock = AsyncMock(return_value=_ROOM_INFO_PAYLOAD)
        monkeypatch.setattr(BilibiliLive, '_get_resource_as_json', get_json_mock)

        room_info = await BilibiliLive.query_room_info(room_id=1234567)

        assert get_json_mock.call_args.kwargs['params'] == {'room_id': '1234567'}
        assert room_info.data.room_id == '1234567'

    async def test_query_room_info_by_room_id_list_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """批量接口使用重复 room_ids 参数对编码"""
        from src.utils.bilibili_api import BilibiliLive

        get_json_mock = AsyncMock(return_value=_ROOM_BASE_INFO_PAYLOAD)
        monkeypatch.setattr(BilibiliLive, '_get_resource_as_json', get_json_mock)

        base_info = await BilibiliLive.query_room_info_by_room_id_list(room_id_list=[1234567, '890'])

        params = get_json_mock.call_args.kwargs['params']
        assert ('req_biz', 'web_room_componet') in params
        assert ('room_ids', '1234567') in params
        assert ('room_ids', '890') in params
        assert set(base_info.data.by_room_ids.keys()) == {'1234567'}

    async def test_query_room_info_by_uid_list_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """按 uid 批量查询为 POST JSON 载荷且不携带 cookies"""
        from src.utils.bilibili_api import BilibiliLive

        post_mock = AsyncMock(return_value=_USERS_ROOM_INFO_PAYLOAD)
        monkeypatch.setattr(BilibiliLive, '_post_acquire_as_json', post_mock)

        users_info = await BilibiliLive.query_room_info_by_uid_list(uid_list=[2165572, 12345])

        assert post_mock.call_args.kwargs['json'] == {'uids': [2165572, 12345]}
        assert post_mock.call_args.kwargs['no_cookies'] is True
        assert set(users_info.data.keys()) == {2165572, 12345}

    async def test_query_room_user_info_params(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api import BilibiliLive

        get_json_mock = AsyncMock(return_value=_ROOM_USER_INFO_PAYLOAD)
        monkeypatch.setattr(BilibiliLive, '_get_resource_as_json', get_json_mock)

        room_user_info = await BilibiliLive.query_room_user_info(room_id=1234567)

        assert get_json_mock.call_args.kwargs['params'] == {'roomid': '1234567'}
        assert room_user_info.data.info.uid == 2165572
        assert room_user_info.data.san == 12


class TestRoomInfoLiveTime:
    """直播开播时间时区处理测试 (naive 时间应按东八区本地时间解释)"""

    def _make_room_info(self, live_time: str, live_status: int = 1):
        from src.utils.bilibili_api.models.live import RoomInfoData

        return RoomInfoData.model_validate(_make_room_info_dict(live_status=live_status, live_time=live_time))

    def test_naive_live_time_interpreted_as_local_tz(self) -> None:
        data = self._make_room_info('2024-01-01 12:00:00')

        assert isinstance(data.live_time, datetime)
        assert data.live_time.utcoffset() == timedelta(hours=8)
        # 墙钟时间不得发生偏移
        assert (data.live_time.hour, data.live_time.minute) == (12, 0)

    def test_aware_live_time_converted_to_local_tz(self) -> None:
        data = self._make_room_info('2024-01-01T12:00:00+00:00')

        assert isinstance(data.live_time, datetime)
        assert data.live_time.utcoffset() == timedelta(hours=8)
        assert data.live_time.hour == 20

    def test_offline_live_time_passthrough_as_str(self) -> None:
        """未开播时 live_time 为 '0000-00-00 00:00:00', 无法解析为 datetime, 应保持字符串原样"""
        data = self._make_room_info('0000-00-00 00:00:00', live_status=0)

        assert data.live_time == '0000-00-00 00:00:00'


class TestRoomInfoModels:
    """直播数据模型边界测试"""

    def test_cover_url_fallback_chain(self) -> None:
        """cover_url 依次回退: cover -> user_cover -> cover_from_user -> 空字符串"""
        from src.utils.bilibili_api.models.live import RoomInfoData

        data = RoomInfoData.model_validate(_make_room_info_dict(
            cover='https://i0.hdslb.com/bfs/live/cover.jpg',
            user_cover='https://i0.hdslb.com/bfs/live/user_cover.jpg',
            cover_from_user='https://i0.hdslb.com/bfs/live/cover_from_user.jpg',
        ))
        assert data.cover_url == 'https://i0.hdslb.com/bfs/live/cover.jpg'

        data = RoomInfoData.model_validate(_make_room_info_dict(
            user_cover='https://i0.hdslb.com/bfs/live/user_cover.jpg',
            cover_from_user='https://i0.hdslb.com/bfs/live/cover_from_user.jpg',
        ))
        assert data.cover_url == 'https://i0.hdslb.com/bfs/live/user_cover.jpg'

        data = RoomInfoData.model_validate(_make_room_info_dict(
            cover_from_user='https://i0.hdslb.com/bfs/live/cover_from_user.jpg',
        ))
        assert data.cover_url == 'https://i0.hdslb.com/bfs/live/cover_from_user.jpg'

        data = RoomInfoData.model_validate(_make_room_info_dict())
        assert data.cover_url == ''

    def test_users_room_info_int_key_coercion(self) -> None:
        """接口返回的字符串键应被强转为 int"""
        from src.utils.bilibili_api.models.live import UsersRoomInfo

        parsed = UsersRoomInfo.model_validate(_USERS_ROOM_INFO_PAYLOAD)

        assert set(parsed.data.keys()) == {2165572, 12345}

    def test_live_status_values(self) -> None:
        from src.utils.bilibili_api.models.live import LiveStatus

        assert LiveStatus(0) is LiveStatus.offline
        assert LiveStatus(1) is LiveStatus.streaming
        assert LiveStatus(2) is LiveStatus.rotating


# ------------------------------------------------------------------ #
# api/user.py 测试
# ------------------------------------------------------------------ #


class TestMyInfo:
    """我的账户/大会员信息接口测试"""

    async def test_query_my_account_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api.api.user import BilibiliUser

        monkeypatch.setattr(BilibiliUser, '_get_resource_as_json', AsyncMock(return_value=_ACCOUNT_PAYLOAD))

        account = await BilibiliUser.query_my_account_info()

        assert account.data.mid == 2165572
        assert account.data.uname == 'test_uname'
        assert account.data.birthday == '05-05'

    async def test_query_my_vip_info(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api.api.user import BilibiliUser

        monkeypatch.setattr(BilibiliUser, '_get_resource_as_json', AsyncMock(return_value=_VIP_PAYLOAD))

        vip = await BilibiliUser.query_my_vip_info()

        assert vip.data.mid == 2165572
        assert vip.data.vip_type == 2


class TestUserSpaceRenderData:
    """用户空间页 __RENDER_DATA__ 解析测试"""

    async def test_parse_success(self) -> None:
        from src.utils.bilibili_api.api.user import BilibiliUser

        render_data = await BilibiliUser._parse_user_space_w_webid(content=_USER_SPACE_HTML)

        assert render_data.access_id == 'access_id_value'

    async def test_parse_missing_node(self) -> None:
        from src.utils.bilibili_api.api.user import BilibiliUser

        with pytest.raises(RuntimeError, match='parsing user render_data not found'):
            await BilibiliUser._parse_user_space_w_webid(content='<html><head></head><body></body></html>')

    async def test_parse_empty_text(self) -> None:
        from src.utils.bilibili_api.api.user import BilibiliUser

        with pytest.raises(RuntimeError, match='parsing user render_data failed'):
            await BilibiliUser._parse_user_space_w_webid(
                content='<html><head><script id="__RENDER_DATA__"></script></head><body></body></html>'
            )


class TestQueryUserInfo:
    """用户信息查询测试 (w_webid 注入与降级)"""

    async def test_with_w_webid(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """RENDER_DATA 可用时请求参数包含 w_webid 与 wbi 签名"""
        from src.utils.bilibili_api.api.user import BilibiliUser
        from src.utils.bilibili_api.models import UserSpaceRenderData

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)

        monkeypatch.setattr(
            BilibiliUser,
            '_query_user_space_w_webid',
            AsyncMock(return_value=UserSpaceRenderData.model_validate({'access_id': 'access_id_value'})),
        )
        get_json_mock = AsyncMock(return_value=_USER_PAYLOAD)
        monkeypatch.setattr(BilibiliUser, '_get_resource_as_json', get_json_mock)

        user = await BilibiliUser.query_user_info(mid=12345)

        params = get_json_mock.call_args.kwargs['params']
        assert params['mid'] == '12345'
        assert params['w_webid'] == 'access_id_value'
        assert 'w_rid' in params
        assert user.data.mid == 12345
        assert user.uname == 'test_up'

    async def test_render_data_failure_degrades(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """RENDER_DATA 获取失败时降级为无 w_webid 请求, 不中断查询"""
        from src.utils.bilibili_api.api.user import BilibiliUser

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(img_key=_WBI_KEY_IMG, sub_key=_WBI_KEY_SUB)

        monkeypatch.setattr(
            BilibiliUser,
            '_query_user_space_w_webid',
            AsyncMock(side_effect=RuntimeError('render data missing')),
        )
        get_json_mock = AsyncMock(return_value=_USER_PAYLOAD)
        monkeypatch.setattr(BilibiliUser, '_get_resource_as_json', get_json_mock)

        user = await BilibiliUser.query_user_info(mid=12345)

        params = get_json_mock.call_args.kwargs['params']
        assert 'w_webid' not in params
        assert user.data.mid == 12345


class TestSearchUser:
    """用户搜索测试"""

    async def test_filters_mixed_results(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """search_user 应从混合类型结果中过滤出 UserSearchResult"""
        from src.utils.bilibili_api.api.user import BilibiliUser
        from src.utils.bilibili_api.models import SearchTypeResult

        monkeypatch.setattr(
            BilibiliUser,
            'global_search_by_type',
            AsyncMock(return_value=SearchTypeResult.model_validate(_SEARCH_TYPE_PAYLOAD)),
        )

        results = await BilibiliUser.search_user(keyword='test')

        assert len(results) == 1
        assert results[0].mid == 12345
        assert results[0].uname == 'test_up'


# ------------------------------------------------------------------ #
# api/login.py 测试
# ------------------------------------------------------------------ #


class TestCheckValid:
    """登录验证测试 (仅明确的未登录语义才清除凭据, 风控等临时状态码保留凭据)"""

    def _mock_nav(self, monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        monkeypatch.setattr(BilibiliCredential, '_get_resource_as_json', AsyncMock(return_value=payload))

    async def test_risk_control_code_keeps_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value', bili_jct='jct_value', DedeUserID='12345')
        self._mock_nav(monkeypatch, _make_nav_payload(-412))

        result = await BilibiliCredential.check_valid()

        assert result is False
        assert manager.get_cookie('DedeUserID') == '12345'

    async def test_not_logged_in_clears_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value', bili_jct='jct_value', DedeUserID='12345')
        self._mock_nav(monkeypatch, _make_nav_payload(0, is_login=False))

        result = await BilibiliCredential.check_valid()

        assert result is False
        assert manager.get_cookie('DedeUserID') is None

    async def test_code_minus_101_clears_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value', bili_jct='jct_value', DedeUserID='12345')
        self._mock_nav(monkeypatch, _make_nav_payload(-101))

        result = await BilibiliCredential.check_valid()

        assert result is False
        assert manager.get_cookie('DedeUserID') is None

    async def test_mid_mismatch_clears_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value', bili_jct='jct_value', DedeUserID='12345')
        self._mock_nav(monkeypatch, _make_nav_payload(0, mid='99999'))

        result = await BilibiliCredential.check_valid()

        assert result is False
        assert manager.get_cookie('DedeUserID') is None

    async def test_valid_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value', bili_jct='jct_value', DedeUserID='12345')
        self._mock_nav(monkeypatch, _make_nav_payload(0))

        result = await BilibiliCredential.check_valid()

        assert result is True
        assert manager.get_cookie('DedeUserID') == '12345'

    async def test_request_failure_keeps_cookies(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """请求异常 (网络错误/响应解析失败) 返回 False 且保留凭据"""
        from src.utils.bilibili_api import BilibiliCredential

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='sess_value', bili_jct='jct_value', DedeUserID='12345')
        monkeypatch.setattr(
            BilibiliCredential, '_get_resource_as_json', AsyncMock(side_effect=RuntimeError('network error'))
        )

        result = await BilibiliCredential.check_valid()

        assert result is False
        assert manager.get_cookie('DedeUserID') == '12345'


class TestCheckNeedRefresh:
    """刷新必要性检查测试"""

    async def test_no_bili_jct_needs_refresh(
            self, credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        credential_manager_sandbox.clear_cookies()

        assert await BilibiliCredential.check_need_refresh() is True

    async def test_api_error_returns_false(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """cookie/info 接口返回异常 code 时视为无需刷新"""
        from src.utils.bilibili_api import BilibiliCredential

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(bili_jct='jct_value')
        monkeypatch.setattr(
            BilibiliCredential,
            '_get_resource_as_json',
            AsyncMock(return_value={'code': -101, 'message': '账号未登录', 'ttl': 1}),
        )

        assert await BilibiliCredential.check_need_refresh() is False

    async def test_refresh_flag_true(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(bili_jct='jct_value')
        get_json_mock = AsyncMock(return_value=_COOKIE_INFO_PAYLOAD)
        monkeypatch.setattr(BilibiliCredential, '_get_resource_as_json', get_json_mock)

        assert await BilibiliCredential.check_need_refresh() is True
        assert get_json_mock.call_args.kwargs['params'] == {'csrf': 'jct_value'}

    async def test_refresh_flag_false(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(bili_jct='jct_value')
        payload = {'code': 0, 'message': '0', 'ttl': 1, 'data': {'refresh': False, 'timestamp': 1700000000000}}
        monkeypatch.setattr(BilibiliCredential, '_get_resource_as_json', AsyncMock(return_value=payload))

        assert await BilibiliCredential.check_need_refresh() is False


class TestGetRefreshCsrf:
    """refresh_csrf 页面解析测试"""

    def _mock_correspond(self, monkeypatch: pytest.MonkeyPatch, html: str) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        # get_refresh_csrf 内含固定的 asyncio.sleep 等待, 测试中跳过
        monkeypatch.setattr(asyncio, 'sleep', AsyncMock())
        monkeypatch.setattr(BilibiliCredential, '_get_resource_as_text', AsyncMock(return_value=html))

    async def test_parse_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        self._mock_correspond(monkeypatch, _REFRESH_CSRF_HTML)

        assert await BilibiliCredential.get_refresh_csrf() == 'refresh_csrf_value'

    async def test_parse_missing_node(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        self._mock_correspond(monkeypatch, _REFRESH_CSRF_HTML_NO_DIV)

        with pytest.raises(RuntimeError, match='parsing API refresh_csrf not found'):
            await BilibiliCredential.get_refresh_csrf()

    async def test_parse_empty_text(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        self._mock_correspond(monkeypatch, _REFRESH_CSRF_HTML_EMPTY)

        with pytest.raises(RuntimeError, match='parsing API refresh_csrf failed'):
            await BilibiliCredential.get_refresh_csrf()


class TestGetCorrespondPath:
    """CorrespondPath 生成测试"""

    def test_correspond_path_format(self) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        path = BilibiliCredential._get_correspond_path()

        # RSA-1024 加密输出 128 字节, hex 编码后为 256 个十六进制字符
        assert re.fullmatch(r'[0-9a-f]{256}', path)


class TestConfirmCookiesRefresh:
    """确认刷新请求参数测试"""

    async def test_params_shape(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        post_mock = AsyncMock(return_value={'code': 0, 'message': '0', 'ttl': 1})
        monkeypatch.setattr(BilibiliCredential, '_post_acquire_as_json', post_mock)

        await BilibiliCredential.confirm_cookies_refresh(csrf='csrf_value', refresh_token='rt_value')

        assert post_mock.call_args.kwargs['params'] == {'csrf': 'csrf_value', 'refresh_token': 'rt_value'}

    async def test_none_refresh_token_becomes_empty_str(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        post_mock = AsyncMock(return_value={'code': 0, 'message': '0', 'ttl': 1})
        monkeypatch.setattr(BilibiliCredential, '_post_acquire_as_json', post_mock)

        await BilibiliCredential.confirm_cookies_refresh(csrf='csrf_value', refresh_token=None)

        assert post_mock.call_args.kwargs['params']['refresh_token'] == ''


class TestRefreshCookies:
    """凭据刷新流程测试 (先算后换, 成功一次性替换, 失败全局凭据保持原状)"""

    def _mock_refresh_pipeline(
            self,
            monkeypatch: pytest.MonkeyPatch,
            *,
            refresh_payload: dict | None = None,
            confirm_code: int = 0,
            buvid_side_effect: Exception | None = None,
            set_cookies: dict | None = None,
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.api.base import BilibiliCommon
        from src.utils.bilibili_api.models import WebConfirmRefreshInfo

        monkeypatch.setattr(BilibiliCommon, '_init_spm_prefix', AsyncMock(return_value='333.1387'))
        monkeypatch.setattr(BilibiliCredential, 'get_refresh_csrf', AsyncMock(return_value='refresh_csrf_value'))
        monkeypatch.setattr(BilibiliCredential, '_request_post', AsyncMock(return_value=MagicMock()))
        monkeypatch.setattr(
            BilibiliCredential,
            '_parse_content_as_json',
            MagicMock(return_value=refresh_payload or _REFRESH_SUCCESS_PAYLOAD),
        )
        monkeypatch.setattr(
            BilibiliCredential,
            '_extra_set_cookies_from_response',
            MagicMock(return_value=set_cookies or {'SESSDATA': 'new_sess', 'bili_jct': 'new_jct',
                                                   'DedeUserID': '12345'}),
        )
        monkeypatch.setattr(
            BilibiliCommon,
            '_fetch_ticket_wbi_cookies',
            AsyncMock(return_value={
                'bili_ticket': 'ticket_value',
                'bili_ticket_expires': 1700000000,
                'img_key': 'img_key_value',
                'sub_key': 'sub_key_value',
            }),
        )
        monkeypatch.setattr(
            BilibiliCommon,
            '_fetch_buvid_cookies',
            AsyncMock(
                return_value={'buvid3': 'b3', 'buvid4': 'b4'},
                side_effect=buvid_side_effect,
            ),
        )
        monkeypatch.setattr(
            BilibiliCredential,
            'confirm_cookies_refresh',
            AsyncMock(return_value=WebConfirmRefreshInfo.model_validate(
                {'code': confirm_code, 'message': f'code_{confirm_code}', 'ttl': 1}
            )),
        )

    def _prepare_manager(self, manager: '_BilibiliCredentialManager') -> None:
        manager.clear_cookies()
        manager.update_cookies(
            SESSDATA='old_sess', bili_jct='old_jct', DedeUserID='12345', ac_time_value='old_rt'
        )

    def _assert_manager_unchanged(self, manager: '_BilibiliCredentialManager') -> None:
        assert manager.get_cookie('SESSDATA') == 'old_sess'
        assert manager.get_cookie('bili_jct') == 'old_jct'
        assert manager.get_cookie('ac_time_value') == 'old_rt'
        assert manager.get_cookie('img_key') is None
        assert manager.get_cookie('buvid3') is None

    async def test_refresh_success_swaps_atomically(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.credential_manager import _BilibiliCredentialManager

        self._mock_refresh_pipeline(monkeypatch)
        rebuild_mock = AsyncMock()
        monkeypatch.setattr(_BilibiliCredentialManager, 'rebuild_to_database', rebuild_mock)
        monkeypatch.setattr(BilibiliCredential, 'check_valid', AsyncMock(return_value=True))

        manager = credential_manager_sandbox
        self._prepare_manager(manager)

        result = await BilibiliCredential.refresh_cookies()

        assert result is True
        assert manager.get_cookie('SESSDATA') == 'new_sess'
        assert manager.get_cookie('bili_jct') == 'new_jct'
        assert manager.get_cookie('ac_time_value') == 'new_rt'
        assert manager.get_cookie('img_key') == 'img_key_value'
        assert manager.get_cookie('buvid3') == 'b3'
        rebuild_mock.assert_awaited_once()

    async def test_refresh_failure_keeps_manager_untouched(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """中间步骤异常: 返回 False 且全局凭据不变, 不落库"""
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.credential_manager import _BilibiliCredentialManager

        self._mock_refresh_pipeline(monkeypatch, buvid_side_effect=RuntimeError('buvid activate failed'))
        rebuild_mock = AsyncMock()
        monkeypatch.setattr(_BilibiliCredentialManager, 'rebuild_to_database', rebuild_mock)

        manager = credential_manager_sandbox
        self._prepare_manager(manager)

        result = await BilibiliCredential.refresh_cookies()

        assert result is False
        self._assert_manager_unchanged(manager)
        rebuild_mock.assert_not_awaited()

    async def test_confirm_failure_keeps_manager_untouched(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """确认更新失败: 返回 False 且全局凭据不变, 不落库"""
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.credential_manager import _BilibiliCredentialManager

        self._mock_refresh_pipeline(monkeypatch, confirm_code=-400)
        rebuild_mock = AsyncMock()
        monkeypatch.setattr(_BilibiliCredentialManager, 'rebuild_to_database', rebuild_mock)

        manager = credential_manager_sandbox
        self._prepare_manager(manager)

        result = await BilibiliCredential.refresh_cookies()

        assert result is False
        self._assert_manager_unchanged(manager)
        rebuild_mock.assert_not_awaited()

    async def test_refresh_code_nonzero_keeps_manager_untouched(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """刷新接口返回异常 code: 返回 False 且全局凭据不变"""
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.credential_manager import _BilibiliCredentialManager

        self._mock_refresh_pipeline(monkeypatch, refresh_payload={
            'code': -101, 'message': '账号未登录', 'ttl': 1,
            'data': {'status': -101, 'message': '账号未登录', 'refresh_token': ''},
        })
        rebuild_mock = AsyncMock()
        monkeypatch.setattr(_BilibiliCredentialManager, 'rebuild_to_database', rebuild_mock)

        manager = credential_manager_sandbox
        self._prepare_manager(manager)

        result = await BilibiliCredential.refresh_cookies()

        assert result is False
        self._assert_manager_unchanged(manager)
        rebuild_mock.assert_not_awaited()

    async def test_missing_bili_jct_in_set_cookies_keeps_manager_untouched(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """set-cookies 缺少 bili_jct: 确认步骤取键失败被捕获, 返回 False 且全局凭据不变"""
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.credential_manager import _BilibiliCredentialManager

        self._mock_refresh_pipeline(monkeypatch, set_cookies={'SESSDATA': 'new_sess'})
        rebuild_mock = AsyncMock()
        monkeypatch.setattr(_BilibiliCredentialManager, 'rebuild_to_database', rebuild_mock)

        manager = credential_manager_sandbox
        self._prepare_manager(manager)

        result = await BilibiliCredential.refresh_cookies()

        assert result is False
        self._assert_manager_unchanged(manager)
        rebuild_mock.assert_not_awaited()


class TestLoginWithQrcode:
    """扫码登录流程测试"""

    def _mock_login_pipeline(
            self,
            monkeypatch: pytest.MonkeyPatch,
            poll_results: list,
    ) -> AsyncMock:
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.credential_manager import _BilibiliCredentialManager

        check_mock = AsyncMock(side_effect=poll_results)
        monkeypatch.setattr(BilibiliCredential, 'check_qrcode_login', check_mock)
        # 轮询间隔固定 asyncio.sleep(6), 测试中跳过
        monkeypatch.setattr(asyncio, 'sleep', AsyncMock())
        monkeypatch.setattr(_BilibiliCredentialManager, 'rebuild_to_database', AsyncMock())
        monkeypatch.setattr(BilibiliCredential, 'check_valid', AsyncMock(return_value=True))
        return check_mock

    async def test_login_success_uses_rebuild(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """登录成功后重建数据库系列并写入新凭据"""
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.credential_manager import _BilibiliCredentialManager
        from src.utils.bilibili_api.models import WebQrcodeGenerateInfo, WebQrcodePollInfo

        poll_info = WebQrcodePollInfo.model_validate(_QRCODE_POLL_SUCCESS_PAYLOAD)
        self._mock_login_pipeline(
            monkeypatch,
            [(poll_info, {'SESSDATA': 'login_sess', 'bili_jct': 'jct', 'DedeUserID': '12345'})],
        )
        rebuild_mock = AsyncMock()
        monkeypatch.setattr(_BilibiliCredentialManager, 'rebuild_to_database', rebuild_mock)

        manager = credential_manager_sandbox
        manager.clear_cookies()
        manager.update_cookies(SESSDATA='stale_sess')

        qrcode_info = WebQrcodeGenerateInfo.model_validate(_QRCODE_GENERATE_PAYLOAD)
        result = await BilibiliCredential.login_with_qrcode(qrcode_info=qrcode_info)

        assert result is True
        rebuild_mock.assert_awaited_once()
        assert manager.get_cookie('SESSDATA') == 'login_sess'
        assert manager.get_cookie('ac_time_value') == 'login_rt'

    async def test_retry_then_success(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """86101 待扫码重试后登录成功"""
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.models import WebQrcodeGenerateInfo, WebQrcodePollInfo

        pending_info = WebQrcodePollInfo.model_validate(_QRCODE_POLL_PENDING_PAYLOAD)
        success_info = WebQrcodePollInfo.model_validate(_QRCODE_POLL_SUCCESS_PAYLOAD)
        check_mock = self._mock_login_pipeline(
            monkeypatch,
            [
                (pending_info, {}),
                (pending_info, {}),
                (success_info, {'SESSDATA': 'login_sess', 'bili_jct': 'jct', 'DedeUserID': '12345'}),
            ],
        )

        credential_manager_sandbox.clear_cookies()

        qrcode_info = WebQrcodeGenerateInfo.model_validate(_QRCODE_GENERATE_PAYLOAD)
        result = await BilibiliCredential.login_with_qrcode(qrcode_info=qrcode_info)

        assert result is True
        assert check_mock.await_count == 3

    async def test_expired_qrcode_raises(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """86038 二维码过期应立即抛出异常"""
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.models import WebQrcodeGenerateInfo, WebQrcodePollInfo

        expired_info = WebQrcodePollInfo.model_validate(_QRCODE_POLL_EXPIRED_PAYLOAD)
        self._mock_login_pipeline(monkeypatch, [(expired_info, {})])

        credential_manager_sandbox.clear_cookies()

        qrcode_info = WebQrcodeGenerateInfo.model_validate(_QRCODE_GENERATE_PAYLOAD)
        with pytest.raises(RuntimeError, match='登录二维码过期'):
            await BilibiliCredential.login_with_qrcode(qrcode_info=qrcode_info)

    async def test_wait_timeout_raises(
            self,
            monkeypatch: pytest.MonkeyPatch,
            credential_manager_sandbox: '_BilibiliCredentialManager',
    ) -> None:
        """持续未扫码超过尝试上限 (attempt >= 15) 应抛出等待超时异常, 共发起 16 次轮询"""
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.models import WebQrcodeGenerateInfo, WebQrcodePollInfo

        pending_info = WebQrcodePollInfo.model_validate(_QRCODE_POLL_PENDING_PAYLOAD)
        check_mock = self._mock_login_pipeline(monkeypatch, [(pending_info, {})] * 16)

        credential_manager_sandbox.clear_cookies()

        qrcode_info = WebQrcodeGenerateInfo.model_validate(_QRCODE_GENERATE_PAYLOAD)
        with pytest.raises(RuntimeError, match='等待超时'):
            await BilibiliCredential.login_with_qrcode(qrcode_info=qrcode_info)

        assert check_mock.await_count == 16


class TestMakeQrcode:
    """登录二维码图片生成测试 (真实写临时文件, 用例内清理)"""

    async def test_make_qrcode_file(self) -> None:
        from src.utils.bilibili_api import BilibiliCredential

        qrcode_file = await BilibiliCredential._make_qrcode('https://passport.bilibili.com/test')
        try:
            assert qrcode_file.is_file
            assert qrcode_file.suffix == '.png'
        finally:
            qrcode_file.remove()

    async def test_generate_login_qrcode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """generate_login_qrcode 以 qrcode url 为内容委托 _make_qrcode"""
        from src.utils.bilibili_api import BilibiliCredential
        from src.utils.bilibili_api.models import WebQrcodeGenerateInfo

        make_mock = AsyncMock(return_value='qrcode_file_value')
        monkeypatch.setattr(BilibiliCredential, '_make_qrcode', make_mock)

        qrcode_info = WebQrcodeGenerateInfo.model_validate(_QRCODE_GENERATE_PAYLOAD)
        result = await BilibiliCredential.generate_login_qrcode(qrcode_info=qrcode_info)

        make_mock.assert_awaited_once_with(_QRCODE_GENERATE_PAYLOAD['data']['url'])
        assert result == 'qrcode_file_value'


_LIVE_REQUEST_INTERVAL = 1.5
"""真实请求间隔秒数, 防频控"""


@pytest.fixture(scope='class')
async def live_dynamic_state() -> SimpleNamespace:
    """真实动态接口验证的共享状态: 加载凭据并校验登录, 未配置或失效则跳过整类用例

    仅读取数据库 (load_from_database), 不执行任何凭据写入/轮换
    """
    from src.utils.bilibili_api.api.login import BilibiliCredential
    from src.utils.bilibili_api.credential_manager import BILIBILI_CREDENTIAL_MANAGER

    await BILIBILI_CREDENTIAL_MANAGER.load_from_database()
    if BILIBILI_CREDENTIAL_MANAGER.get_cookie('SESSDATA') is None:
        pytest.skip('数据库中未配置 bilibili 登录 Cookies, 跳过真实请求验证')
    if not await BilibiliCredential.check_valid():
        pytest.skip('Cookies 已失效或触发风控, 跳过真实请求验证')

    return SimpleNamespace(feed=None, harvested=[])


class TestBilibiliDynamicLive:
    """BilibiliDynamic 真实请求验证 (需数据库中已登录 Cookies)

    本类用例发起真实 bilibili API 请求, 仅应以
    `pytest tests/test_003_web/test_003_bilibili_api.py -k TestBilibiliDynamicLive -v -s` 单独运行
    """

    @staticmethod
    def _smoke_items(items) -> Counter:
        """逐项访问模型派生属性 (暴露 union 分支解析缺口), 并返回动态类型分布"""
        type_counter = Counter()
        for item in items:
            type_counter[str(item.type)] += 1
            _ = item.modules.module_author.mid
            _ = item.modules.module_author.pub_ts
            _ = item.modules.pub_text
            _ = item.modules.dyn_text
            _ = item.modules.dyn_image_urls
        return type_counter

    async def test_query_my_following_dynamics(self, live_dynamic_state: SimpleNamespace) -> None:
        """关注动态 feed 默认参数验证"""
        from src.utils.bilibili_api import BilibiliDynamic

        try:
            feed = await BilibiliDynamic.query_my_following_dynamics()
        except ValidationError as e:
            pytest.fail(f'关注动态 feed 响应模型验证失败 (模型过时或未登录): \n{e}')

        assert not feed.error, f'feed 接口返回异常: code={feed.code}, message={feed.message}'
        assert feed.data.items, '关注动态 feed 为空, 无法验证模型 (账号可能无关注更新)'

        type_counter = self._smoke_items(feed.data.items)
        print(f'feed/all 类型分布: {dict(type_counter)}')  # noqa: T201 用例诊断输出
        first = feed.data.items[0]
        print(f'feed/all 首条: [{first.type}] {first.modules.module_author.name}: '  # noqa: T201 用例诊断输出
              f'{first.modules.dyn_text[:80]!r}')

        assert all(item.id_str for item in feed.data.items)
        live_dynamic_state.feed = feed
        live_dynamic_state.harvested.extend(
            (item.id_str, str(item.type), item.modules.module_author.mid) for item in feed.data.items
        )

    async def test_query_my_following_dynamics_type_filter(self, live_dynamic_state: SimpleNamespace) -> None:
        """关注动态 feed 类型过滤参数验证"""
        from src.utils.bilibili_api import BilibiliDynamic
        from src.utils.bilibili_api.models.dynamic import DynamicType

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            feed = await BilibiliDynamic.query_my_following_dynamics(type_='video')
        except ValidationError as e:
            pytest.fail(f'type=video feed 响应模型验证失败: \n{e}')

        assert not feed.error, f'type=video feed 接口返回异常: code={feed.code}, message={feed.message}'
        if not feed.data.items:
            print('type=video feed 为空, 跳过类型断言')  # noqa: T201 用例诊断输出
        else:
            assert all(x.type == DynamicType.av for x in feed.data.items), (
                f'type=video 过滤后仍存在非视频动态: '
                f'{[str(x.type) for x in feed.data.items if x.type != DynamicType.av]}'
            )
        self._smoke_items(feed.data.items)

    async def test_query_my_following_dynamics_pagination(self, live_dynamic_state: SimpleNamespace) -> None:
        """关注动态 feed 分页回传验证 (offset/update_baseline 参数键真实接口行为)"""
        from src.utils.bilibili_api import BilibiliDynamic

        feed = live_dynamic_state.feed
        assert feed is not None, '依赖 test_query_my_following_dynamics 的 feed 数据'
        offset, update_baseline = feed.data.offset, feed.data.update_baseline
        assert offset or update_baseline, '首页未返回分页参数'

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            next_feed = await BilibiliDynamic.query_my_following_dynamics(
                offset=offset, update_baseline=update_baseline
            )
        except ValidationError as e:
            pytest.fail(f'分页 feed 响应模型验证失败: \n{e}')

        assert not next_feed.error, (
            f'分页 feed 接口返回异常: code={next_feed.code}, message={next_feed.message}'
        )
        first_ids = {x.id_str for x in feed.data.items}
        next_ids = {x.id_str for x in next_feed.data.items}
        print(f'feed/all 分页: 首页 {len(first_ids)} 条, 次页 {len(next_ids)} 条, '  # noqa: T201 用例诊断输出
              f'重叠 {len(first_ids & next_ids)} 条, offset={offset!r}, update_baseline={update_baseline!r}')
        assert next_ids != first_ids, 'offset 分页回传后内容与首页完全相同, offset 参数可能未生效'
        self._smoke_items(next_feed.data.items)

    async def test_query_user_space_dynamics(self, live_dynamic_state: SimpleNamespace) -> None:
        """用户空间动态验证 (含 offset 分页回传)"""
        from src.utils.bilibili_api import BilibiliDynamic

        assert live_dynamic_state.harvested, '依赖 test_query_my_following_dynamics 采收的 host_mid'
        host_mid = live_dynamic_state.harvested[0][2]

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            space_feed = await BilibiliDynamic.query_user_space_dynamics(host_mid=host_mid)
        except ValidationError as e:
            pytest.fail(f'用户空间动态响应模型验证失败: \n{e}')

        assert not space_feed.error, (
            f'空间动态接口返回异常 (mid={host_mid}): code={space_feed.code}, message={space_feed.message}'
        )
        assert space_feed.data.items, f'用户 {host_mid} 空间动态为空'

        type_counter = self._smoke_items(space_feed.data.items)
        print(f'feed/space 类型分布 (mid={host_mid}): {dict(type_counter)}')  # noqa: T201 用例诊断输出
        live_dynamic_state.harvested.extend(
            (item.id_str, str(item.type), host_mid) for item in space_feed.data.items
        )

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            next_feed = await BilibiliDynamic.query_user_space_dynamics(
                host_mid=host_mid, offset=space_feed.data.offset
            )
        except ValidationError as e:
            pytest.fail(f'空间动态分页响应模型验证失败: \n{e}')

        assert not next_feed.error, (
            f'空间动态分页接口返回异常 (mid={host_mid}): code={next_feed.code}, message={next_feed.message}'
        )
        first_ids = {x.id_str for x in space_feed.data.items}
        next_ids = {x.id_str for x in next_feed.data.items}
        assert next_ids != first_ids, '空间动态 offset 分页回传后内容与首页完全相同, offset 参数可能未生效'
        self._smoke_items(next_feed.data.items)

    async def test_query_dynamic_detail(self, live_dynamic_state: SimpleNamespace) -> None:
        """动态详情验证 (按不同动态类型各取首条, 覆盖尽可能多的 union 分支)"""
        from src.utils.bilibili_api import BilibiliDynamic

        picked: dict[str, str] = {}
        for id_str, dyn_type, _mid in live_dynamic_state.harvested:
            picked.setdefault(dyn_type, id_str)
        assert picked, '无可用的动态 id 采收结果'

        for dyn_type, dyn_id in list(picked.items())[:6]:
            await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
            try:
                detail = await BilibiliDynamic.query_dynamic_detail(id_=dyn_id)
            except ValidationError as e:
                pytest.fail(f'动态详情响应模型验证失败 (type={dyn_type}, id={dyn_id}): \n{e}')

            assert not detail.error, (
                f'动态详情接口返回异常 (type={dyn_type}, id={dyn_id}): '
                f'code={detail.code}, message={detail.message}'
            )
            assert detail.data.item.id_str == dyn_id
            self._smoke_items([detail.data.item])
            print(f'动态详情验证通过: type={dyn_type}, id={dyn_id}')  # noqa: T201 用例诊断输出


@pytest.fixture(scope='class')
async def live_room_state() -> SimpleNamespace:
    """真实直播接口验证的共享状态: 采收候选 (room_id, uid), 无候选则跳过整类用例

    凭据仅读取 (load_from_database); 直播端点匿名可用, 登录失效不阻断本类用例
    采收来源: 关注动态的 LIVE_RCMD 项 -> 直播间搜索兜底
    """
    from src.utils.bilibili_api import BilibiliDynamic, BilibiliLive
    from src.utils.bilibili_api.credential_manager import BILIBILI_CREDENTIAL_MANAGER
    from src.utils.bilibili_api.models.dynamic import DynamicType, ModuleDynamicMajorLiveRcmd
    from src.utils.bilibili_api.models.search import LiveRoomSearchResult

    await BILIBILI_CREDENTIAL_MANAGER.load_from_database()

    rooms: list[tuple[int, int]] = []
    if BILIBILI_CREDENTIAL_MANAGER.get_cookie('SESSDATA') is not None:
        try:
            feed = await BilibiliDynamic.query_my_following_dynamics()
            for item in feed.data.items:
                major = item.modules.module_dynamic.major
                if item.type == DynamicType.live_rcmd and isinstance(major, ModuleDynamicMajorLiveRcmd):
                    play_info = major.live_rcmd.content.live_play_info
                    rooms.append((play_info.room_id, play_info.uid))
        except Exception as e:
            print(f'feed 采收直播房间失败, 将尝试搜索兜底: {e}')  # noqa: T201 用例诊断输出

    if not rooms:
        try:
            await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
            search_result = await BilibiliLive.global_search_by_type(search_type='live_room', keyword='英雄联盟')
            for result in search_result.all_results:
                if isinstance(result, LiveRoomSearchResult) and result.live_status == 1:
                    rooms.append((result.roomid, result.uid))
        except Exception as e:
            print(f'搜索兜底采收直播房间失败: {e}')  # noqa: T201 用例诊断输出

    unique_rooms = list(dict.fromkeys(rooms))[:5]
    if not unique_rooms:
        pytest.skip('无可用的真实直播间候选 (feed 无 LIVE_RCMD 且搜索兜底失败), 跳过真实请求验证')

    print(f'直播验证候选房间: {unique_rooms}')  # noqa: T201 用例诊断输出
    return SimpleNamespace(rooms=unique_rooms)


class TestBilibiliLiveLive:
    """BilibiliLive 真实请求验证 (直播端点匿名可用, 凭据仅用于降低风控概率)

    本类用例发起真实 bilibili API 请求, 仅应以
    `pytest tests/test_003_web/test_003_bilibili_api.py -k TestBilibiliLiveLive -v -s` 单独运行
    """

    async def test_query_room_info(self, live_room_state: SimpleNamespace) -> None:
        """单个直播间信息验证 (含 live_time 时区/离线形态)"""
        from src.utils.bilibili_api import BilibiliLive
        from src.utils.bilibili_api.models.live import LiveStatus

        for room_id, _uid in live_room_state.rooms[:3]:
            await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
            try:
                room_info = await BilibiliLive.query_room_info(room_id=room_id)
            except ValidationError as e:
                pytest.fail(f'直播间信息响应模型验证失败 (room_id={room_id}): \n{e}')

            assert not room_info.error, (
                f'直播间信息接口返回异常 (room_id={room_id}): code={room_info.code}, message={room_info.message}'
            )
            data = room_info.data
            assert str(data.room_id) == str(room_id)
            assert data.uname, f'直播间 {room_id} 主播名为空'
            assert data.title, f'直播间 {room_id} 标题为空'
            print(f'直播间 {room_id}: {data.uname} - {data.title!r}, '  # noqa: T201 用例诊断输出
                  f'状态: {data.live_status.name}, live_time={data.live_time!r}')

            if data.live_status == LiveStatus.streaming:
                assert isinstance(data.live_time, datetime)
                assert data.live_time.utcoffset() == timedelta(hours=8)
            _ = data.cover_url

    async def test_query_room_info_by_room_id_list(self, live_room_state: SimpleNamespace) -> None:
        """批量直播间信息验证 (重复 room_ids 参数编码)"""
        from src.utils.bilibili_api import BilibiliLive

        room_ids = [room_id for room_id, _ in live_room_state.rooms]

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            base_info = await BilibiliLive.query_room_info_by_room_id_list(room_id_list=room_ids)
        except ValidationError as e:
            pytest.fail(f'批量直播间信息响应模型验证失败 (room_ids={room_ids}): \n{e}')

        assert not base_info.error, (
            f'批量直播间信息接口返回异常: code={base_info.code}, message={base_info.message}'
        )
        assert set(base_info.data.by_room_ids.keys()) == {str(x) for x in room_ids}
        for key, room_data in base_info.data.by_room_ids.items():
            assert str(room_data.room_id) == key
            _ = room_data.cover_url
        print(f'批量直播间信息验证通过: {list(base_info.data.by_room_ids.keys())}')  # noqa: T201 用例诊断输出

    async def test_query_room_info_by_uid_list(self, live_room_state: SimpleNamespace) -> None:
        """按 uid 列表批量获取直播间信息验证 (POST, 无凭据, 键 coercion)"""
        from src.utils.bilibili_api import BilibiliLive

        uids = [uid for _, uid in live_room_state.rooms]

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            users_room_info = await BilibiliLive.query_room_info_by_uid_list(uid_list=uids)
        except ValidationError as e:
            pytest.fail(f'uid 批量直播间信息响应模型验证失败 (uids={uids}): \n{e}')

        assert not users_room_info.error, (
            f'uid 批量直播间信息接口返回异常: code={users_room_info.code}, message={users_room_info.message}'
        )
        assert set(users_room_info.data.keys()) == {int(x) for x in uids}
        for uid_key, room_data in users_room_info.data.items():
            assert str(room_data.uid) == str(uid_key)
        print(f'uid 批量直播间信息验证通过: {list(users_room_info.data.keys())}')  # noqa: T201 用例诊断输出

    async def test_query_room_user_info(self, live_room_state: SimpleNamespace) -> None:
        """直播间主播信息验证 (重点核实 san 字段存续)"""
        from src.utils.bilibili_api import BilibiliLive

        for room_id, uid in live_room_state.rooms[:3]:
            await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
            try:
                room_user_info = await BilibiliLive.query_room_user_info(room_id=room_id)
            except ValidationError as e:
                pytest.fail(f'直播间主播信息响应模型验证失败 (room_id={room_id}): \n{e}')

            assert not room_user_info.error, (
                f'直播间主播信息接口返回异常 (room_id={room_id}): '
                f'code={room_user_info.code}, message={room_user_info.message}'
            )
            assert room_user_info.data.info.uid == int(uid)
            assert room_user_info.data.info.uname
            print(f'直播间 {room_id} 主播: {room_user_info.data.info.uname}, '  # noqa: T201 用例诊断输出
                  f'uid={room_user_info.data.info.uid}, san={room_user_info.data.san}')


@pytest.fixture(scope='class')
async def live_user_state() -> SimpleNamespace:
    """真实用户接口验证的共享状态: 加载并校验凭据, 采收自身 mid 与外部目标 UP 主

    凭据仅读取 (load_from_database); 本类 account/vip 用例强制依赖登录态, 失效则整类跳过
    """
    from src.utils.bilibili_api import BilibiliDynamic
    from src.utils.bilibili_api.api.login import BilibiliCredential
    from src.utils.bilibili_api.credential_manager import BILIBILI_CREDENTIAL_MANAGER

    await BILIBILI_CREDENTIAL_MANAGER.load_from_database()
    dedeuserid = BILIBILI_CREDENTIAL_MANAGER.get_cookie('DedeUserID')
    if BILIBILI_CREDENTIAL_MANAGER.get_cookie('SESSDATA') is None or dedeuserid is None:
        pytest.skip('数据库中未配置 bilibili 登录 Cookies, 跳过真实请求验证')
    if not await BilibiliCredential.check_valid():
        pytest.skip('Cookies 已失效或触发风控, 跳过真实请求验证')

    author: tuple[str, str] | None = None
    try:
        feed = await BilibiliDynamic.query_my_following_dynamics()
        if feed.data.items:
            author_info = feed.data.items[0].modules.module_author
            author = (author_info.mid, author_info.name)
    except Exception as e:
        print(f'feed 采收外部 UP 主失败, 相关用例将跳过: {e}')  # noqa: T201 用例诊断输出

    return SimpleNamespace(own_mid=int(dedeuserid), author=author)


class TestBilibiliUserLive:
    """BilibiliUser 真实请求验证 (强制依赖登录态)

    本类用例发起真实 bilibili API 请求, 仅应以
    `pytest tests/test_003_web/test_003_bilibili_api.py -k TestBilibiliUserLive -v -s` 单独运行
    """

    async def test_query_my_account_info(self, live_user_state: SimpleNamespace) -> None:
        """我的账户信息验证 (mid 与凭据一致性)"""
        from src.utils.bilibili_api import BilibiliUser

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            account = await BilibiliUser.query_my_account_info()
        except ValidationError as e:
            pytest.fail(f'account 响应模型验证失败: \n{e}')

        assert not account.error, f'account 接口返回异常: code={account.code}, message={account.message}'
        assert account.data.mid == live_user_state.own_mid
        assert account.data.uname, 'account 用户名为空'
        print(f'account: mid={account.data.mid}, uname={account.data.uname}, '  # noqa: T201 用例诊断输出
              f'userid={account.data.userid!r}, rank={account.data.rank!r}, '
              f'sex={account.data.sex!r}, birthday={account.data.birthday!r}')

    async def test_query_my_vip_info(self, live_user_state: SimpleNamespace) -> None:
        """我的大会员状态验证 (零值形态建模)"""
        from src.utils.bilibili_api import BilibiliUser

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            vip = await BilibiliUser.query_my_vip_info()
        except ValidationError as e:
            pytest.fail(f'vip 响应模型验证失败: \n{e}')

        assert not vip.error, f'vip 接口返回异常: code={vip.code}, message={vip.message}'
        assert vip.data.mid == live_user_state.own_mid
        print(f'vip: mid={vip.data.mid}, vip_type={vip.data.vip_type}, '  # noqa: T201 用例诊断输出
              f'vip_status={vip.data.vip_status}, vip_due_date={vip.data.vip_due_date}, '
              f'vip_pay_type={vip.data.vip_pay_type}, theme_type={vip.data.theme_type}')

    async def test_query_user_info_self(self, live_user_state: SimpleNamespace) -> None:
        """自查询用户信息验证 (覆盖 __RENDER_DATA__ -> w_webid -> wbi 签名完整链路)"""
        from src.utils.bilibili_api import BilibiliUser

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            user = await BilibiliUser.query_user_info(mid=live_user_state.own_mid)
        except ValidationError as e:
            pytest.fail(f'用户信息(自查询)响应模型验证失败: \n{e}')

        assert not user.error, f'用户信息(自查询)接口返回异常: code={user.code}, message={user.message}'
        assert user.data.mid == live_user_state.own_mid
        assert user.data.name, '用户名(自查询)为空'
        print(f'user(self): mid={user.data.mid}, name={user.data.name}, '  # noqa: T201 用例诊断输出
              f'level={user.data.level}, live_room={user.data.live_room!r}, '
              f'top_photo={user.data.top_photo!r}, birthday={user.data.birthday!r}')

    async def test_query_user_info_other(self, live_user_state: SimpleNamespace) -> None:
        """他查询用户信息验证"""
        from src.utils.bilibili_api import BilibiliUser

        if live_user_state.author is None:
            pytest.skip('未采收到外部 UP 主, 跳过他查询验证')
        author_mid, _author_name = live_user_state.author

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            user = await BilibiliUser.query_user_info(mid=author_mid)
        except ValidationError as e:
            pytest.fail(f'用户信息(他查询)响应模型验证失败 (mid={author_mid}): \n{e}')

        assert not user.error, (
            f'用户信息(他查询)接口返回异常 (mid={author_mid}): code={user.code}, message={user.message}'
        )
        assert user.data.mid == int(author_mid)
        assert user.data.name, f'用户名(他查询, mid={author_mid})为空'
        print(f'user(other): mid={user.data.mid}, name={user.data.name}, '  # noqa: T201 用例诊断输出
              f'is_followed={user.data.is_followed}, level={user.data.level}')

    async def test_search_user(self, live_user_state: SimpleNamespace) -> None:
        """用户搜索验证 (顺带实测 search/type 无 wbi 签名是否被接受)"""
        from src.utils.bilibili_api import BilibiliUser

        if live_user_state.author is None:
            pytest.skip('未采收到外部 UP 主, 跳过搜索验证')
        author_mid, author_name = live_user_state.author

        await asyncio.sleep(_LIVE_REQUEST_INTERVAL)
        try:
            results = await BilibiliUser.search_user(keyword=author_name)
        except ValidationError as e:
            pytest.fail(f'用户搜索响应模型验证失败 (keyword={author_name!r}): \n{e}')

        assert results, f'用户搜索无结果 (keyword={author_name!r})'
        for result in results:
            _ = result.mid
            _ = result.uname
            _ = result.fans
            _ = result.upic
        print(f'search_user({author_name!r}) 前 3 结果: '  # noqa: T201 用例诊断输出
              f'{[(r.mid, r.uname, r.fans) for r in results[:3]]}')
        assert any(r.mid == int(author_mid) for r in results), (
            f'目标 UP 主 {author_mid} 未出现在其名称 {author_name!r} 的搜索结果中'
        )
