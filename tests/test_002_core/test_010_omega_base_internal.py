"""
@Author         : Ailitonia
@Date           : 2026/9/8 00:52
@FileName       : test_010_omega_base_internal
@Project        : omega-miya
@Description    : omega_base.internal 模块单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import time
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import nonebot
import pytest
from nonebug import App
from pydantic import ValidationError

from tests.test_002_core.helpers import (
    make_entity_init_params,
    make_mock_bot,
    make_obv11_group_message_event,
    registered_online_bot,
)

if TYPE_CHECKING:
    from src.service.omega_base.internal.entity import EntityInitParams


@pytest.fixture(scope='class')
def onebot_v11_version_info() -> dict[str, Any]:
    """OneBot V11 get_version_info 接口返回的客户端版本信息"""
    return {
        'app_name': f'cqhttp-{uuid4().hex[:8]}',
        'app_version': '1.0.1',
        'protocol_version': 'v11',
        'app_full_name': 'test-go-cqhttp-client-1.0.1',
    }


@pytest.fixture(scope='class')
def onebot_v11_group_info() -> list[dict[str, Any]]:
    """OneBot V11 get_group_list 接口返回的群信息"""

    def _random_group_info() -> dict[str, Any]:
        return {
            'group_id': random.randint(10000000, 99999999),
            'group_name': uuid4().hex[:8],
            'member_count': random.randint(1, 255),
            'max_member_count': 500,
            'group_memo': 'test_group',
            'group_create_time': int(time.time()),
            'group_level': 1,
        }

    return [_random_group_info() for _ in range(8)]


@pytest.fixture(scope='class')
def onebot_v11_friend_info() -> list[dict[str, Any]]:
    """OneBot V11 get_friend_list 接口返回的好友信息"""

    def _random_friend_info() -> dict[str, Any]:
        return {
            'user_id': random.randint(10000000, 99999999),
            'nickname': uuid4().hex[:8],
            'remark': 'test_user',
        }

    return [_random_friend_info() for _ in range(8)]


@pytest.fixture
async def telegram_me_info() -> dict[str, Any]:
    """Telegram Bot get_me 接口返回的 Bot 信息"""
    return {
        'id': random.randint(10000000, 99999999),
        'is_bot': True,
        'first_name': uuid4().hex[:8],
        'username': uuid4().hex[:8],
    }


def _define_dummy_target_cls() -> type:
    """构造用于测试的 BaseEntityTarget 具体子类"""
    from nonebot_plugin_alconna.uniseg import Target

    from src.service.omega_base.internal import BaseEntityTarget

    class _DummyEntityTarget(BaseEntityTarget):

        def _construct_target(self) -> Target:
            return Target(id=self.entity_params.entity_id)

        async def call_api_get_entity_name(self) -> str:
            return 'dummy_entity'

        async def call_api_get_entity_profile_image_url(self) -> str:
            return 'https://example.com/dummy.png'

    return _DummyEntityTarget


def _define_dummy_depend_cls() -> type:
    """构造用于测试的 BaseEventDepend 具体子类, event/user 分支返回可区分的 entity_id"""
    from src.service.omega_base.internal import BaseEventDepend

    class _DummyEventDepend(BaseEventDepend):

        def _extract_event_entity_params(self) -> 'EntityInitParams':
            return make_entity_init_params(entity_id='EVENT_ENTITY')

        def _extract_user_entity_params(self) -> 'EntityInitParams':
            return make_entity_init_params(entity_id='USER_ENTITY')

        def get_user_nickname(self) -> str:
            return 'dummy_user'

        def get_reply_msg_image_urls(self) -> list[str]:
            return []

    return _DummyEventDepend


def _define_plain_event_cls(event_type_name: str = 'plain_event') -> type:
    """构造用于测试的 OmegaBaseEvent 具体子类 (get_message 保持抛出 NotImplementedError)"""
    from src.service.omega_base.internal import OmegaBaseEvent

    class _PlainEvent(OmegaBaseEvent):
        event_type: str = event_type_name

        def get_user_id(self) -> str:
            return '10001'

        def get_session_id(self) -> str:
            return 'fake_session_10001'

        def is_tome(self) -> bool:
            return False

    return _PlainEvent


def _define_message_event_cls() -> type:
    """构造携带平台消息字段的事件子类, 用于 BaseEventDepend 消息提取测试"""
    from nonebot.adapters import Message as BaseMessage

    from src.service.omega_base.internal import OmegaBaseEvent

    class _FakeMessageEvent(OmegaBaseEvent):
        event_type: str = 'fake_message'
        message: BaseMessage
        original_message: BaseMessage | None = None

        def get_message(self) -> BaseMessage:
            return self.message

        def get_user_id(self) -> str:
            return '10001'

        def get_session_id(self) -> str:
            return 'fake_session_10001'

        def is_tome(self) -> bool:
            return False

    return _FakeMessageEvent


class TestModuleContract:
    """模块导出契约测试"""

    def test_module_all(self) -> None:
        import src.service.omega_base.internal as internal_module

        assert internal_module.__all__ == [
            'ENTITY_TARGET_REGISTER',
            'EVENT_DEPEND_REGISTER',
            'BaseEntityTarget',
            'BaseEventDepend',
            'BotActionEvent',
            'BotConnectEvent',
            'BotDisconnectEvent',
            'EntityAcquireType',
            'EntityInitParams',
            'OmegaBaseEvent',
            'OmegaEntity',
            'get_online_bots',
        ]

    def test_all_exports_resolvable(self) -> None:
        import src.service.omega_base.internal as internal_module

        for name in internal_module.__all__:
            assert getattr(internal_module, name, None) is not None, f'{name} 未能从模块导出中解析'

    def test_submodule_all(self) -> None:
        import src.service.omega_base.internal.adapter as adapter_module
        import src.service.omega_base.internal.bots as bots_module
        import src.service.omega_base.internal.consts as consts_module
        import src.service.omega_base.internal.entity as entity_module
        import src.service.omega_base.internal.event as event_module

        assert adapter_module.__all__ == [
            'BaseEntityTarget', 'BaseEventDepend', 'ENTITY_TARGET_REGISTER', 'EVENT_DEPEND_REGISTER',
        ]
        assert bots_module.__all__ == ['get_online_bots']
        assert consts_module.__all__ == [
            'CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX',
            'CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX',
            'GLOBAL_COOLDOWN_EVENT',
            'SKIP_COOLDOWN_PERMISSION_NODE',
            'CharacterAttribute',
            'CharacterProfile',
            'PermissionGlobal',
            'PermissionLevel',
        ]
        assert entity_module.__all__ == ['EntityAcquireType', 'EntityInitParams', 'OmegaEntity']
        assert event_module.__all__ == ['BotActionEvent', 'BotConnectEvent', 'BotDisconnectEvent', 'OmegaBaseEvent']


class TestInternalConsts:
    """内部权限节点及冷却事件常量测试"""

    def test_permission_nodes(self) -> None:
        from src.service.omega_base.internal.consts import PermissionGlobal, PermissionLevel

        assert PermissionGlobal.module == 'OmegaInternal'
        assert PermissionGlobal.plugin == 'OmegaInternal'
        assert PermissionGlobal.node == 'OmegaPermissionGlobalEnable'
        assert PermissionLevel.module == 'OmegaInternal'
        assert PermissionLevel.plugin == 'OmegaInternal'
        assert PermissionLevel.node == 'OmegaPermissionLevel'

    def test_character_nodes(self) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute, CharacterProfile

        assert CharacterAttribute.module == 'OmegaInternal'
        assert CharacterAttribute.plugin == 'OmegaInternalCharacterAttribute'
        assert CharacterProfile.module == 'OmegaInternal'
        assert CharacterProfile.plugin == 'OmegaInternalCharacterProfile'

    def test_cooldown_and_permission_constants(self) -> None:
        from src.service.omega_base.internal import consts

        assert consts.SKIP_COOLDOWN_PERMISSION_NODE == 'OmegaAllowSkipCooldown'
        assert consts.GLOBAL_COOLDOWN_EVENT == 'OmegaGlobalCooldown'
        assert consts.CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX == 'OmegaICAttrSetter'
        assert consts.CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX == 'OmegaICProfileSetter'

    def test_dataclass_default_instantiation(self) -> None:
        from src.service.omega_base.internal.consts import PermissionGlobal

        assert PermissionGlobal().module == 'OmegaInternal'


class TestOmegaBaseEvent:
    """OmegaBaseEvent 内部事件基类测试"""

    def test_type_and_name_reflect_event_type(self) -> None:
        from src.service.omega_base.internal import OmegaBaseEvent

        event = OmegaBaseEvent(event_type='custom_type')

        assert event.get_type() == 'custom_type'
        assert event.get_event_name() == 'custom_type'

    def test_description_escapes_tags(self) -> None:
        from src.service.omega_base.internal import OmegaBaseEvent

        event = OmegaBaseEvent(event_type='<script>')

        description = event.get_event_description()

        # escape_tag 以反斜杠转义 <tag> 形式的标记, 避免 NoneBot 日志标记语言被注入
        assert description == r"{'event_type': '\<script>'}"

    def test_unimplemented_methods_raise(self) -> None:
        from src.service.omega_base.internal import OmegaBaseEvent

        event = OmegaBaseEvent(event_type='x')

        with pytest.raises(NotImplementedError):
            event.get_message()
        with pytest.raises(NotImplementedError):
            event.get_user_id()
        with pytest.raises(NotImplementedError):
            event.get_session_id()
        with pytest.raises(NotImplementedError):
            event.is_tome()


class TestBotActionEvent:
    """BotActionEvent 及其子类事件测试"""

    def test_defaults_and_accessors(self) -> None:
        from src.service.omega_base.internal import BotActionEvent, BotConnectEvent, BotDisconnectEvent

        event = BotConnectEvent(bot_id='10001', bot_type='OneBot V11')

        assert event.event_type == 'bot_action'
        assert event.action == 'bot_connect'
        assert event.get_type() == 'bot_action'
        assert event.get_event_name() == 'bot_action'
        assert event.get_user_id() == '10001'
        assert event.get_session_id() == '10001'
        assert event.is_tome() is True

        disconnect_event = BotDisconnectEvent(bot_id='10002', bot_type='Console')
        assert disconnect_event.action == 'bot_disconnect'

        base_event = BotActionEvent(bot_id='10003', bot_type='Telegram', action='custom')
        assert base_event.action == 'custom'

    def test_get_message_raises_value_error(self) -> None:
        from src.service.omega_base.internal import BotConnectEvent

        event = BotConnectEvent(bot_id='1', bot_type='Console')

        with pytest.raises(ValueError, match='no message'):
            event.get_message()

    def test_description_format(self) -> None:
        from src.service.omega_base.internal import BotActionEvent

        event = BotActionEvent(bot_id='10001', bot_type='OneBot V11', action='bot_connect')

        assert event.get_event_description() == 'Bot(OneBot V11/10001) occurred the action: BOT_CONNECT'

    def test_missing_required_fields_raises(self) -> None:
        from src.service.omega_base.internal import BotConnectEvent

        with pytest.raises(ValidationError):
            BotConnectEvent(action='bot_connect')


class TestEntityTargetRegister:
    """EntityTarget 平台适配器注册表测试"""

    async def test_register_and_get_roundtrip(self, entity_target_register_sandbox) -> None:
        from src.database.internal.entity import EntityType

        dummy_cls = _define_dummy_target_cls()

        entity_target_register_sandbox.register_target(EntityType.CONSOLE_USER)(dummy_cls)

        assert entity_target_register_sandbox.get_target(EntityType.CONSOLE_USER) is dummy_cls

    async def test_register_decorator_returns_class_identity(self, entity_target_register_sandbox) -> None:
        """注册装饰器应原样返回被装饰的类"""
        from src.database.internal.entity import EntityType

        dummy_cls = _define_dummy_target_cls()

        returned = entity_target_register_sandbox.register_target(EntityType.CONSOLE_USER)(dummy_cls)

        assert returned is dummy_cls

    async def test_duplicate_registration_rejected(self, entity_target_register_sandbox) -> None:
        from src.database.internal.entity import EntityType

        register = entity_target_register_sandbox
        register.register_target(EntityType.CONSOLE_USER)(_define_dummy_target_cls())

        with pytest.raises(ValueError, match='Duplicate entity'):
            register.register_target(EntityType.CONSOLE_USER)(_define_dummy_target_cls())

    async def test_get_unregistered_rejected(self, entity_target_register_sandbox) -> None:
        from src.database.internal.entity import EntityType

        with pytest.raises(ValueError, match='not registered'):
            entity_target_register_sandbox.get_target(EntityType.TELEGRAM_CHANNEL)

    async def test_register_invalid_name_rejected(self, entity_target_register_sandbox) -> None:
        with pytest.raises(ValueError, match='not supported'):
            entity_target_register_sandbox.register_target('not_an_entity_type')(_define_dummy_target_cls())

    async def test_get_invalid_name_rejected(self, entity_target_register_sandbox) -> None:
        with pytest.raises(ValueError, match='not supported'):
            entity_target_register_sandbox.get_target('not_an_entity_type')

    async def test_incomplete_subclass_cannot_instantiate(self) -> None:
        from src.service.omega_base.internal import BaseEntityTarget

        class _IncompleteEntityTarget(BaseEntityTarget):
            pass

        with pytest.raises(TypeError):
            _IncompleteEntityTarget(entity_params=make_entity_init_params())

    async def test_get_bot_offline_raises_key_error(self) -> None:
        dummy_cls = _define_dummy_target_cls()
        target = dummy_cls(entity_params=make_entity_init_params(bot_id='TEST_OFFLINE_BOT_123'))

        with pytest.raises(KeyError):
            target.get_bot()

    async def test_get_bot_online_returns_registered_bot(self, app: App) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot

        dummy_cls = _define_dummy_target_cls()

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            async with registered_online_bot(
                    ctx, self_id='TEST_ONLINE_BOT_123', base=Bot, adapter=adapter,
            ) as bot:
                target = dummy_cls(
                    entity_params=make_entity_init_params(
                        bot_type='OneBot V11', bot_id='TEST_ONLINE_BOT_123', entity_type='onebot_v11_user',
                    ),
                )

                assert target.get_bot() is bot

    async def test_send_message_auto_revoke_sends_and_recalls(self) -> None:
        dummy_cls = _define_dummy_target_cls()
        target = dummy_cls(entity_params=make_entity_init_params())

        receipt = MagicMock()
        receipt.recall = AsyncMock()
        target.send_message = AsyncMock(return_value=receipt)

        await target.send_message_auto_revoke('hello', revoke_delay=5)

        target.send_message.assert_awaited_once()
        receipt.recall.assert_awaited_once_with(delay=5)


class TestBaseEntityTarget:
    """BaseEntityTarget 平台 API 适配器基类方法测试"""

    async def test_send_message_constructs_target_and_passthrough(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """send_message 应使用 _construct_target 构造的 Target 与 get_bot 的 Bot, 并透传 flags/kwargs"""
        from nonebot_plugin_alconna.uniseg import UniMessage

        dummy_cls = _define_dummy_target_cls()
        target_adapter = dummy_cls(entity_params=make_entity_init_params())

        fake_bot = MagicMock()
        target_adapter.get_bot = lambda: fake_bot  # type: ignore[method-assign]

        send_mock = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(UniMessage, 'send', send_mock)

        result = await target_adapter.send_message('hello', at_sender=True, reply_to=True, extra_kwarg=1)

        assert result is send_mock.return_value
        call_kwargs = send_mock.await_args.kwargs
        assert call_kwargs['target'].id == 'TEST_DUMMY_ENTITY'
        assert call_kwargs['bot'] is fake_bot
        assert call_kwargs['at_sender'] is True
        assert call_kwargs['reply_to'] is True
        assert call_kwargs['extra_kwarg'] == 1

    async def test_send_message_auto_revoke_default_delay(self) -> None:
        """send_message_auto_revoke 缺省撤回延迟应为 60 秒"""
        dummy_cls = _define_dummy_target_cls()
        target = dummy_cls(entity_params=make_entity_init_params())

        receipt = MagicMock()
        receipt.recall = AsyncMock()
        target.send_message = AsyncMock(return_value=receipt)

        await target.send_message_auto_revoke('hello')

        target.send_message.assert_awaited_once()
        receipt.recall.assert_awaited_once_with(delay=60)


class TestEventDependRegister:
    """EventDepend 事件对象解析器注册表测试"""

    def test_register_and_get_exact_class(self, event_depend_register_sandbox) -> None:
        event_cls = _define_plain_event_cls('exact_event')
        depend_cls = _define_dummy_depend_cls()

        event_depend_register_sandbox.register_depend(event_cls)(depend_cls)

        assert event_depend_register_sandbox.get_depend(event_cls()) is depend_cls

    def test_mro_resolves_to_registered_ancestor(self, event_depend_register_sandbox) -> None:
        base_cls = _define_plain_event_cls('ancestor_event')
        base_depend = _define_dummy_depend_cls()
        event_depend_register_sandbox.register_depend(base_cls)(base_depend)

        child_cls = type('ChildEvent', (base_cls,), {})

        assert event_depend_register_sandbox.get_depend(child_cls()) is base_depend

    def test_mro_prefers_nearest_ancestor(self, event_depend_register_sandbox) -> None:
        base_cls = _define_plain_event_cls('far_ancestor_event')
        child_cls = type('NearAncestorEvent', (base_cls,), {})
        base_depend = _define_dummy_depend_cls()
        child_depend = _define_dummy_depend_cls()
        event_depend_register_sandbox.register_depend(base_cls)(base_depend)
        event_depend_register_sandbox.register_depend(child_cls)(child_depend)

        assert event_depend_register_sandbox.get_depend(child_cls()) is child_depend
        assert event_depend_register_sandbox.get_depend(base_cls()) is base_depend

    def test_duplicate_registration_rejected(self, event_depend_register_sandbox) -> None:
        event_cls = _define_plain_event_cls('duplicate_event')
        event_depend_register_sandbox.register_depend(event_cls)(_define_dummy_depend_cls())

        with pytest.raises(ValueError, match='Duplicate event'):
            event_depend_register_sandbox.register_depend(event_cls)(_define_dummy_depend_cls())

    def test_unregistered_event_rejected(self, event_depend_register_sandbox) -> None:
        from src.service.omega_base.internal import OmegaBaseEvent

        with pytest.raises(ValueError, match='Event not supported'):
            event_depend_register_sandbox.get_depend(OmegaBaseEvent(event_type='x'))

    def test_get_depend_falls_back_to_registered_root(self, event_depend_register_sandbox) -> None:
        """注册 BaseEvent 根本身时, 任意事件均沿 MRO 解析到该兜底解析器"""
        from nonebot.adapters import Event as BaseEvent

        root_depend = _define_dummy_depend_cls()
        event_depend_register_sandbox.register_depend(BaseEvent)(root_depend)

        event_cls = _define_plain_event_cls('any_event')

        assert event_depend_register_sandbox.get_depend(event_cls()) is root_depend


class TestBaseEventDepend:
    """BaseEventDepend 事件解析及消息提取方法测试"""

    async def test_extract_entity_params_dispatch(self) -> None:
        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=MagicMock())

        event_params = depend.extract_entity_params('event')
        user_params = depend.extract_entity_params('user')

        assert event_params.entity_id == 'EVENT_ENTITY'
        assert user_params.entity_id == 'USER_ENTITY'

    async def test_extract_entity_params_invalid_acquire_type(self) -> None:
        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=MagicMock())

        with pytest.raises(ValueError, match='Not supported entity acquire_type'):
            depend.extract_entity_params('invalid')

    async def test_send_passthrough(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """send 应使用事件 Target 与构造时的 Bot, 并透传 flags/kwargs"""
        from nonebot_plugin_alconna.uniseg import Target, UniMessage

        bot = MagicMock()
        depend = _define_dummy_depend_cls()(bot=bot, event=MagicMock())
        depend.get_target = lambda: Target(id='TARGET_1', private=True)

        send_mock = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(UniMessage, 'send', send_mock)

        result = await depend.send('hello', at_sender=True, reply_to=True, custom_kwarg='x')

        assert result is send_mock.return_value
        call_kwargs = send_mock.await_args.kwargs
        assert call_kwargs['target'].id == 'TARGET_1'
        assert call_kwargs['target'].private is True
        assert call_kwargs['bot'] is bot
        assert call_kwargs['at_sender'] is True
        assert call_kwargs['reply_to'] is True
        assert call_kwargs['custom_kwarg'] == 'x'

    async def test_revoke_bot_sent_msg_delay_passthrough(self) -> None:
        """revoke_bot_sent_msg 应将 delay 原样透传至 receipt.recall"""
        from src.service.omega_base.internal import BaseEventDepend

        receipt = MagicMock()
        receipt.recall = AsyncMock()

        await BaseEventDepend.revoke_bot_sent_msg(receipt, revoke_delay=30)

        receipt.recall.assert_awaited_once_with(delay=30)

    async def test_get_uni_message_converts_platform_message(self, app: App) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id='TEST_DEP_BOT_1', base=Bot, adapter=adapter, auto_connect=False)

            event = _define_message_event_cls()(
                message=Message([MessageSegment.at('111'), MessageSegment.text('hi')]),
            )
            depend = _define_dummy_depend_cls()(bot=bot, event=event)

            uni_message = depend.get_uni_message()

            assert depend.get_msg_mentioned_user_ids() == ['111']
            assert uni_message.extract_plain_text() == 'hi'

    async def test_get_msg_image_urls_from_platform_message(self, app: App) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id='TEST_DEP_BOT_2', base=Bot, adapter=adapter, auto_connect=False)

            event = _define_message_event_cls()(
                message=Message([MessageSegment.image('https://example.com/a.png')]),
            )
            depend = _define_dummy_depend_cls()(bot=bot, event=event)

            assert depend.get_msg_image_urls() == ['https://example.com/a.png']

    async def test_get_uni_message_origin_uses_original_message(self, app: App) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot, Message

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id='TEST_DEP_BOT_3', base=Bot, adapter=adapter, auto_connect=False)

            event = _define_message_event_cls()(
                message=Message('current'),
                original_message=Message('origin text'),
            )
            depend = _define_dummy_depend_cls()(bot=bot, event=event)

            assert depend.get_uni_message().extract_plain_text() == 'current'
            assert depend.get_uni_message(origin=True).extract_plain_text() == 'origin text'

    async def test_get_uni_message_not_implemented_normalized(self) -> None:
        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=_define_plain_event_cls()(event_type='x'))

        with pytest.raises(NotImplementedError):
            depend.get_uni_message()

    async def test_get_uni_message_value_error_normalized(self) -> None:
        from src.service.omega_base.internal import BotConnectEvent

        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=BotConnectEvent(bot_id='1', bot_type='Console'))

        with pytest.raises(NotImplementedError):
            depend.get_uni_message()

    async def test_get_msg_image_urls_filters_none_url(self) -> None:
        """无 url 的图片段应被过滤 (直接构造 UniMessage 精确控制 url 为 None 的分支)"""
        from nonebot_plugin_alconna.uniseg import Image, UniMessage

        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=MagicMock())
        depend.get_uni_message = lambda **kwargs: UniMessage([
            Image(id='no_url'),
            Image(id='has_url', url='https://example.com/b.png'),
        ])

        assert depend.get_msg_image_urls() == ['https://example.com/b.png']

    async def test_get_reply_message_empty_returns_none(self) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=MagicMock())
        depend.get_uni_message = lambda **kwargs: UniMessage('plain text')

        assert depend.get_reply_message() is None

    async def test_get_reply_message_returns_first(self) -> None:
        from nonebot_plugin_alconna.uniseg import Reply, UniMessage

        first_reply = Reply(id='1')
        second_reply = Reply(id='2')
        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=MagicMock())
        depend.get_uni_message = lambda **kwargs: UniMessage([first_reply, second_reply])

        assert depend.get_reply_message() is first_reply

    async def test_get_reply_msg_plain_text_str_branch(self) -> None:
        from nonebot_plugin_alconna.uniseg import Reply, UniMessage

        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=MagicMock())
        depend.get_uni_message = lambda **kwargs: UniMessage([Reply(id='1', msg='raw string')])

        assert depend.get_reply_msg_plain_text() == 'raw string'

    async def test_get_reply_msg_plain_text_message_branch(self) -> None:
        from nonebot.adapters.onebot.v11 import Message
        from nonebot_plugin_alconna.uniseg import Reply, UniMessage

        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=MagicMock())
        depend.get_uni_message = lambda **kwargs: UniMessage([Reply(id='1', msg=Message('hello world'))])

        assert depend.get_reply_msg_plain_text() == 'hello world'

    async def test_get_reply_msg_plain_text_none_msg_branch(self) -> None:
        from nonebot_plugin_alconna.uniseg import Reply, UniMessage

        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=MagicMock())
        depend.get_uni_message = lambda **kwargs: UniMessage([Reply(id='1', msg=None)])

        assert depend.get_reply_msg_plain_text() is None

    async def test_get_reply_msg_plain_text_no_reply_returns_none(self) -> None:
        from nonebot_plugin_alconna.uniseg import UniMessage

        depend = _define_dummy_depend_cls()(bot=MagicMock(), event=MagicMock())
        depend.get_uni_message = lambda **kwargs: UniMessage('plain text')

        assert depend.get_reply_msg_plain_text() is None

    async def test_reply_from_platform_message(self, app: App) -> None:
        """OneBot V11 reply 段经真实转换后 msg 为 None, 文本提取应返回 None"""
        from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id='TEST_DEP_BOT_4', base=Bot, adapter=adapter, auto_connect=False)

            event = _define_message_event_cls()(
                message=Message([MessageSegment.reply(123), MessageSegment.text('hi')]),
            )
            depend = _define_dummy_depend_cls()(bot=bot, event=event)

            reply = depend.get_reply_message()

            assert reply is not None
            assert reply.id == '123'
            assert depend.get_reply_msg_plain_text() is None

    async def test_get_target_from_group_message_event(self, app: App) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot
        from nonebot_plugin_alconna.uniseg import Target

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id='TEST_DEP_BOT_5', base=Bot, adapter=adapter, auto_connect=False)

            event = make_obv11_group_message_event(group_id=10000, text='hello')
            depend = _define_dummy_depend_cls()(bot=bot, event=event)

            target = depend.get_target()

            assert isinstance(target, Target)
            assert target.id == '10000'
            assert target.private is False


class TestBotsOnlineRegistry:
    """在线 Bot 注册表及事件预处理去重逻辑测试 (隔离全局状态)"""

    async def test_connect_hook_registers_and_dispatches(self, online_bots_sandbox) -> None:
        bots_module, handle_event_mock = online_bots_sandbox

        from src.service.omega_base.internal import BotConnectEvent

        bot = make_mock_bot(self_id='TEST_HOOK_BOT_1')
        await getattr(bots_module, '__init_bot_connect')(bot)

        online_bots = bots_module.get_online_bots()
        assert online_bots['OneBot V11']['TEST_HOOK_BOT_1'] is bot

        handle_event_mock.assert_awaited_once()
        dispatched = handle_event_mock.await_args.kwargs['event']
        assert isinstance(dispatched, BotConnectEvent)
        assert dispatched.bot_id == 'TEST_HOOK_BOT_1'
        assert handle_event_mock.await_args.kwargs['bot'] is bot

    async def test_disconnect_hook_removes_and_dispatches(self, online_bots_sandbox) -> None:
        bots_module, handle_event_mock = online_bots_sandbox

        from src.service.omega_base.internal import BotDisconnectEvent

        bot = make_mock_bot(self_id='TEST_HOOK_BOT_2')
        await getattr(bots_module, '__init_bot_connect')(bot)
        await getattr(bots_module, '__dispose_bot_disconnect')(bot)

        assert 'TEST_HOOK_BOT_2' not in bots_module.get_online_bots().get('OneBot V11', {})
        assert handle_event_mock.await_count == 2
        assert isinstance(handle_event_mock.await_args.kwargs['event'], BotDisconnectEvent)

    async def test_disconnect_unknown_bot_no_error(self, online_bots_sandbox) -> None:
        """未注册的 Bot 断开连接不应抛出异常"""
        bots_module, _ = online_bots_sandbox

        await getattr(bots_module, '__dispose_bot_disconnect')(make_mock_bot(self_id='GHOST_BOT'))

    async def test_get_online_bots_returns_snapshot(self, online_bots_sandbox) -> None:
        """get_online_bots 返回快照副本, 修改返回值不影响内部注册表"""
        bots_module, _ = online_bots_sandbox

        bot = make_mock_bot(self_id='TEST_HOOK_BOT_3', adapter_name='Telegram')
        await getattr(bots_module, '__init_bot_connect')(bot)

        snapshot = bots_module.get_online_bots()
        snapshot.clear()

        assert 'TEST_HOOK_BOT_3' in bots_module.get_online_bots().get('Telegram', {})

    async def test_unique_bot_limit_ignores_no_user_events(self, online_bots_sandbox) -> None:
        bots_module, _ = online_bots_sandbox

        checker = getattr(bots_module, '__unique_bot_responding_limit')
        bot = make_mock_bot(self_id='ME_BOT')
        event = MagicMock()

        event.get_user_id.side_effect = NotImplementedError
        await checker(bot=bot, event=event)

        event.get_user_id.side_effect = ValueError('no user id')
        await checker(bot=bot, event=event)

    async def test_unique_bot_limit_ignores_other_online_bot_events(self, online_bots_sandbox) -> None:
        from nonebot.exception import IgnoredException

        bots_module, _ = online_bots_sandbox

        getattr(bots_module, '__ONLINE_BOTS')[('Telegram', 'OTHER_BOT')] = make_mock_bot(
            self_id='OTHER_BOT', adapter_name='Telegram',
        )

        checker = getattr(bots_module, '__unique_bot_responding_limit')
        bot = make_mock_bot(self_id='ME_BOT')
        event = MagicMock()
        event.get_user_id.return_value = 'OTHER_BOT'

        with pytest.raises(IgnoredException):
            await checker(bot=bot, event=event)

    async def test_unique_bot_limit_allows_unrelated_user(self, online_bots_sandbox) -> None:
        bots_module, _ = online_bots_sandbox

        getattr(bots_module, '__ONLINE_BOTS')[('Telegram', 'OTHER_BOT')] = make_mock_bot(
            self_id='OTHER_BOT', adapter_name='Telegram',
        )

        checker = getattr(bots_module, '__unique_bot_responding_limit')
        bot = make_mock_bot(self_id='ME_BOT')
        event = MagicMock()
        event.get_user_id.return_value = 'NORMAL_USER_1'

        await checker(bot=bot, event=event)

    async def test_unique_bot_limit_allows_own_self_id(self, online_bots_sandbox) -> None:
        """事件发送者为 Bot 自身账号时应放行 (仅比对其他在线 Bot)"""
        bots_module, _ = online_bots_sandbox

        bot = make_mock_bot(self_id='ME_BOT')
        getattr(bots_module, '__ONLINE_BOTS')[('OneBot V11', 'ME_BOT')] = bot

        checker = getattr(bots_module, '__unique_bot_responding_limit')
        event = MagicMock()
        event.get_user_id.return_value = 'ME_BOT'

        await checker(bot=bot, event=event)

    async def test_first_responded_bot_limit(self, online_bots_sandbox) -> None:
        from nonebot.exception import IgnoredException

        bots_module, _ = online_bots_sandbox

        limiter = getattr(bots_module, '__first_responded_bot_limit')
        event = MagicMock()
        event.get_session_id.return_value = 'SESSION_1'
        event.get_event_name.return_value = 'test_event'

        # 首次响应的 Bot 登记会话归属
        await limiter(bot=make_mock_bot(self_id='BOT_A'), event=event)
        registry = getattr(bots_module, '__FIRST_RESPOND_REGISTRY')
        assert registry['SESSION_1'][0] == 'BOT_A'
        first_expire_at = registry['SESSION_1'][1]

        # 同一会话内同一 Bot 放行并刷新有效期
        await limiter(bot=make_mock_bot(self_id='BOT_A'), event=event)
        assert registry['SESSION_1'][1] >= first_expire_at

        # 同一会话内其他 Bot 被忽略
        with pytest.raises(IgnoredException):
            await limiter(bot=make_mock_bot(self_id='BOT_B'), event=event)

    async def test_first_responded_bot_limit_expired_allows_takeover(self, online_bots_sandbox) -> None:
        """会话归属过期后, 其他 Bot 可接管该会话"""
        bots_module, _ = online_bots_sandbox

        # 直接构造已过期的会话归属记录
        registry = getattr(bots_module, '__FIRST_RESPOND_REGISTRY')
        registry['SESSION_EXPIRED'] = ('BOT_A', time.monotonic() - 1)

        limiter = getattr(bots_module, '__first_responded_bot_limit')
        event = MagicMock()
        event.get_session_id.return_value = 'SESSION_EXPIRED'
        event.get_event_name.return_value = 'test_event'

        await limiter(bot=make_mock_bot(self_id='BOT_B'), event=event)
        assert registry['SESSION_EXPIRED'][0] == 'BOT_B'

    async def test_first_responded_bot_limit_no_session_id_skips(self, online_bots_sandbox) -> None:
        """无法提取 session_id 的事件不参与检查, 直接放行且不登记"""
        bots_module, _ = online_bots_sandbox

        limiter = getattr(bots_module, '__first_responded_bot_limit')
        event = MagicMock()

        event.get_session_id.side_effect = NotImplementedError
        await limiter(bot=make_mock_bot(self_id='BOT_A'), event=event)

        event.get_session_id.side_effect = ValueError('no session id')
        await limiter(bot=make_mock_bot(self_id='BOT_A'), event=event)

        assert getattr(bots_module, '__FIRST_RESPOND_REGISTRY') == {}

    async def test_get_online_bots_multi_adapter_grouping(self, online_bots_sandbox) -> None:
        """get_online_bots 应按适配器分组, 同适配器下按 self_id 区分多实例"""
        bots_module, _ = online_bots_sandbox

        bot_ob_a = make_mock_bot(self_id='BOT_OB_A', adapter_name='OneBot V11')
        bot_ob_b = make_mock_bot(self_id='BOT_OB_B', adapter_name='OneBot V11')
        bot_tg = make_mock_bot(self_id='BOT_TG', adapter_name='Telegram')
        for bot in (bot_ob_a, bot_ob_b, bot_tg):
            await getattr(bots_module, '__init_bot_connect')(bot)

        online_bots = bots_module.get_online_bots()
        assert set(online_bots.keys()) == {'OneBot V11', 'Telegram'}
        assert set(online_bots['OneBot V11'].keys()) == {'BOT_OB_A', 'BOT_OB_B'}
        assert online_bots['OneBot V11']['BOT_OB_A'] is bot_ob_a
        assert online_bots['Telegram']['BOT_TG'] is bot_tg

    async def test_connect_hook_overwrites_same_bot(self, online_bots_sandbox) -> None:
        """同一 Bot 重复连接时覆盖登记, 每次连接均派发 BotConnectEvent"""
        bots_module, handle_event_mock = online_bots_sandbox

        bot_first = make_mock_bot(self_id='BOT_DUP')
        bot_reconnect = make_mock_bot(self_id='BOT_DUP')
        await getattr(bots_module, '__init_bot_connect')(bot_first)
        await getattr(bots_module, '__init_bot_connect')(bot_reconnect)

        online_bots = bots_module.get_online_bots()
        assert online_bots['OneBot V11']['BOT_DUP'] is bot_reconnect
        assert handle_event_mock.await_count == 2

    async def test_unique_bot_limit_empty_online_list(self, online_bots_sandbox) -> None:
        """无其他在线 Bot 时, 任何用户事件均放行"""
        bots_module, _ = online_bots_sandbox

        checker = getattr(bots_module, '__unique_bot_responding_limit')
        event = MagicMock()
        event.get_user_id.return_value = 'NORMAL_USER_1'

        await checker(bot=make_mock_bot(self_id='ME_BOT'), event=event)

    async def test_unique_bot_limit_cross_adapter_same_self_id(self, online_bots_sandbox) -> None:
        """跨适配器数值 ID 恰好碰撞时的误忽略为已声明的设计取舍, 固化该行为"""
        from nonebot.exception import IgnoredException

        bots_module, _ = online_bots_sandbox

        # 另一适配器上存在 self_id 相同的在线 Bot
        getattr(bots_module, '__ONLINE_BOTS')[('Telegram', '10001')] = make_mock_bot(
            self_id='10001', adapter_name='Telegram',
        )

        checker = getattr(bots_module, '__unique_bot_responding_limit')
        event = MagicMock()
        event.get_user_id.return_value = '10001'

        with pytest.raises(IgnoredException):
            await checker(bot=make_mock_bot(self_id='ME_BOT', adapter_name='OneBot V11'), event=event)


class TestBotActions:
    """Bot 事件测试"""

    async def test_onebot_v11_bot_connected(
            self,
            app: App,
            test_onebot_v11_bot,
            onebot_v11_version_info: dict[str, Any],
            onebot_v11_group_info: list[dict[str, Any]],
            onebot_v11_friend_info: list[dict[str, Any]],
    ) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot
        from nonebot.message import handle_event

        from src.database.internal.bot import BotSelf, BotSelfDAL, BotStatus, BotType
        from src.database.internal.entity import EntityDAL
        from src.service.omega_base.internal import BotConnectEvent

        test_bot_self_id = test_onebot_v11_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            # auto_connect=False: 不触发后台连接钩子任务, 由下方 handle_event 同步驱动
            bot = ctx.create_bot(self_id=test_bot_self_id, base=Bot, adapter=adapter, auto_connect=False)

            # 不带 adapter= 约束: ApiContext 已将真实 adapter 的 _call_api 替换为
            # 临时 fake adapter 实例的绑定方法, 声明真实 adapter 身份永远无法匹配
            ctx.should_call_api('get_version_info', {}, onebot_v11_version_info)
            ctx.should_call_api('get_group_list', {}, onebot_v11_group_info)
            ctx.should_call_api('get_friend_list', {}, onebot_v11_friend_info)

            # 同步驱动 BotConnectEvent 的真实处理管线 (与 __init_bot_connect 同路径):
            # event_preprocessor __obv11_bot_connect 会按序调用上述三个 API 并同步 Bot 状态与群组/好友数据
            await handle_event(
                bot=bot,
                event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )

            # 三个 API 期望应全部被连接钩子按顺序消费
            assert ctx.wait_list.empty()

        # 验证连接同步逻辑的落库结果
        expected_bot_info = (
            f'{onebot_v11_version_info["app_name"]}-'
            f'{onebot_v11_version_info["app_version"]}-'
            f'{onebot_v11_version_info["protocol_version"]}'
        )
        async with BotSelfDAL.create() as dal:
            bot_self: BotSelf = await dal.query_unique(bot_type=BotType.ONEBOT_V11, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.ENABLED
        assert bot_self.bot_info == expected_bot_info

        async with EntityDAL.create() as dal:
            for group in onebot_v11_group_info:
                entity = await dal.query_unique(
                    bot_type=BotType.ONEBOT_V11,
                    bot_self_id=test_bot_self_id,
                    entity_type='onebot_v11_group',
                    entity_id=str(group['group_id']),
                )
                assert entity.entity_name == group['group_name']
                assert entity.entity_info == group['group_memo']

            for friend in onebot_v11_friend_info:
                entity = await dal.query_unique(
                    bot_type=BotType.ONEBOT_V11,
                    bot_self_id=test_bot_self_id,
                    entity_type='onebot_v11_user',
                    entity_id=str(friend['user_id']),
                )
                assert entity.entity_name == friend['nickname']
                assert entity.entity_info == friend['remark']

    async def test_onebot_v11_bot_disconnected(
            self,
            app: App,
            test_onebot_v11_bot,
    ) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot
        from nonebot.message import handle_event

        from src.database.internal.bot import BotSelfDAL, BotType
        from src.service.omega_base.internal import BotDisconnectEvent

        test_bot_self_id = test_onebot_v11_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id=test_bot_self_id, base=Bot, adapter=adapter, auto_connect=False)

            # 断开处理不调用任何 API, 期望队列应保持为空
            await handle_event(
                bot=bot,
                event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证断开处理更新了 Bot 状态信息
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.ONEBOT_V11, self_id=test_bot_self_id)
        assert bot_self.bot_info == 'Bot Offline'

    async def test_console_bot_connected(
            self,
            app: App,
            test_console_bot,
    ) -> None:
        from nonebot.adapters.console import Adapter
        from nonebot.adapters.console import Bot as ConsoleBot
        from nonebot.message import handle_event
        from nonechat.model import Robot

        from src.database.internal.bot import BotSelfDAL, BotStatus, BotType
        from src.service.omega_base.internal import BotConnectEvent

        test_bot_self_id = test_console_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            # Console Bot 构造签名为 __init__(adapter, info: Robot), 与 nonebug 的
            # create_bot(self_id=...) 不兼容, 手动构造实例 (不注册进 driver)
            bot = ConsoleBot(adapter=adapter, info=Robot(id=test_bot_self_id))

            # 连接处理不调用任何 API, 期望队列应保持为空
            await handle_event(
                bot=bot,
                event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证连接同步逻辑的落库结果
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.CONSOLE, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.ENABLED
        assert bot_self.bot_info == 'Bot Online'

    async def test_console_bot_disconnected(
            self,
            app: App,
            test_console_bot,
    ) -> None:
        from nonebot.adapters.console import Adapter
        from nonebot.adapters.console import Bot as ConsoleBot
        from nonebot.message import handle_event
        from nonechat.model import Robot

        from src.database.internal.bot import BotSelfDAL, BotStatus, BotType
        from src.service.omega_base.internal import BotDisconnectEvent

        test_bot_self_id = test_console_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ConsoleBot(adapter=adapter, info=Robot(id=test_bot_self_id))

            # 断开处理不调用任何 API, 期望队列应保持为空
            await handle_event(
                bot=bot,
                event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证断开处理更新了 Bot 状态信息
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.CONSOLE, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.DISABLED
        assert bot_self.bot_info == 'Bot Offline'

    async def test_telegram_bot_connected(
            self,
            app: App,
            test_telegram_bot,
            telegram_me_info: dict[str, Any],
    ) -> None:
        from nonebot.adapters.telegram import Adapter, Bot
        from nonebot.adapters.telegram.config import BotConfig as TelegramBotConfig
        from nonebot.message import handle_event

        from src.database.internal.bot import BotSelfDAL, BotStatus, BotType
        from src.service.omega_base.internal import BotConnectEvent

        test_bot_self_id = test_telegram_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            # auto_connect=False: 不触发后台连接钩子任务, 由下方 handle_event 同步驱动
            # Telegram Bot 构造强制要求 config 参数, 经 create_bot 的 **kwargs 透传
            bot = ctx.create_bot(
                self_id=test_bot_self_id,
                base=Bot,
                adapter=adapter,
                auto_connect=False,
                config=TelegramBotConfig(token='123456:TEST_TOKEN'),
            )

            # 不带 adapter= 约束 (同 OneBot V11 测试); get_me 的返回值会经
            # Telegram Bot.call_api 类型化包装校验为 User 模型, mock 须为合法载荷
            ctx.should_call_api('get_me', {}, telegram_me_info)

            # 同步驱动 BotConnectEvent 的真实处理管线:
            # event_preprocessor __telegram_bot_connect 会调用 get_me 并更新 Bot 状态
            await handle_event(
                bot=bot,
                event=BotConnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证连接同步逻辑的落库结果
        expected_bot_info = (
            f'{telegram_me_info["id"]}-'
            f'{telegram_me_info["first_name"]}@'
            f'{telegram_me_info["username"]}'
        )
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.TELEGRAM, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.ENABLED
        assert bot_self.bot_info == expected_bot_info

    async def test_telegram_bot_disconnected(
            self,
            app: App,
            test_telegram_bot,
    ) -> None:
        from nonebot.adapters.telegram import Adapter, Bot
        from nonebot.adapters.telegram.config import BotConfig as TelegramBotConfig
        from nonebot.message import handle_event

        from src.database.internal.bot import BotSelfDAL, BotStatus, BotType
        from src.service.omega_base.internal import BotDisconnectEvent

        test_bot_self_id = test_telegram_bot.self_id
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(
                self_id=test_bot_self_id,
                base=Bot,
                adapter=adapter,
                auto_connect=False,
                config=TelegramBotConfig(token='123456:TEST_TOKEN'),
            )

            # 断开处理不调用任何 API, 期望队列应保持为空
            await handle_event(
                bot=bot,
                event=BotDisconnectEvent(bot_id=bot.self_id, bot_type=bot.adapter.get_name()),
            )
            assert ctx.wait_list.empty()

        # 验证断开处理更新了 Bot 状态信息
        async with BotSelfDAL.create() as dal:
            bot_self = await dal.query_unique(bot_type=BotType.TELEGRAM, self_id=test_bot_self_id)
        assert bot_self.bot_status == BotStatus.DISABLED
        assert bot_self.bot_info == 'Bot Offline'
