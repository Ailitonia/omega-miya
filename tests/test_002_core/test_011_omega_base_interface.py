"""
@Author         : Ailitonia
@Date           : 2026/9/10 20:45
@FileName       : test_011_omega_base_interface
@Project        : omega-miya
@Description    : omega_base 模块 interface 与 middlewares 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import nonebot
import pytest
from nonebot.exception import FinishedException, PausedException, RejectedException
from nonebug import App

if TYPE_CHECKING:
    from nonebot.adapters import Event as BaseEvent

    from src.service.omega_base.internal.entity import EntityInitParams


@pytest.fixture
def entity_target_register_sandbox(monkeypatch: pytest.MonkeyPatch):
    """EntityTarget 注册表测试沙箱

    以空表替换内部注册表 (monkeypatch 在测试后恢复原表), 测试内的注册操作不影响全局
    """
    from src.service.omega_base.internal import ENTITY_TARGET_REGISTER

    monkeypatch.setattr(ENTITY_TARGET_REGISTER, '_map', {})
    return ENTITY_TARGET_REGISTER


def _make_entity_init_params(**overrides: Any) -> 'EntityInitParams':
    """构造测试用 EntityInitParams (内部导入避免收集期初始化)"""
    from src.database.internal.bot import BotType
    from src.database.internal.entity import EntityType
    from src.service.omega_base.internal.entity import EntityInitParams

    params: dict[str, Any] = {
        'bot_type': BotType.CONSOLE,
        'bot_id': 'TEST_DUMMY_BOT',
        'entity_type': EntityType.CONSOLE_USER,
        'entity_id': 'TEST_DUMMY_ENTITY',
        'entity_extra': {},
    }
    params.update(overrides)
    return EntityInitParams(**params)


def _make_mock_bot(adapter_name: str = 'OneBot V11') -> MagicMock:
    """构造提供 adapter.get_name 与 self_id 的 mock Bot (用于不触发真实 API 的依赖提取)"""
    bot = MagicMock()
    bot.self_id = '10086'
    bot.adapter.get_name.return_value = adapter_name
    return bot


# ------------------------------------------------------------------ #
# 事件构造工具
# ------------------------------------------------------------------ #

def _make_obv11_group_message_event(
        *,
        group_id: int = 10000,
        user_id: int = 10001,
        nickname: str | None = None,
        card: str | None = None,
        reply: Any = None,
) -> 'BaseEvent':
    from nonebot.adapters.onebot.v11 import Message
    from nonebot.adapters.onebot.v11.event import GroupMessageEvent, Sender

    return GroupMessageEvent(
        time=1,
        self_id=10086,
        post_type='message',
        sub_type='normal',
        message_id=1,
        user_id=user_id,
        message_type='group',
        group_id=group_id,
        message=Message('hi'),
        original_message=Message('hi'),
        raw_message='hi',
        font=0,
        sender=Sender(user_id=user_id, nickname=nickname, card=card),
        reply=reply,
    )


def _make_obv11_private_message_event(
        *,
        user_id: int = 10001,
        nickname: str | None = None,
) -> 'BaseEvent':
    from nonebot.adapters.onebot.v11 import Message
    from nonebot.adapters.onebot.v11.event import PrivateMessageEvent, Sender

    return PrivateMessageEvent(
        time=1,
        self_id=10086,
        post_type='message',
        message_type='private',
        sub_type='friend',
        message_id=1,
        user_id=user_id,
        message=Message('hi'),
        original_message=Message('hi'),
        raw_message='hi',
        font=0,
        sender=Sender(user_id=user_id, nickname=nickname),
    )


def _make_obv11_meta_event() -> 'BaseEvent':
    from nonebot.adapters.onebot.v11.event import MetaEvent

    return MetaEvent(time=1, self_id=10086, post_type='meta_event', meta_event_type='lifecycle')


def _make_obv11_friend_recall_notice_event(*, user_id: int = 30001) -> 'BaseEvent':
    from nonebot.adapters.onebot.v11.event import FriendRecallNoticeEvent

    return FriendRecallNoticeEvent(
        time=1,
        self_id=10086,
        post_type='notice',
        notice_type='friend_recall',
        user_id=user_id,
        message_id=1,
    )


def _make_obv11_honor_notify_event(*, group_id: int = 10000, user_id: int = 10001) -> 'BaseEvent':
    from nonebot.adapters.onebot.v11.event import HonorNotifyEvent

    return HonorNotifyEvent(
        time=1,
        self_id=10086,
        post_type='notice',
        notice_type='notify',
        sub_type='honor',
        honor_type='talkative',
        group_id=group_id,
        user_id=user_id,
    )


def _make_obv11_poke_notify_event(*, group_id: int | None = 10000, user_id: int = 10001) -> 'BaseEvent':
    from nonebot.adapters.onebot.v11.event import PokeNotifyEvent

    return PokeNotifyEvent(
        time=1,
        self_id=10086,
        post_type='notice',
        notice_type='notify',
        sub_type='poke',
        group_id=group_id,
        user_id=user_id,
        target_id=user_id,
    )


def _make_telegram_user_payload(*, user_id: int = 10001, username: str | None = None) -> dict[str, Any]:
    return {'id': user_id, 'is_bot': False, 'first_name': 'Tester', 'username': username}


def _make_telegram_message_event(
        event_kind: str = 'group',
        *,
        username: str | None = None,
        chat_username: str | None = None,
        reply_to: dict[str, Any] | None = None,
        message: list[dict[str, Any]] | None = None,
) -> 'BaseEvent':
    """构造 Telegram 平台消息事件 (经 model_validate 以正确处理 from 字段别名)"""
    from nonebot.adapters.telegram.event import (
        ChannelPostEvent,
        GroupMessageEvent,
        PrivateMessageEvent,
    )

    chat: dict[str, Any] = {
        'id': -1001234567,
        'type': {'group': 'group', 'private': 'private', 'channel': 'channel'}[event_kind],
        'title': 'Test Chat',
    }
    if chat_username is not None:
        chat['username'] = chat_username

    payload: dict[str, Any] = {
        'message_id': 1,
        'date': 1,
        'chat': chat,
        'message': message or [{'type': 'text', 'data': {'text': 'hi'}}],
    }
    if event_kind != 'channel':
        payload['from'] = _make_telegram_user_payload(username=username)
    if reply_to is not None:
        payload['reply_to_message'] = reply_to

    event_cls = {'group': GroupMessageEvent, 'private': PrivateMessageEvent, 'channel': ChannelPostEvent}[event_kind]
    return event_cls.model_validate(payload)


def _make_console_message_event(*, direct: bool = False, channel_id: str = 'channel_1') -> 'BaseEvent':
    from datetime import datetime

    from nonebot.adapters.console import Message as ConsoleMessage
    from nonebot.adapters.console.event import MessageEvent as ConsoleMessageEvent
    from nonechat.model import DIRECT, Channel, User

    channel = DIRECT if direct else Channel(id=channel_id, name='测试频道', description='频道描述')
    return ConsoleMessageEvent(
        time=datetime.now(),
        self_id='console',
        user=User(id='user_1', nickname='测试用户'),
        channel=channel,
        message_id='m1',
        message=ConsoleMessage('hi'),
    )


class TestModuleContract:
    """模块导出契约测试"""

    def test_omega_base_module_all(self) -> None:
        import src.service.omega_base as omega_base_module

        assert omega_base_module.__all__ == [
            'OmegaEntity',
            'OmegaEntityInterface',
            'OmegaMatcherInterface',
            'get_online_bots',
        ]

        for name in omega_base_module.__all__:
            assert getattr(omega_base_module, name, None) is not None, f'{name} 未能从模块导出中解析'

    def test_interface_module_all(self) -> None:
        import src.service.omega_base.interface as interface_module

        assert interface_module.__all__ == ['OmegaEntityInterface', 'OmegaMatcherInterface']

    def test_middlewares_module_all(self) -> None:
        import src.service.omega_base.middlewares as middlewares_module

        assert middlewares_module.__all__ == []


class TestOmegaEntityInterface:
    """OmegaEntityInterface 对象接口测试"""

    def test_type_property(self) -> None:
        from src.service.omega_base import OmegaEntityInterface

        params = _make_entity_init_params()
        interface = OmegaEntityInterface(entity_params=params)

        assert interface.type == params.entity_type
        assert interface.entity_params is params

    async def test_get_entity_target_resolves_middleware_cls(self) -> None:
        from src.service.omega_base import OmegaEntityInterface
        from src.service.omega_base.middlewares.console import ConsoleUserEntityTarget
        from src.service.omega_base.middlewares.onebot_v11 import OneBotV11GroupEntityTarget, OneBotV11UserEntityTarget
        from src.service.omega_base.middlewares.telegram import TelegramUserEntityTarget

        console_params = _make_entity_init_params()
        obv11_user_params = _make_entity_init_params(
            bot_type='OneBot V11', entity_type='onebot_v11_user', bot_id='10086', entity_id='10001',
        )
        obv11_group_params = _make_entity_init_params(
            bot_type='OneBot V11', entity_type='onebot_v11_group', bot_id='10086', entity_id='10000',
        )
        telegram_params = _make_entity_init_params(
            bot_type='Telegram', entity_type='telegram_user', bot_id='TG_BOT', entity_id='TG_USER',
        )

        assert isinstance(OmegaEntityInterface(console_params).get_entity_target(), ConsoleUserEntityTarget)
        assert isinstance(OmegaEntityInterface(obv11_user_params).get_entity_target(), OneBotV11UserEntityTarget)
        assert isinstance(OmegaEntityInterface(obv11_group_params).get_entity_target(), OneBotV11GroupEntityTarget)
        assert isinstance(OmegaEntityInterface(telegram_params).get_entity_target(), TelegramUserEntityTarget)

        target = OmegaEntityInterface(obv11_user_params).get_entity_target()
        assert target.entity_params is obv11_user_params

    async def test_get_entity_target_unregistered_rejected(self, entity_target_register_sandbox) -> None:
        from src.service.omega_base import OmegaEntityInterface

        interface = OmegaEntityInterface(entity_params=_make_entity_init_params())

        with pytest.raises(ValueError, match='not registered'):
            interface.get_entity_target()

    async def test_get_bot_offline_raises_key_error(self) -> None:
        from src.service.omega_base import OmegaEntityInterface

        interface = OmegaEntityInterface(entity_params=_make_entity_init_params(bot_id='TEST_OFFLINE_BOT_456'))

        with pytest.raises(KeyError):
            interface.get_bot()

    async def test_get_bot_online_returns_registered_bot(self, app: App) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot

        from src.service.omega_base import OmegaEntityInterface

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id='TEST_ONLINE_BOT_456', base=Bot, adapter=adapter, auto_connect=False)

            interface = OmegaEntityInterface(entity_params=_make_entity_init_params(
                bot_type='OneBot V11', bot_id='TEST_ONLINE_BOT_456', entity_type='onebot_v11_user', entity_id='10001',
            ))

            driver_bots = nonebot.get_driver().bots
            driver_bots['TEST_ONLINE_BOT_456'] = bot
            try:
                assert interface.get_bot() is bot
            finally:
                driver_bots.pop('TEST_ONLINE_BOT_456', None)

    async def test_send_entity_message_wires_target_and_bot(self, app: App, monkeypatch: pytest.MonkeyPatch) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot
        from nonebot_plugin_alconna.uniseg import UniMessage

        from src.service.omega_base import OmegaEntityInterface

        send_mock = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(UniMessage, 'send', send_mock)

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id='TEST_SEND_BOT_1', base=Bot, adapter=adapter, auto_connect=False)

            driver_bots = nonebot.get_driver().bots
            driver_bots['TEST_SEND_BOT_1'] = bot
            try:
                interface = OmegaEntityInterface(entity_params=_make_entity_init_params(
                    bot_type='OneBot V11', bot_id='TEST_SEND_BOT_1', entity_type='onebot_v11_group', entity_id='10000',
                ))

                await interface.send_entity_message('hello', at_sender=True)

                send_mock.assert_awaited_once()
                kwargs = send_mock.await_args.kwargs
                assert kwargs['bot'] is bot
                assert kwargs['at_sender'] is True
                assert kwargs['target'].id == '10000'
                assert kwargs['target'].private is False
            finally:
                driver_bots.pop('TEST_SEND_BOT_1', None)

    async def test_send_entity_message_auto_revoke_recalls(self, app: App, monkeypatch: pytest.MonkeyPatch) -> None:
        from nonebot.adapters.console import Adapter
        from nonebot.adapters.console import Bot as ConsoleBot
        from nonebot_plugin_alconna.uniseg import UniMessage
        from nonechat.model import Robot

        from src.service.omega_base import OmegaEntityInterface

        receipt = MagicMock()
        receipt.recall = AsyncMock()
        send_mock = AsyncMock(return_value=receipt)
        monkeypatch.setattr(UniMessage, 'send', send_mock)

        async with app.test_api():
            adapter = nonebot.get_adapter(Adapter)
            # Console Bot 构造签名与 create_bot 不兼容, 手动构造 (同 test_010 模式)
            bot = ConsoleBot(adapter=adapter, info=Robot(id='TEST_SEND_BOT_2'))

            driver_bots = nonebot.get_driver().bots
            driver_bots['TEST_SEND_BOT_2'] = bot
            try:
                interface = OmegaEntityInterface(entity_params=_make_entity_init_params(
                    bot_id='TEST_SEND_BOT_2',
                ))

                await interface.send_entity_message_auto_revoke('hello', revoke_delay=3)

                send_mock.assert_awaited_once()
                receipt.recall.assert_awaited_once_with(delay=3)
            finally:
                driver_bots.pop('TEST_SEND_BOT_2', None)

    async def test_console_get_entity_name_and_profile(self) -> None:
        from src.service.omega_base import OmegaEntityInterface

        named = OmegaEntityInterface(entity_params=_make_entity_init_params(entity_name='tester'))
        unnamed = OmegaEntityInterface(entity_params=_make_entity_init_params(entity_name=None))

        assert await named.get_entity_name() == 'tester'
        assert await unnamed.get_entity_name() == 'ConsoleUser'
        assert await named.get_entity_profile_image_url() == ''

    async def test_entity_name_and_profile_delegate_to_registered_target(
            self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """get_entity_name/get_entity_profile_image_url 应经注册表解析的目标类委派平台 API"""
        from src.service.omega_base import OmegaEntityInterface
        from src.service.omega_base.middlewares.onebot_v11 import OneBotV11UserEntityTarget

        name_mock = AsyncMock(return_value='mocked_name')
        profile_mock = AsyncMock(return_value='https://example.com/p.png')
        monkeypatch.setattr(OneBotV11UserEntityTarget, 'call_api_get_entity_name', name_mock)
        monkeypatch.setattr(OneBotV11UserEntityTarget, 'call_api_get_entity_profile_image_url', profile_mock)

        interface = OmegaEntityInterface(entity_params=_make_entity_init_params(
            bot_type='OneBot V11', entity_type='onebot_v11_user', bot_id='10086', entity_id='10001',
        ))

        assert await interface.get_entity_name() == 'mocked_name'
        assert await interface.get_entity_profile_image_url() == 'https://example.com/p.png'
        name_mock.assert_awaited_once()
        profile_mock.assert_awaited_once()


class TestMiddlewareEntityTargets:
    """平台中间件 EntityTarget 适配器测试"""

    async def test_obv11_user_target_construction(self) -> None:
        from nonebot_plugin_alconna.uniseg import SupportScope

        from src.service.omega_base.middlewares.onebot_v11 import OneBotV11UserEntityTarget

        target = OneBotV11UserEntityTarget(entity_params=_make_entity_init_params(
            bot_type='OneBot V11', entity_type='onebot_v11_user', bot_id='10086', entity_id='10001',
        ))

        platform_target = target._construct_target()

        assert platform_target.id == '10001'
        assert platform_target.private is True
        assert platform_target.self_id == '10086'
        assert platform_target.scope == SupportScope.qq_client

    async def test_obv11_group_target_construction(self) -> None:
        from src.service.omega_base.middlewares.onebot_v11 import OneBotV11GroupEntityTarget

        target = OneBotV11GroupEntityTarget(entity_params=_make_entity_init_params(
            bot_type='OneBot V11', entity_type='onebot_v11_group', bot_id='10086', entity_id='10000',
        ))

        platform_target = target._construct_target()

        assert platform_target.id == '10000'
        assert platform_target.private is False

    async def test_telegram_target_is_private_defaults_by_entity_type(self) -> None:
        """entity_extra 缺少 is_private 键时应按 entity_type 推断而非抛出 KeyError"""
        from src.service.omega_base.middlewares.telegram import TelegramGroupEntityTarget, TelegramUserEntityTarget

        user_params = _make_entity_init_params(
            bot_type='Telegram', entity_type='telegram_user', bot_id='TG_BOT', entity_id='TG_USER', entity_extra={},
        )
        group_params = _make_entity_init_params(
            bot_type='Telegram', entity_type='telegram_group', bot_id='TG_BOT', entity_id='TG_GROUP', entity_extra={},
        )

        user_target = TelegramUserEntityTarget(entity_params=user_params)._construct_target()
        group_target = TelegramGroupEntityTarget(entity_params=group_params)._construct_target()

        assert user_target.private is True
        assert group_target.private is False

    async def test_telegram_target_honors_explicit_extra(self) -> None:
        from src.service.omega_base.middlewares.telegram import TelegramGroupEntityTarget

        params = _make_entity_init_params(
            bot_type='Telegram',
            entity_type='telegram_group',
            bot_id='TG_BOT',
            entity_id='TG_GROUP',
            entity_extra={'is_private': True, 'message_thread_id': 42},
        )

        platform_target = TelegramGroupEntityTarget(entity_params=params)._construct_target()

        assert platform_target.private is True
        assert platform_target.extra.get('message_thread_id') == 42

    async def test_console_targets_construction(self) -> None:
        from src.service.omega_base.middlewares.console import ConsoleChannelEntityTarget, ConsoleUserEntityTarget

        user_target = ConsoleUserEntityTarget(entity_params=_make_entity_init_params())._construct_target()
        channel_target = ConsoleChannelEntityTarget(
            entity_params=_make_entity_init_params(entity_type='console_channel'),
        )._construct_target()

        assert user_target.private is True
        assert channel_target.private is False

    async def test_obv11_user_profile_image_url_versions(self) -> None:
        from src.service.omega_base.middlewares.onebot_v11 import OneBotV11UserEntityTarget

        target = OneBotV11UserEntityTarget(entity_params=_make_entity_init_params(
            bot_type='OneBot V11', entity_type='onebot_v11_user', entity_id='10001',
        ))

        assert await target.call_api_get_entity_profile_image_url() == (
            'https://q1.qlogo.cn/g?b=qq&nk=10001&s=5'
        )
        assert await target.call_api_get_entity_profile_image_url(url_version=1, head_img_size=100) == (
            'https://q2.qlogo.cn/headimg_dl?dst_uin=10001&spec=100'
        )
        assert await target.call_api_get_entity_profile_image_url(url_version=2) == (
            'https://users.qzone.qq.com/fcg-bin/cgi_get_portrait.fcg?uins=10001'
        )

    async def test_obv11_group_profile_image_url(self) -> None:
        from src.service.omega_base.middlewares.onebot_v11 import OneBotV11GroupEntityTarget

        target = OneBotV11GroupEntityTarget(entity_params=_make_entity_init_params(
            bot_type='OneBot V11', entity_type='onebot_v11_group', entity_id='10000',
        ))

        assert await target.call_api_get_entity_profile_image_url(head_img_size=140) == (
            'https://p.qlogo.cn/gh/10000/10000/140/'
        )

    async def test_obv11_get_entity_name_via_api(self, app: App) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot

        from src.service.omega_base import OmegaEntityInterface

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id='TEST_NAME_BOT_1', base=Bot, adapter=adapter, auto_connect=False)

            driver_bots = nonebot.get_driver().bots
            driver_bots['TEST_NAME_BOT_1'] = bot
            try:
                ctx.should_call_api('get_stranger_info', {'user_id': '10001'}, {'nickname': '测试用户'})

                interface = OmegaEntityInterface(entity_params=_make_entity_init_params(
                    bot_type='OneBot V11',
                    bot_id='TEST_NAME_BOT_1',
                    entity_type='onebot_v11_user',
                    entity_id='10001',
                ))

                assert await interface.get_entity_name() == '测试用户'
            finally:
                driver_bots.pop('TEST_NAME_BOT_1', None)

    async def test_telegram_get_entity_name_via_api(self, app: App) -> None:
        from nonebot.adapters.telegram import Adapter, Bot
        from nonebot.adapters.telegram.config import BotConfig as TelegramBotConfig

        from src.service.omega_base import OmegaEntityInterface

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(
                self_id='TEST_NAME_BOT_2',
                base=Bot,
                adapter=adapter,
                auto_connect=False,
                config=TelegramBotConfig(token='123456:TEST_TOKEN'),
            )

            driver_bots = nonebot.get_driver().bots
            driver_bots['TEST_NAME_BOT_2'] = bot
            try:
                ctx.should_call_api(
                    'get_chat',
                    {'chat_id': '-1001234567'},
                    {
                        'id': -1001234567,
                        'type': 'group',
                        'title': '群标题',
                        'accent_color_id': 0,
                        'max_reaction_count': 10,
                    },
                )

                interface = OmegaEntityInterface(entity_params=_make_entity_init_params(
                    bot_type='Telegram',
                    bot_id='TEST_NAME_BOT_2',
                    entity_type='telegram_group',
                    entity_id='-1001234567',
                ))

                assert await interface.get_entity_name() == '群标题'
            finally:
                driver_bots.pop('TEST_NAME_BOT_2', None)

    async def test_telegram_get_entity_name_falls_back_to_first_name(self, app: App) -> None:
        from nonebot.adapters.telegram import Adapter, Bot
        from nonebot.adapters.telegram.config import BotConfig as TelegramBotConfig

        from src.service.omega_base.middlewares.telegram import TelegramUserEntityTarget

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(
                self_id='TEST_NAME_BOT_3',
                base=Bot,
                adapter=adapter,
                auto_connect=False,
                config=TelegramBotConfig(token='123456:TEST_TOKEN'),
            )

            driver_bots = nonebot.get_driver().bots
            driver_bots['TEST_NAME_BOT_3'] = bot
            try:
                ctx.should_call_api(
                    'get_chat',
                    {'chat_id': '10001'},
                    {
                        'id': 10001,
                        'type': 'private',
                        'first_name': '名字',
                        'accent_color_id': 0,
                        'max_reaction_count': 10,
                    },
                )

                target = TelegramUserEntityTarget(entity_params=_make_entity_init_params(
                    bot_type='Telegram', bot_id='TEST_NAME_BOT_3', entity_type='telegram_user', entity_id='10001',
                ))

                assert await target.call_api_get_entity_name() == '名字'
            finally:
                driver_bots.pop('TEST_NAME_BOT_3', None)

    async def test_telegram_profile_image_url_without_photo_raises(self, app: App) -> None:
        from nonebot.adapters.telegram import Adapter, Bot
        from nonebot.adapters.telegram.config import BotConfig as TelegramBotConfig

        from src.service.omega_base.middlewares.telegram import TelegramUserEntityTarget

        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(
                self_id='TEST_NAME_BOT_4',
                base=Bot,
                adapter=adapter,
                auto_connect=False,
                config=TelegramBotConfig(token='123456:TEST_TOKEN'),
            )

            driver_bots = nonebot.get_driver().bots
            driver_bots['TEST_NAME_BOT_4'] = bot
            try:
                ctx.should_call_api(
                    'get_chat',
                    {'chat_id': '10001'},
                    {
                        'id': 10001,
                        'type': 'private',
                        'first_name': '名字',
                        'accent_color_id': 0,
                        'max_reaction_count': 10,
                    },
                )

                target = TelegramUserEntityTarget(entity_params=_make_entity_init_params(
                    bot_type='Telegram', bot_id='TEST_NAME_BOT_4', entity_type='telegram_user', entity_id='10001',
                ))

                with pytest.raises(ValueError, match='no photo'):
                    await target.call_api_get_entity_profile_image_url()
            finally:
                driver_bots.pop('TEST_NAME_BOT_4', None)


class TestOmegaMatcherInterface:
    """OmegaMatcherInterface 事件接口测试"""

    def test_constructor_defaults(self) -> None:
        from src.service.omega_base import OmegaMatcherInterface

        bot, event, matcher = _make_mock_bot(), _make_obv11_group_message_event(), MagicMock()

        interface = OmegaMatcherInterface(bot=bot, event=event, matcher=matcher)

        assert interface.bot is bot
        assert interface.event is event
        assert interface.matcher is matcher
        assert interface.acquire_type == 'event'

    def test_depend_factory(self) -> None:
        from src.service.omega_base import OmegaMatcherInterface

        bot, event, matcher = _make_mock_bot(), _make_obv11_group_message_event(), MagicMock()

        depend_callable = OmegaMatcherInterface.depend(acquire_type='user')
        interface = depend_callable(bot, event, matcher)

        assert isinstance(interface, OmegaMatcherInterface)
        assert interface.bot is bot
        assert interface.event is event
        assert interface.matcher is matcher
        assert interface.acquire_type == 'user'

    def test_get_event_depend_cls_resolves(self) -> None:
        from src.service.omega_base import OmegaMatcherInterface
        from src.service.omega_base.middlewares.onebot_v11 import (
            OneBotV11EventDepend,
            OneBotV11GroupMessageEventDepend,
            OneBotV11PokeNotifyEventDepend,
            OneBotV11PrivateMessageEventDepend,
        )

        assert OmegaMatcherInterface.get_event_depend_cls(
            target_event=_make_obv11_group_message_event(),
        ) is OneBotV11GroupMessageEventDepend
        assert OmegaMatcherInterface.get_event_depend_cls(
            target_event=_make_obv11_private_message_event(),
        ) is OneBotV11PrivateMessageEventDepend
        assert OmegaMatcherInterface.get_event_depend_cls(
            target_event=_make_obv11_poke_notify_event(),
        ) is OneBotV11PokeNotifyEventDepend
        # 精确类与中间抽象类均未注册时按 MRO 解析到基类注册
        assert OmegaMatcherInterface.get_event_depend_cls(
            target_event=_make_obv11_friend_recall_notice_event(),
        ) is OneBotV11EventDepend

    def test_get_event_depend_cls_unsupported_rejected(self) -> None:
        from src.service.omega_base import OmegaMatcherInterface
        from src.service.omega_base.internal import OmegaBaseEvent

        with pytest.raises(ValueError, match='Event not supported'):
            OmegaMatcherInterface.get_event_depend_cls(target_event=OmegaBaseEvent(event_type='x'))

    def test_get_event_depend_wires_bot_and_event(self) -> None:
        from src.service.omega_base import OmegaMatcherInterface
        from src.service.omega_base.middlewares.onebot_v11 import OneBotV11GroupMessageEventDepend

        bot = _make_mock_bot()
        event = _make_obv11_group_message_event()
        interface = OmegaMatcherInterface(bot=bot, event=event, matcher=MagicMock())

        depend = interface.get_event_depend()

        assert isinstance(depend, OneBotV11GroupMessageEventDepend)
        assert depend.bot is bot
        assert depend.event is event

    def test_extract_current_entity_params_event_and_user(self) -> None:
        from src.database.internal.entity import EntityType
        from src.service.omega_base import OmegaMatcherInterface

        event = _make_obv11_group_message_event(group_id=20000, user_id=30001, nickname='nick')

        event_params = OmegaMatcherInterface(
            bot=_make_mock_bot(), event=event, matcher=MagicMock(),
        ).extract_current_entity_params()
        user_params = OmegaMatcherInterface(
            bot=_make_mock_bot(), event=event, matcher=MagicMock(), acquire_type='user',
        ).extract_current_entity_params()

        assert event_params.entity_type is EntityType.ONEBOT_V11_GROUP
        assert event_params.entity_id == '20000'
        assert user_params.entity_type is EntityType.ONEBOT_V11_USER
        assert user_params.entity_id == '30001'
        assert user_params.entity_name == 'nick'

    def test_get_current_entity_interface(self) -> None:
        from src.service.omega_base import OmegaEntityInterface, OmegaMatcherInterface

        interface = OmegaMatcherInterface(
            bot=_make_mock_bot(), event=_make_obv11_group_message_event(group_id=20000), matcher=MagicMock(),
        )

        entity_interface = interface.get_current_entity_interface()

        assert isinstance(entity_interface, OmegaEntityInterface)
        assert entity_interface.type is entity_interface.entity_params.entity_type
        assert entity_interface.entity_params.entity_id == '20000'

    async def test_get_current_entity_without_db_access(self) -> None:
        from src.database.internal.entity import EntityType
        from src.service.omega_base import OmegaMatcherInterface
        from src.service.omega_base.internal import OmegaEntity

        interface = OmegaMatcherInterface(
            bot=_make_mock_bot(),
            event=_make_obv11_group_message_event(group_id=20000, user_id=30001),
            matcher=MagicMock(),
        )

        entity = interface.get_current_entity(db_session=MagicMock())

        assert isinstance(entity, OmegaEntity)
        assert entity.entity_type is EntityType.ONEBOT_V11_GROUP
        assert entity.entity_id == '20000'
        assert entity.not_init is True

    async def test_create_current_entity_session_persists(self, app: App, test_onebot_v11_bot) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot

        from src.database.internal.bot import BotType
        from src.database.internal.entity import EntityDAL
        from src.service.omega_base import OmegaMatcherInterface

        group_id = random.randint(10_000_000, 99_999_999)
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id=test_onebot_v11_bot.self_id, base=Bot, adapter=adapter, auto_connect=False)

            interface = OmegaMatcherInterface(
                bot=bot, event=_make_obv11_group_message_event(group_id=group_id), matcher=MagicMock(),
            )

            async with interface.create_current_entity_session() as entity:
                assert entity.not_init is True

                created = await entity.query_entity_self()

                assert created.entity_id == str(group_id)

        # 会话退出时提交, 新会话中应能查询到自动创建的 Entity
        async with EntityDAL.create() as dal:
            row = await dal.query_unique(
                bot_type=BotType.ONEBOT_V11,
                bot_self_id=test_onebot_v11_bot.self_id,
                entity_type='onebot_v11_group',
                entity_id=str(group_id),
            )

        assert row.entity_id == str(group_id)

    async def test_create_current_entity_session_rolls_back_on_error(
            self, app: App, test_onebot_v11_bot,
    ) -> None:
        from nonebot.adapters.onebot.v11 import Adapter, Bot
        from sqlalchemy.exc import NoResultFound

        from src.database.internal.bot import BotType
        from src.database.internal.entity import EntityDAL
        from src.service.omega_base import OmegaMatcherInterface

        group_id = random.randint(10_000_000, 99_999_999)
        async with app.test_api() as ctx:
            adapter = nonebot.get_adapter(Adapter)
            bot = ctx.create_bot(self_id=test_onebot_v11_bot.self_id, base=Bot, adapter=adapter, auto_connect=False)

            interface = OmegaMatcherInterface(
                bot=bot, event=_make_obv11_group_message_event(group_id=group_id), matcher=MagicMock(),
            )

            async def _raise_inside_session() -> None:
                async with interface.create_current_entity_session() as entity:
                    await entity.query_entity_self()
                    raise RuntimeError('boom')

            # 异常需经上下文管理器退出, 才能触发 database_session 的回滚
            with pytest.raises(RuntimeError, match='boom'):
                await _raise_inside_session()

        async with EntityDAL.create() as dal:
            with pytest.raises(NoResultFound):
                await dal.query_unique(
                    bot_type=BotType.ONEBOT_V11,
                    bot_self_id=test_onebot_v11_bot.self_id,
                    entity_type='onebot_v11_group',
                    entity_id=str(group_id),
                )

    @staticmethod
    def _make_interface_with_mocked_depend(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, MagicMock]:
        """构造 get_event_depend 被 mock 的接口实例, 返回 (interface, mock_depend)

        OmegaMatcherInterface 定义了 __slots__, 禁止实例级替换方法, 故用类级 monkeypatch
        """
        from src.service.omega_base import OmegaMatcherInterface

        interface = OmegaMatcherInterface(
            bot=_make_mock_bot(), event=_make_obv11_group_message_event(), matcher=MagicMock(),
        )
        mock_depend = MagicMock()
        mock_depend.send = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(OmegaMatcherInterface, 'get_event_depend', lambda self: mock_depend)
        return interface, mock_depend

    async def test_send_delegation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        interface, mock_depend = self._make_interface_with_mocked_depend(monkeypatch)

        await interface.send('msg')
        await interface.send_at_sender('msg')
        await interface.send_reply('msg')

        assert mock_depend.send.await_count == 3
        assert mock_depend.send.await_args_list[0].kwargs == {'message': 'msg', 'at_sender': False, 'reply_to': False}
        assert mock_depend.send.await_args_list[1].kwargs['at_sender'] is True
        assert mock_depend.send.await_args_list[2].kwargs['reply_to'] is True

    async def test_send_auto_revoke_recalls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        interface, mock_depend = self._make_interface_with_mocked_depend(monkeypatch)

        receipt = MagicMock()
        receipt.recall = AsyncMock()
        mock_depend.send = AsyncMock(return_value=receipt)
        mock_depend.revoke_bot_sent_msg = AsyncMock()

        await interface.send_auto_revoke('msg', revoke_delay=7)

        mock_depend.send.assert_awaited_once()
        mock_depend.revoke_bot_sent_msg.assert_awaited_once()
        assert mock_depend.revoke_bot_sent_msg.await_args.kwargs['revoke_delay'] == 7

    async def test_finish_raises_after_send(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nonebot.exception import FinishedException

        interface, mock_depend = self._make_interface_with_mocked_depend(monkeypatch)

        with pytest.raises(FinishedException):
            await interface.finish('done')

        mock_depend.send.assert_awaited_once()

    async def test_pause_raises_after_send(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nonebot.exception import PausedException

        interface, mock_depend = self._make_interface_with_mocked_depend(monkeypatch)

        with pytest.raises(PausedException):
            await interface.pause_at_sender('wait')

        mock_depend.send.assert_awaited_once()

    async def test_reject_raises_after_send(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nonebot.exception import RejectedException

        interface, mock_depend = self._make_interface_with_mocked_depend(monkeypatch)

        with pytest.raises(RejectedException):
            await interface.reject_reply('retry')

        mock_depend.send.assert_awaited_once()

    async def test_reject_arg_delegates_to_matcher(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nonebot.exception import RejectedException

        from src.service.omega_base import OmegaMatcherInterface

        matcher = MagicMock()
        matcher.reject_arg = AsyncMock(side_effect=RejectedException)
        interface = OmegaMatcherInterface(
            bot=_make_mock_bot(), event=_make_obv11_group_message_event(), matcher=matcher,
        )
        mock_depend = MagicMock()
        mock_depend.send = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(OmegaMatcherInterface, 'get_event_depend', lambda self: mock_depend)

        with pytest.raises(RejectedException):
            await interface.reject_arg('key', 'retry')

        mock_depend.send.assert_awaited_once()
        matcher.reject_arg.assert_awaited_once_with('key')

    async def test_reject_receive_delegates_to_matcher(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from nonebot.exception import RejectedException

        from src.service.omega_base import OmegaMatcherInterface

        matcher = MagicMock()
        matcher.reject_receive = AsyncMock(side_effect=RejectedException)
        interface = OmegaMatcherInterface(
            bot=_make_mock_bot(), event=_make_obv11_group_message_event(), matcher=matcher,
        )
        mock_depend = MagicMock()
        mock_depend.send = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(OmegaMatcherInterface, 'get_event_depend', lambda self: mock_depend)

        with pytest.raises(RejectedException):
            await interface.reject_receive('key', 'retry')

        mock_depend.send.assert_awaited_once()
        matcher.reject_receive.assert_awaited_once_with('key')

    async def test_get_target_entity_classmethod(self) -> None:
        """get_target_entity 类方法应经事件解析参数并以给定会话构造 OmegaEntity"""
        from src.database.internal.entity import EntityType
        from src.service.omega_base import OmegaMatcherInterface
        from src.service.omega_base.internal import OmegaEntity

        entity = OmegaMatcherInterface.get_target_entity(
            bot=_make_mock_bot(),
            event=_make_obv11_group_message_event(group_id=20000, user_id=30001),
            db_session=MagicMock(),
            acquire_type='user',
        )

        assert isinstance(entity, OmegaEntity)
        assert entity.entity_type is EntityType.ONEBOT_V11_USER
        assert entity.entity_id == '30001'
        assert entity.not_init is True

    async def test_send_auto_revoke_default_delay(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """send_auto_revoke 默认撤回延迟应与基类适配器一致 (60 秒)"""
        interface, mock_depend = self._make_interface_with_mocked_depend(monkeypatch)
        mock_depend.revoke_bot_sent_msg = AsyncMock()

        await interface.send_auto_revoke('msg')

        assert mock_depend.revoke_bot_sent_msg.await_args.kwargs['revoke_delay'] == 60

    @pytest.mark.parametrize(
        ('method_name', 'expected_exception', 'expected_flags'),
        [
            ('finish', FinishedException, {'at_sender': False, 'reply_to': False}),
            ('finish_at_sender', FinishedException, {'at_sender': True, 'reply_to': False}),
            ('finish_reply', FinishedException, {'at_sender': False, 'reply_to': True}),
            ('pause', PausedException, {'at_sender': False, 'reply_to': False}),
            ('pause_at_sender', PausedException, {'at_sender': True, 'reply_to': False}),
            ('pause_reply', PausedException, {'at_sender': False, 'reply_to': True}),
            ('reject', RejectedException, {'at_sender': False, 'reply_to': False}),
            ('reject_at_sender', RejectedException, {'at_sender': True, 'reply_to': False}),
            ('reject_reply', RejectedException, {'at_sender': False, 'reply_to': True}),
        ],
    )
    async def test_flow_control_variants(
            self,
            monkeypatch: pytest.MonkeyPatch,
            method_name: str,
            expected_exception: type[Exception],
            expected_flags: dict[str, bool],
    ) -> None:
        """finish/pause/reject 各变体均应先发送消息 (flags 正确), 再抛出对应流程控制异常"""
        interface, mock_depend = self._make_interface_with_mocked_depend(monkeypatch)

        with pytest.raises(expected_exception):
            await getattr(interface, method_name)('msg')

        mock_depend.send.assert_awaited_once()
        call_kwargs = mock_depend.send.await_args.kwargs
        assert call_kwargs['at_sender'] is expected_flags['at_sender']
        assert call_kwargs['reply_to'] is expected_flags['reply_to']

    @pytest.mark.parametrize(
        ('method_name', 'matcher_method', 'expected_flags'),
        [
            ('reject_arg', 'reject_arg', {'at_sender': False, 'reply_to': False}),
            ('reject_arg_at_sender', 'reject_arg', {'at_sender': True, 'reply_to': False}),
            ('reject_arg_reply', 'reject_arg', {'at_sender': False, 'reply_to': True}),
            ('reject_receive', 'reject_receive', {'at_sender': False, 'reply_to': False}),
            ('reject_receive_at_sender', 'reject_receive', {'at_sender': True, 'reply_to': False}),
            ('reject_receive_reply', 'reject_receive', {'at_sender': False, 'reply_to': True}),
        ],
    )
    async def test_reject_key_variants(
            self,
            monkeypatch: pytest.MonkeyPatch,
            method_name: str,
            matcher_method: str,
            expected_flags: dict[str, bool],
    ) -> None:
        """reject_arg/reject_receive 各变体均应先发送消息 (flags 正确), 再以相同 key 委托 matcher"""
        from src.service.omega_base import OmegaMatcherInterface

        matcher = MagicMock()
        matcher.reject_arg = AsyncMock(side_effect=RejectedException)
        matcher.reject_receive = AsyncMock(side_effect=RejectedException)
        interface = OmegaMatcherInterface(
            bot=_make_mock_bot(), event=_make_obv11_group_message_event(), matcher=matcher,
        )
        mock_depend = MagicMock()
        mock_depend.send = AsyncMock(return_value=MagicMock())
        monkeypatch.setattr(OmegaMatcherInterface, 'get_event_depend', lambda self: mock_depend)

        with pytest.raises(RejectedException):
            await getattr(interface, method_name)('key', 'msg')

        mock_depend.send.assert_awaited_once()
        call_kwargs = mock_depend.send.await_args.kwargs
        assert call_kwargs['at_sender'] is expected_flags['at_sender']
        assert call_kwargs['reply_to'] is expected_flags['reply_to']
        getattr(matcher, matcher_method).assert_awaited_once_with('key')


class TestOneBotV11EventDepends:
    """OneBot V11 中间件 EventDepend 提取逻辑测试"""

    @staticmethod
    def _make_depend(event: 'BaseEvent') -> Any:
        from src.service.omega_base import OmegaMatcherInterface

        depend_cls = OmegaMatcherInterface.get_event_depend_cls(target_event=event)
        return depend_cls(bot=_make_mock_bot('OneBot V11'), event=event)

    async def test_group_message_event_params(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_obv11_group_message_event(group_id=20000, user_id=30001))

        params = depend.extract_entity_params('event')

        assert params.entity_type is EntityType.ONEBOT_V11_GROUP
        assert params.entity_id == '20000'
        assert params.entity_name == 'Unknown'

    async def test_private_message_event_params_fallback_to_user(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_obv11_private_message_event(user_id=30001, nickname='nick'))

        params = depend.extract_entity_params('event')

        assert params.entity_type is EntityType.ONEBOT_V11_USER
        assert params.entity_id == '30001'
        assert params.entity_name == 'nick'

    async def test_meta_event_user_extraction_raises(self) -> None:
        depend = self._make_depend(_make_obv11_meta_event())

        with pytest.raises(NotImplementedError):
            depend.extract_entity_params('user')

    async def test_notify_event_params(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_obv11_honor_notify_event(group_id=20000, user_id=30001))

        event_params = depend.extract_entity_params('event')
        user_params = depend.extract_entity_params('user')

        assert event_params.entity_type is EntityType.ONEBOT_V11_GROUP
        assert event_params.entity_id == '20000'
        assert user_params.entity_type is EntityType.ONEBOT_V11_USER
        assert user_params.entity_id == '30001'

    async def test_notify_event_without_group_falls_back_to_user(self) -> None:
        """group_id 为空的 notify 事件应回退到用户对象, 不产生 entity_id='None' 的污染数据

        PokeNotifyEvent 经注册表解析到专属 Depend, 此处直接实例化基类 Depend 验证其空值防御
        """
        from src.database.internal.entity import EntityType
        from src.service.omega_base.middlewares.onebot_v11 import OneBotV11NotifyEventDepend

        event = _make_obv11_poke_notify_event(group_id=None, user_id=30001)
        depend = OneBotV11NotifyEventDepend(bot=_make_mock_bot('OneBot V11'), event=event)

        event_params = depend.extract_entity_params('event')

        assert event_params.entity_type is EntityType.ONEBOT_V11_USER
        assert event_params.entity_id == '30001'

    async def test_private_poke_event_params_fallback_to_user(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_obv11_poke_notify_event(group_id=None, user_id=30001))

        event_params = depend.extract_entity_params('event')

        assert event_params.entity_type is EntityType.ONEBOT_V11_USER
        assert event_params.entity_id == '30001'

    async def test_group_poke_event_params(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_obv11_poke_notify_event(group_id=20000, user_id=30001))

        event_params = depend.extract_entity_params('event')

        assert event_params.entity_type is EntityType.ONEBOT_V11_GROUP
        assert event_params.entity_id == '20000'

    async def test_group_message_user_params_include_sender_dump(self) -> None:
        from nonebot.adapters.onebot.v11.event import Sender

        depend = self._make_depend(_make_obv11_group_message_event(
            group_id=20000, user_id=30001, nickname='nick', card='card',
        ))

        user_params = depend.extract_entity_params('user')

        assert user_params.entity_id == '30001'
        assert user_params.entity_name == 'nick'
        assert user_params.entity_extra == Sender(user_id=30001, nickname='nick', card='card').model_dump()

    async def test_get_user_nickname_prefers_card(self) -> None:
        depend = self._make_depend(_make_obv11_group_message_event(nickname='nick', card='card'))

        assert depend.get_user_nickname() == 'card'

    async def test_get_user_nickname_empty_fallback(self) -> None:
        depend = self._make_depend(_make_obv11_group_message_event(nickname=None, card=None))

        assert depend.get_user_nickname() == ''

    async def test_get_reply_msg_image_urls(self) -> None:
        """回复消息中的图片链接应从 event.reply 提取, 无 url 的图片段被过滤"""
        from nonebot.adapters.onebot.v11 import Message, MessageSegment
        from nonebot.adapters.onebot.v11.event import Reply as Obv11Reply
        from nonebot.adapters.onebot.v11.event import Sender

        reply = Obv11Reply(
            time=1,
            message_type='group',
            message_id=111,
            real_id=111,
            sender=Sender(user_id=1),
            message=Message([
                MessageSegment('image', {'file': '1.jpg', 'url': 'https://example.com/1.jpg'}),
                MessageSegment('image', {'file': '2.jpg'}),
                MessageSegment.text('text'),
            ]),
        )
        depend = self._make_depend(_make_obv11_group_message_event(reply=reply))

        assert depend.get_reply_msg_image_urls() == ['https://example.com/1.jpg']

    async def test_get_reply_msg_image_urls_without_reply(self) -> None:
        depend = self._make_depend(_make_obv11_group_message_event(reply=None))

        assert depend.get_reply_msg_image_urls() == []

    async def test_get_reply_msg_image_urls_text_only_reply(self) -> None:
        from nonebot.adapters.onebot.v11 import Message
        from nonebot.adapters.onebot.v11.event import Reply as Obv11Reply
        from nonebot.adapters.onebot.v11.event import Sender

        reply = Obv11Reply(
            time=1,
            message_type='group',
            message_id=111,
            real_id=111,
            sender=Sender(user_id=1),
            message=Message('text only'),
        )
        depend = self._make_depend(_make_obv11_group_message_event(reply=reply))

        assert depend.get_reply_msg_image_urls() == []


class TestTelegramEventDepends:
    """Telegram 中间件 EventDepend 提取逻辑测试"""

    @staticmethod
    def _make_depend(event: 'BaseEvent') -> Any:
        from src.service.omega_base import OmegaMatcherInterface

        depend_cls = OmegaMatcherInterface.get_event_depend_cls(target_event=event)
        return depend_cls(bot=_make_mock_bot('Telegram'), event=event)

    async def test_group_message_event_params(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_telegram_message_event('group'))

        params = depend.extract_entity_params('event')

        assert params.entity_type is EntityType.TELEGRAM_GROUP
        assert params.entity_id == '-1001234567'
        assert params.entity_name == 'Test Chat'
        assert params.entity_extra == {'is_private': False, 'message_thread_id': None}
        assert params.entity_info == 'group'

    async def test_group_message_user_params_with_username(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_telegram_message_event('group', username='tester'))

        params = depend.extract_entity_params('user')

        assert params.entity_type is EntityType.TELEGRAM_USER
        assert params.entity_id == '10001'
        assert params.entity_name == 'Tester'
        assert params.entity_info == 'Tester@tester'
        assert params.entity_extra == {'is_private': False, 'message_thread_id': None}

    async def test_group_message_user_params_without_username(self) -> None:
        """username 为 None 时 entity_info 不应产生 'Name@None' 形式"""
        depend = self._make_depend(_make_telegram_message_event('group', username=None))

        params = depend.extract_entity_params('user')

        assert params.entity_info == 'Tester'

    async def test_private_message_params(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_telegram_message_event('private', username=None))

        event_params = depend.extract_entity_params('event')
        user_params = depend.extract_entity_params('user')

        assert event_params.entity_type is EntityType.TELEGRAM_USER
        assert event_params.entity_extra == {'is_private': True, 'message_thread_id': None}
        assert user_params.entity_id == '10001'
        assert user_params.entity_info == 'Tester'

    async def test_channel_post_user_params_fallback_to_channel(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_telegram_message_event('channel'))

        event_params = depend.extract_entity_params('event')
        user_params = depend.extract_entity_params('user')

        assert event_params.entity_type is EntityType.TELEGRAM_CHANNEL
        assert event_params.entity_id == '-1001234567'
        assert user_params == event_params

    async def test_base_event_depend_user_maps_to_bot_self(self) -> None:
        from src.database.internal.entity import EntityType
        from src.service.omega_base.middlewares.telegram import TelegramEventDepend

        bot = _make_mock_bot('Telegram')
        bot.self_id = 'TG_BOT_SELF'
        depend = TelegramEventDepend(bot=bot, event=_make_telegram_message_event('group'))

        params = depend.extract_entity_params('user')

        assert params.entity_type is EntityType.TELEGRAM_USER
        assert params.entity_id == 'TG_BOT_SELF'
        assert params.entity_name == 'Telegram Bot Self'

    async def test_get_user_nickname_variants(self) -> None:
        """基类 TelegramMessageEventDepend 的昵称取 chat.username (具体子类均覆写为 from_.first_name)"""
        from src.service.omega_base.middlewares.telegram import TelegramMessageEventDepend

        chat_with_username = _make_telegram_message_event('group', chat_username='tester')
        chat_without_username = _make_telegram_message_event('group', chat_username=None)

        depend_with = TelegramMessageEventDepend(bot=_make_mock_bot('Telegram'), event=chat_with_username)
        depend_without = TelegramMessageEventDepend(bot=_make_mock_bot('Telegram'), event=chat_without_username)

        assert depend_with.get_user_nickname() == 'tester'
        assert depend_without.get_user_nickname() == ''

    async def test_group_depend_get_user_nickname(self) -> None:
        depend = self._make_depend(_make_telegram_message_event('group'))

        assert depend.get_user_nickname() == 'Tester'

    async def test_get_reply_msg_image_urls(self) -> None:
        """回复消息中的图片应从 event.reply_to_message 提取, Telegram 无直接 URL 返回 file_id"""
        reply_message = [
            {'type': 'photo', 'data': {'file': 'file_id_1'}},
            {'type': 'photo', 'data': {'file': 'file_id_2'}},
            {'type': 'text', 'data': {'text': 'text'}},
        ]
        reply_to = {
            'message_id': 2,
            'date': 1,
            'chat': {'id': 10001, 'type': 'private', 'first_name': 'Tester'},
            'from': _make_telegram_user_payload(),
            'message': reply_message,
            # original_message 仅在适配器 parse_event 中填充, 直接 model_validate 需显式提供
            'original_message': reply_message,
        }
        depend = self._make_depend(_make_telegram_message_event('group', reply_to=reply_to))

        assert depend.get_reply_msg_image_urls() == ['file_id_1', 'file_id_2']

    async def test_get_reply_msg_image_urls_without_reply(self) -> None:
        depend = self._make_depend(_make_telegram_message_event('group', reply_to=None))

        assert depend.get_reply_msg_image_urls() == []


class TestConsoleEventDepends:
    """Console 中间件 EventDepend 提取逻辑测试"""

    @staticmethod
    def _make_depend(event: 'BaseEvent') -> Any:
        from src.service.omega_base import OmegaMatcherInterface

        depend_cls = OmegaMatcherInterface.get_event_depend_cls(target_event=event)
        return depend_cls(bot=_make_mock_bot('Console'), event=event)

    async def test_event_params(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_console_message_event(channel_id='channel_1'))

        params = depend.extract_entity_params('event')

        assert params.entity_type is EntityType.CONSOLE_CHANNEL
        assert params.entity_id == 'channel_1'
        assert params.entity_name == '测试频道'
        assert params.entity_info == '频道描述'

    async def test_user_params_public_channel(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_console_message_event(channel_id='channel_1'))

        params = depend.extract_entity_params('user')

        assert params.entity_type is EntityType.CONSOLE_CHANNEL
        assert params.entity_id == 'channel_1'

    async def test_user_params_direct_channel(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_console_message_event(direct=True))

        params = depend.extract_entity_params('user')

        assert params.entity_type is EntityType.CONSOLE_USER
        assert params.entity_id == 'user_1'
        assert params.entity_name == '测试用户'
        assert params.entity_info == '👤'

    async def test_user_params_private_prefix_channel(self) -> None:
        from src.database.internal.entity import EntityType

        depend = self._make_depend(_make_console_message_event(channel_id='private:user_1'))

        params = depend.extract_entity_params('user')

        assert params.entity_type is EntityType.CONSOLE_USER
        assert params.entity_id == 'user_1'

    async def test_get_user_nickname(self) -> None:
        depend = self._make_depend(_make_console_message_event())

        assert depend.get_user_nickname() == '测试用户'

    async def test_get_reply_msg_image_urls(self) -> None:
        depend = self._make_depend(_make_console_message_event())

        assert depend.get_reply_msg_image_urls() == []
