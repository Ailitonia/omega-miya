"""
@Author         : Ailitonia
@Date           : 2026/9/4 18:52
@FileName       : test_004_event_patches
@Project        : omega-miya
@Description    : 自定义事件 patch 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from nonebot.adapters.onebot.v11 import (
    Adapter as OneBotV11Adapter,
)
from nonebot.adapters.onebot.v11 import (
    GroupMessageEvent as OneBotV11GroupMessageEvent,
)
from nonebot.adapters.onebot.v11 import (
    GroupUploadNoticeEvent as OneBotV11GroupUploadNoticeEvent,
)
from nonebot.adapters.onebot.v11 import (
    NoticeEvent as OneBotV11NoticeEvent,
)
from pydantic import ValidationError

_SELF_ID = 100001
"""测试用机器人自身 ID"""
_USER_ID = 900001
"""测试用用户 ID"""
_GROUP_ID = 800001
"""测试用群 ID"""

_ADDITION_PATCH_ALL_EXPORTS = [
    'GroupCardNoticeEvent',
    'OfflineFileNoticeEvent',
    'ClientStatusNoticeEvent',
    'EssenceNoticeEvent',
]
"""onebot_v11_addition_event_patch 及其 model 子模块的 __all__ 导出契约"""


def _make_notice_payload(notice_type: str, **fields: Any) -> dict[str, Any]:
    """构造 notice 事件公共前缀 payload(time/self_id/post_type='notice'/notice_type 四元组)"""
    payload: dict[str, Any] = {
        'time': 1700000000,
        'self_id': _SELF_ID,
        'post_type': 'notice',
        'notice_type': notice_type,
    }
    payload.update(fields)
    return payload


def _make_group_card_payload(**overrides: Any) -> dict[str, Any]:
    """构造群成员名片更新事件 payload(每次返回新 dict, 避免校验器原地改写污染)"""
    payload = _make_notice_payload(
        'group_card',
        group_id=_GROUP_ID,
        user_id=_USER_ID,
        card_new='test_card_new',
        card_old='test_card_old',
    )
    payload.update(overrides)
    return payload


def _make_offline_file_payload(**overrides: Any) -> dict[str, Any]:
    """构造离线文件事件 payload"""
    payload = _make_notice_payload(
        'offline_file',
        user_id=_USER_ID,
        file={
            'name': 'test_file.zip',
            'size': 1024,
            'url': 'https://example.com/file/test_file.zip',
        },
    )
    payload.update(overrides)
    return payload


def _make_client_status_payload(**overrides: Any) -> dict[str, Any]:
    """构造客户端在线状态变更事件 payload(注意: 该事件无 user_id 字段)"""
    payload = _make_notice_payload(
        'client_status',
        client={
            'app_id': 12345,
            'device_name': 'test_device',
            'device_kind': 'test_kind',
        },
        online=True,
    )
    payload.update(overrides)
    return payload


def _make_essence_payload(**overrides: Any) -> dict[str, Any]:
    """构造精华消息变更事件 payload"""
    payload = _make_notice_payload(
        'essence',
        sub_type='add',
        group_id=_GROUP_ID,
        sender_id=_USER_ID,
        operator_id=_USER_ID,
        message_id=12345,
    )
    payload.update(overrides)
    return payload


def _make_message_sent_payload(**overrides: Any) -> dict[str, Any]:
    """构造自身发送消息事件 payload"""
    payload = {
        'time': 1700000000,
        'self_id': _SELF_ID,
        'post_type': 'message_sent',
        'message_type': 'group',
        'sub_type': 'normal',
        'message_id': 123,
        'user_id': _SELF_ID,
        'group_id': _GROUP_ID,
        'message': 'test message content',
        'raw_message': 'test message content',
        'font': 0,
        'sender': {'user_id': _SELF_ID, 'nickname': 'test_bot'},
    }
    payload.update(overrides)
    return payload


class TestModuleContract:
    """模块导出契约测试"""

    def test_addition_patch_all_exports(self):
        import src.service.onebot_v11_addition_event_patch

        assert src.service.onebot_v11_addition_event_patch.__all__ == _ADDITION_PATCH_ALL_EXPORTS

    def test_addition_patch_model_all_exports(self):
        import src.service.onebot_v11_addition_event_patch.model

        assert src.service.onebot_v11_addition_event_patch.model.__all__ == _ADDITION_PATCH_ALL_EXPORTS

    def test_self_sent_patch_all_exports(self):
        import src.service.onebot_v11_self_sent_patch

        assert src.service.onebot_v11_self_sent_patch.__all__ == ['MessageSentEvent', 'SELF_SENT']

    def test_self_sent_patch_model_all_exports(self):
        import src.service.onebot_v11_self_sent_patch.model

        assert src.service.onebot_v11_self_sent_patch.model.__all__ == ['MessageSentEvent']


class TestEventRegistration:
    """自定义事件注册机制测试"""

    def test_addition_events_registered(self):
        from src.service.onebot_v11_addition_event_patch import (
            ClientStatusNoticeEvent,
            EssenceNoticeEvent,
            GroupCardNoticeEvent,
            OfflineFileNoticeEvent,
        )

        for event_model in (GroupCardNoticeEvent, OfflineFileNoticeEvent, ClientStatusNoticeEvent, EssenceNoticeEvent):
            assert event_model in OneBotV11Adapter.event_models.models

    def test_message_sent_event_registered(self):
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        assert MessageSentEvent in OneBotV11Adapter.event_models.models

    def test_unrelated_notice_type_not_hijacked(self):
        """无关 notice_type 的 payload 不应被自定义事件类劫持"""
        payload = {
            'time': 1700000000,
            'self_id': _SELF_ID,
            'post_type': 'notice',
            'notice_type': 'group_upload',
            'group_id': _GROUP_ID,
            'user_id': _USER_ID,
            'file': {'id': 'test_file_id', 'name': 'test_file', 'size': 1024, 'busid': 102},
        }
        parsed = OneBotV11Adapter.json_to_event(payload)

        assert isinstance(parsed, OneBotV11GroupUploadNoticeEvent)

    def test_normal_message_not_parsed_as_message_sent(self):
        """post_type='message' 的正常消息事件不应被解析为 MessageSentEvent(Literal 隔离)"""
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        parsed = OneBotV11Adapter.json_to_event(_make_message_sent_payload(post_type='message'))

        assert isinstance(parsed, OneBotV11GroupMessageEvent)
        assert not isinstance(parsed, MessageSentEvent)


class TestAdditionNoticeEventCommonBehavior:
    """四个自定义 notice 事件的公共行为测试(按事件类参数化合并)"""

    @pytest.mark.parametrize(
        ('event_class_name', 'payload_factory', 'payload_overrides', 'expected_attrs'),
        [
            ('GroupCardNoticeEvent', _make_group_card_payload, {}, {
                'group_id': _GROUP_ID,
                'user_id': _USER_ID,
                'card_new': 'test_card_new',
                'card_old': 'test_card_old',
            }),
            ('OfflineFileNoticeEvent', _make_offline_file_payload, {}, {
                'user_id': _USER_ID,
                'file.name': 'test_file.zip',
                'file.size': 1024,
                'file.url': 'https://example.com/file/test_file.zip',
            }),
            ('ClientStatusNoticeEvent', _make_client_status_payload, {}, {
                'client.app_id': 12345,
                'client.device_name': 'test_device',
                'client.device_kind': 'test_kind',
                'online': True,
            }),
            ('EssenceNoticeEvent', _make_essence_payload, {'sub_type': 'add'}, {
                'sub_type': 'add',
                'group_id': _GROUP_ID,
                'sender_id': _USER_ID,
                'operator_id': _USER_ID,
                'message_id': 12345,
            }),
            ('EssenceNoticeEvent', _make_essence_payload, {'sub_type': 'delete'}, {
                'sub_type': 'delete',
                'group_id': _GROUP_ID,
                'sender_id': _USER_ID,
                'operator_id': _USER_ID,
                'message_id': 12345,
            }),
        ],
    )
    def test_model_validate(
            self,
            event_class_name: str,
            payload_factory: Callable[..., dict[str, Any]],
            payload_overrides: dict[str, Any],
            expected_attrs: dict[str, Any],
    ):
        from src.service import onebot_v11_addition_event_patch

        event_class = getattr(onebot_v11_addition_event_patch, event_class_name)
        event = event_class.model_validate(payload_factory(**payload_overrides))

        for attr_path, expected in expected_attrs.items():
            attr_value = event
            for attr_name in attr_path.split('.'):
                attr_value = getattr(attr_value, attr_name)
            assert attr_value == expected

    @pytest.mark.parametrize(
        ('event_class_name', 'payload_factory', 'payload_overrides'),
        [
            ('GroupCardNoticeEvent', _make_group_card_payload, {}),
            ('OfflineFileNoticeEvent', _make_offline_file_payload, {}),
            ('ClientStatusNoticeEvent', _make_client_status_payload, {}),
            # essence 两种 sub_type 均应解析为自定义类(多值 Literal 注册键回退)
            ('EssenceNoticeEvent', _make_essence_payload, {'sub_type': 'add'}),
            ('EssenceNoticeEvent', _make_essence_payload, {'sub_type': 'delete'}),
        ],
    )
    def test_json_to_event(
            self,
            event_class_name: str,
            payload_factory: Callable[..., dict[str, Any]],
            payload_overrides: dict[str, Any],
    ):
        from src.service import onebot_v11_addition_event_patch

        event_class = getattr(onebot_v11_addition_event_patch, event_class_name)
        payload = payload_factory(**payload_overrides)
        parsed = OneBotV11Adapter.json_to_event(payload)

        assert isinstance(parsed, event_class)
        assert parsed == event_class.model_validate(payload_factory(**payload_overrides))

    @pytest.mark.parametrize(
        ('event_class_name', 'payload_factory', 'required_field'),
        [
            ('GroupCardNoticeEvent', _make_group_card_payload, 'card_new'),
            ('OfflineFileNoticeEvent', _make_offline_file_payload, 'file'),
            ('ClientStatusNoticeEvent', _make_client_status_payload, 'client'),
            ('EssenceNoticeEvent', _make_essence_payload, 'message_id'),
        ],
    )
    def test_json_to_event_invalid_payload_falls_back(
            self,
            event_class_name: str,
            payload_factory: Callable[..., dict[str, Any]],
            required_field: str,
    ):
        """缺必填字段的 payload 不应解析为自定义类, 而是回退到基类 NoticeEvent"""
        from src.service import onebot_v11_addition_event_patch

        event_class = getattr(onebot_v11_addition_event_patch, event_class_name)
        payload = payload_factory()
        del payload[required_field]
        parsed = OneBotV11Adapter.json_to_event(payload)

        assert isinstance(parsed, OneBotV11NoticeEvent)
        assert not isinstance(parsed, event_class)


class TestGroupCardNoticeEvent:
    """群成员名片更新提醒事件测试"""

    @pytest.mark.parametrize(('user_id', 'expected'), [(_SELF_ID, True), (_USER_ID, False)])
    def test_is_tome(self, user_id: int, expected: bool):
        from src.service.onebot_v11_addition_event_patch import GroupCardNoticeEvent

        event = GroupCardNoticeEvent.model_validate(_make_group_card_payload(user_id=user_id))

        assert event.is_tome() is expected

    def test_get_user_id(self):
        from src.service.onebot_v11_addition_event_patch import GroupCardNoticeEvent

        event = GroupCardNoticeEvent.model_validate(_make_group_card_payload())

        assert event.get_user_id() == str(_USER_ID)

    def test_get_session_id(self):
        from src.service.onebot_v11_addition_event_patch import GroupCardNoticeEvent

        event = GroupCardNoticeEvent.model_validate(_make_group_card_payload())

        assert event.get_session_id() == f'group_{_GROUP_ID}_{_USER_ID}'

    def test_missing_required_field_raises(self):
        from src.service.onebot_v11_addition_event_patch import GroupCardNoticeEvent

        payload = _make_group_card_payload()
        del payload['card_new']

        with pytest.raises(ValidationError):
            GroupCardNoticeEvent.model_validate(payload)

    def test_wrong_notice_type_raises(self):
        from src.service.onebot_v11_addition_event_patch import GroupCardNoticeEvent

        with pytest.raises(ValidationError):
            GroupCardNoticeEvent.model_validate(_make_group_card_payload(notice_type='group_admin'))


class TestOfflineFileNoticeEvent:
    """离线文件提醒事件测试"""

    def test_file_extra_fields_allowed(self):
        """OfflineFile 模型应保留未知额外字段(extra='allow')"""
        from src.service.onebot_v11_addition_event_patch import OfflineFileNoticeEvent

        file = {'name': 'test_file.zip', 'size': 1024, 'url': 'https://example.com/f.zip', 'file_id': 'extra_file_id'}
        event = OfflineFileNoticeEvent.model_validate(_make_offline_file_payload(file=file))

        assert event.file.model_extra is not None
        assert event.file.model_extra['file_id'] == 'extra_file_id'

    def test_is_tome_always_true(self):
        from src.service.onebot_v11_addition_event_patch import OfflineFileNoticeEvent

        event = OfflineFileNoticeEvent.model_validate(_make_offline_file_payload(user_id=_SELF_ID))

        assert event.is_tome()

    def test_get_user_id(self):
        from src.service.onebot_v11_addition_event_patch import OfflineFileNoticeEvent

        event = OfflineFileNoticeEvent.model_validate(_make_offline_file_payload())

        assert event.get_user_id() == str(_USER_ID)

    def test_get_session_id(self):
        from src.service.onebot_v11_addition_event_patch import OfflineFileNoticeEvent

        event = OfflineFileNoticeEvent.model_validate(_make_offline_file_payload())

        assert event.get_session_id() == f'{_USER_ID}_test_file.zip'

    def test_invalid_file_field_raises(self):
        from src.service.onebot_v11_addition_event_patch import OfflineFileNoticeEvent

        file = {'name': 'test_file.zip', 'size': 1024}

        with pytest.raises(ValidationError):
            OfflineFileNoticeEvent.model_validate(_make_offline_file_payload(file=file))


class TestClientStatusNoticeEvent:
    """其他客户端在线状态变更事件测试"""

    def test_device_extra_fields_allowed(self):
        """Device 模型应保留未知额外字段(extra='allow')"""
        from src.service.onebot_v11_addition_event_patch import ClientStatusNoticeEvent

        client = {'app_id': 12345, 'device_name': 'd', 'device_kind': 'k', 'extra_key': 'extra_value'}
        event = ClientStatusNoticeEvent.model_validate(_make_client_status_payload(client=client))

        assert event.client.model_extra is not None
        assert event.client.model_extra['extra_key'] == 'extra_value'

    def test_is_tome_always_true(self):
        from src.service.onebot_v11_addition_event_patch import ClientStatusNoticeEvent

        event = ClientStatusNoticeEvent.model_validate(_make_client_status_payload())

        assert event.is_tome()

    def test_get_user_id_uses_self_id(self):
        """client_status 事件无 user_id 字段, 用户 ID 应回退到机器人自身 ID"""
        from src.service.onebot_v11_addition_event_patch import ClientStatusNoticeEvent

        event = ClientStatusNoticeEvent.model_validate(_make_client_status_payload())

        assert event.get_user_id() == str(_SELF_ID)

    def test_get_session_id(self):
        from src.service.onebot_v11_addition_event_patch import ClientStatusNoticeEvent

        event = ClientStatusNoticeEvent.model_validate(_make_client_status_payload())

        assert event.get_session_id() == f'{_SELF_ID}_12345'

    def test_invalid_client_raises(self):
        from src.service.onebot_v11_addition_event_patch import ClientStatusNoticeEvent

        client = {'device_name': 'd', 'device_kind': 'k'}

        with pytest.raises(ValidationError):
            ClientStatusNoticeEvent.model_validate(_make_client_status_payload(client=client))


class TestEssenceNoticeEvent:
    """精华消息变更事件测试"""

    def test_invalid_sub_type_raises(self):
        from src.service.onebot_v11_addition_event_patch import EssenceNoticeEvent

        with pytest.raises(ValidationError):
            EssenceNoticeEvent.model_validate(_make_essence_payload(sub_type='move'))

    @pytest.mark.parametrize(
        ('self_id', 'sender_id', 'operator_id', 'expected'),
        [
            (_SELF_ID, _SELF_ID, _USER_ID, True),
            (_SELF_ID, _USER_ID, _SELF_ID, True),
            (_SELF_ID, _SELF_ID, _SELF_ID, True),
            (_SELF_ID, _USER_ID, 900002, False),
        ],
    )
    def test_is_tome(self, self_id: int, sender_id: int, operator_id: int, expected: bool):
        """is_tome 当且仅当发送者或操作者为机器人自身时为 True"""
        from src.service.onebot_v11_addition_event_patch import EssenceNoticeEvent

        payload = _make_essence_payload(self_id=self_id, sender_id=sender_id, operator_id=operator_id)
        event = EssenceNoticeEvent.model_validate(payload)

        assert event.is_tome() is expected

    def test_get_user_id(self):
        from src.service.onebot_v11_addition_event_patch import EssenceNoticeEvent

        event = EssenceNoticeEvent.model_validate(_make_essence_payload())

        assert event.get_user_id() == str(_USER_ID)

    def test_get_session_id(self):
        from src.service.onebot_v11_addition_event_patch import EssenceNoticeEvent

        event = EssenceNoticeEvent.model_validate(_make_essence_payload())

        assert event.get_session_id() == f'group_{_GROUP_ID}_{_USER_ID}'


class TestOneBotV11SelfSentMessageEvent:
    """自身发送消息事件测试"""

    def test_model_validate_str_message(self):
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload(message='hello', raw_message='hello'))

        assert event.message_id == 123
        assert event.user_id == _SELF_ID
        assert event.message.extract_plain_text() == 'hello'

    def test_model_validate_array_message(self):
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        message = [{'type': 'text', 'data': {'text': 'hello'}}]
        event = MessageSentEvent.model_validate(_make_message_sent_payload(message=message))

        assert event.message.extract_plain_text() == 'hello'

    def test_json_to_event(self):
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload())
        parsed = OneBotV11Adapter.json_to_event(_make_message_sent_payload())

        assert isinstance(parsed, MessageSentEvent)
        assert parsed == event

    def test_message_post_type_rejected(self):
        """post_type='message' 不应通过 MessageSentEvent 校验"""
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        with pytest.raises(ValidationError):
            MessageSentEvent.model_validate(_make_message_sent_payload(post_type='message'))

    def test_default_values(self):
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        payload = _make_message_sent_payload()
        del payload['group_id']
        event = MessageSentEvent.model_validate(payload)

        assert event.message_seq is None
        assert event.target_id is None
        assert event.group_id == 0
        assert event.anonymous is None
        assert event.to_me is False

    def test_original_message_is_deepcopy(self):
        """original_message 应由 message 自动深拷贝填充"""
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload())

        assert event.original_message == event.message
        assert event.original_message is not event.message

    def test_get_type_is_message(self):
        """补丁核心语义: get_type 返回 'message' 而非 'message_sent', 使消息类 matcher 可响应"""
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload())

        assert event.post_type == 'message_sent'
        assert event.get_type() == 'message'

    def test_get_user_id_uses_self_id(self):
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload(user_id=_USER_ID))

        assert event.get_user_id() == str(_SELF_ID)

    def test_get_session_id(self):
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload())

        assert event.get_session_id() == f'self_sent_{_SELF_ID}'

    def test_is_tome_always_false(self):
        """即使显式设置 to_me=True, is_tome 也恒为 False"""
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload())
        event_with_to_me = MessageSentEvent.model_validate(_make_message_sent_payload(to_me=True))

        assert not event.is_tome()
        assert not event_with_to_me.is_tome()
        assert event_with_to_me.to_me is True

    def test_get_event_description(self):
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload())
        description = event.get_event_description()

        assert f'Message {event.message_id}' in description
        assert f'from Bot {event.user_id}@[self-sent]' in description
        assert 'test message content' in description


class TestSelfSentPermission:
    """SELF_SENT 权限与检查函数测试"""

    def test_self_sent_is_permission(self):
        from nonebot.permission import Permission

        from src.service.onebot_v11_self_sent_patch import SELF_SENT

        assert isinstance(SELF_SENT, Permission)

    async def test_permission_matches_self_sent_event(self):
        from src.service.onebot_v11_self_sent_patch import SELF_SENT, MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload())

        assert await SELF_SENT(MagicMock(), event)

    async def test_permission_rejects_non_self_sent_event(self):
        from src.service.onebot_v11_self_sent_patch import SELF_SENT, MessageSentEvent

        event = MessageSentEvent.model_validate(_make_message_sent_payload(user_id=_USER_ID))

        assert not await SELF_SENT(MagicMock(), event)

    async def test_self_sent_checker(self):
        from src.service.onebot_v11_self_sent_patch import MessageSentEvent, _self_sent

        event = MessageSentEvent.model_validate(_make_message_sent_payload())
        other_event = MessageSentEvent.model_validate(_make_message_sent_payload(user_id=_USER_ID))

        assert await _self_sent(event)
        assert not await _self_sent(other_event)
