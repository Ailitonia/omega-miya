"""
@Author         : Ailitonia
@Date           : 2026/9/8 19:35
@FileName       : utils
@Project        : omega-miya
@Description    : nonebug 测试工具与共享事件/Bot 构造层
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from collections.abc import AsyncGenerator, Generator, Iterable, Mapping
from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import nonebot
import pytest
from nonebot.adapters import Event, Message, MessageSegment
from pydantic import create_model

if TYPE_CHECKING:
    from nonebot.adapters import Adapter, Bot
    from nonebot.adapters import Event as BaseEvent
    from nonebot.matcher import Matcher

    from src.database.internal.bot import BotSelf
    from src.service.omega_base.internal.entity import EntityInitParams
    from src.service.omega_base.internal.event import OmegaBaseEvent


def unique_test_id(prefix: str) -> str:
    """生成带唯一后缀的测试 ID"""
    return f'{prefix}_{uuid4().hex[:8]}'


def random_numeric_bot_self_id() -> str:
    """生成 8 位随机数字符串 Bot self_id (OneBot V11 事件模型要求数字 ID)"""
    return str(random.randint(10_000_000, 99_999_999))


def rebind_module_namespace(
        monkeypatch: pytest.MonkeyPatch,
        module: ModuleType,
        name: str,
        **overrides: Any,
) -> SimpleNamespace:
    """以 SimpleNamespace 重绑定目标模块命名空间内的名字(继承原对象全部属性, 仅覆盖指定项)

    目标模块内 `import asyncio`/`import time` 之类的名字指向进程共享的全局模块对象,
    直接 patch 其属性会在共享 session 事件循环上殃及常驻组件(如 uvicorn Server.main_loop);
    此处仅替换目标模块内的名字绑定本身, 返回替换后的命名空间以便取用注入的替身
    """
    source = getattr(module, name)
    namespace = SimpleNamespace(**{**vars(source), **overrides})
    monkeypatch.setattr(module, name, namespace)
    return namespace


def escape_text(s: str, *, escape_comma: bool = True) -> str:
    s = s.replace('&', '&amp;').replace('[', '&#91;').replace(']', '&#93;')
    if escape_comma:
        s = s.replace(',', '&#44;')
    return s


def make_fake_message():
    class FakeMessageSegment(MessageSegment):
        @classmethod
        def get_message_class(cls):
            return FakeMessage

        def __str__(self) -> str:
            return self.data['text'] if self.type == 'text' else f'[fake:{self.type}]'

        @classmethod
        def text(cls, text: str):
            return cls('text', {'text': text})

        @staticmethod
        def image(url: str):
            return FakeMessageSegment('image', {'url': url})

        @staticmethod
        def nested(content: 'FakeMessage'):
            return FakeMessageSegment('node', {'content': content})

        def is_text(self) -> bool:
            return self.type == 'text'

    class FakeMessage(Message):
        @classmethod
        def get_segment_class(cls):
            return FakeMessageSegment

        @staticmethod
        def _construct(msg: str | Iterable[Mapping]):
            if isinstance(msg, str):
                yield FakeMessageSegment.text(msg)
            else:
                for seg in msg:
                    yield FakeMessageSegment(**seg)
            return

        def __add__(self, other):
            other = escape_text(other) if isinstance(other, str) else other
            return super().__add__(other)

    return FakeMessage


def make_fake_event(
        _base: type[Event] | None = None,
        _type: str = 'message',
        _name: str = 'test',
        _description: str = 'test',
        _user_id: str | None = 'test',
        _session_id: str | None = 'test',
        _message: Message | None = None,
        _to_me: bool = True,
        **fields,
) -> type[Event]:
    _Fake = create_model('_Fake', __base__=_base or Event, **fields)

    class FakeEvent(_Fake):
        model_config = {'extra': 'forbid'}  # noqa: RUF012

        def get_type(self) -> str:
            return _type

        def get_event_name(self) -> str:
            return _name

        def get_event_description(self) -> str:
            return _description

        def get_user_id(self) -> str:
            if _user_id is not None:
                return _user_id
            raise NotImplementedError

        def get_session_id(self) -> str:
            if _session_id is not None:
                return _session_id
            raise NotImplementedError

        def get_message(self) -> 'Message':
            if _message is not None:
                return _message
            raise NotImplementedError

        def is_tome(self) -> bool:
            return _to_me

    return FakeEvent


# ------------------------------------------------------------------ #
# omega_base / 事件与 Bot 构造族
# ------------------------------------------------------------------ #

def make_entity_init_params(**overrides: Any) -> 'EntityInitParams':
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


def make_mock_bot(*, self_id: str = '10086', adapter_name: str = 'OneBot V11') -> MagicMock:
    """构造轻量 mock Bot, 配置 self_id / adapter.get_name / type / config 属性"""
    bot = MagicMock()
    bot.self_id = self_id
    bot.type = 'fake_adapter'
    bot.adapter.get_name.return_value = adapter_name
    # SUPERUSER 等依赖读取 bot.config, 提供真实 Driver 配置
    bot.config = nonebot.get_driver().config
    return bot


def make_mock_receipt() -> MagicMock:
    """构造带 recall AsyncMock 的 mock Receipt"""
    receipt = MagicMock()
    receipt.recall = AsyncMock()
    return receipt


def make_obv11_reply(
        message: Any,
        *,
        message_type: str = 'group',
        message_id: int = 111,
        real_id: int = 111,
        sender: Any = None,
) -> Any:
    """构造 OneBot V11 回复消息引用对象 (事件 reply 字段)"""
    from nonebot.adapters.onebot.v11.event import Reply, Sender

    return Reply(
        time=1,
        message_type=message_type,
        message_id=message_id,
        real_id=real_id,
        sender=sender if sender is not None else Sender(user_id=1),
        message=message,
    )


def make_obv11_private_message_event(
        *,
        user_id: int = 10001,
        text: str = '/test',
        self_id: int = 10086,
        message_id: int = 1,
        nickname: str | None = 'tester',
        message: Any = None,
        raw_message: str | None = None,
        reply: Any = None,
) -> 'BaseEvent':
    """构造 OneBot V11 私聊消息事件

    message 缺省时由 text 构造纯文本消息; original_message 为 message 的独立副本
    """
    from nonebot.adapters.onebot.v11 import Message
    from nonebot.adapters.onebot.v11.event import PrivateMessageEvent, Sender

    if message is None:
        message = Message(text)

    return PrivateMessageEvent(
        time=1,
        self_id=self_id,
        post_type='message',
        message_type='private',
        sub_type='friend',
        message_id=message_id,
        user_id=user_id,
        message=message,
        original_message=message.copy(),
        raw_message=text if raw_message is None else raw_message,
        font=0,
        sender=Sender(user_id=user_id, nickname=nickname),
        reply=reply,
    )


def make_obv11_group_message_event(
        *,
        group_id: int = 10000,
        user_id: int = 10001,
        text: str = '/test',
        self_id: int = 10086,
        message_id: int = 1,
        nickname: str | None = 'tester',
        card: str | None = None,
        role: str | None = None,
        reply: Any = None,
) -> 'BaseEvent':
    """构造 OneBot V11 群消息事件"""
    from nonebot.adapters.onebot.v11 import Message
    from nonebot.adapters.onebot.v11.event import GroupMessageEvent, Sender

    return GroupMessageEvent(
        time=1,
        self_id=self_id,
        post_type='message',
        sub_type='normal',
        message_id=message_id,
        user_id=user_id,
        message_type='group',
        group_id=group_id,
        message=Message(text),
        original_message=Message(text),
        raw_message=text,
        font=0,
        sender=Sender(user_id=user_id, nickname=nickname, card=card, role=role),
        reply=reply,
    )


def make_obv11_meta_event(*, self_id: int = 10086, meta_event_type: str = 'lifecycle') -> 'BaseEvent':
    """构造 OneBot V11 元事件"""
    from nonebot.adapters.onebot.v11.event import MetaEvent

    return MetaEvent(time=1, self_id=self_id, post_type='meta_event', meta_event_type=meta_event_type)


def make_obv11_friend_recall_notice_event(
        *,
        user_id: int = 30001,
        self_id: int = 10086,
        message_id: int = 1,
) -> 'BaseEvent':
    """构造 OneBot V11 好友消息撤回通知事件"""
    from nonebot.adapters.onebot.v11.event import FriendRecallNoticeEvent

    return FriendRecallNoticeEvent(
        time=1,
        self_id=self_id,
        post_type='notice',
        notice_type='friend_recall',
        user_id=user_id,
        message_id=message_id,
    )


def make_obv11_honor_notify_event(*, group_id: int = 10000, user_id: int = 10001, self_id: int = 10086) -> 'BaseEvent':
    """构造 OneBot V11 群荣誉变更通知事件"""
    from nonebot.adapters.onebot.v11.event import HonorNotifyEvent

    return HonorNotifyEvent(
        time=1,
        self_id=self_id,
        post_type='notice',
        notice_type='notify',
        sub_type='honor',
        honor_type='talkative',
        group_id=group_id,
        user_id=user_id,
    )


def make_obv11_poke_notify_event(
        *,
        group_id: int | None = 10000,
        user_id: int = 10001,
        self_id: int = 10086,
) -> 'BaseEvent':
    """构造 OneBot V11 戳一戳通知事件 (group_id 为 None 表示私聊戳一戳)"""
    from nonebot.adapters.onebot.v11.event import PokeNotifyEvent

    return PokeNotifyEvent(
        time=1,
        self_id=self_id,
        post_type='notice',
        notice_type='notify',
        sub_type='poke',
        group_id=group_id,
        user_id=user_id,
        target_id=user_id,
    )


@lru_cache(maxsize=1)
def _fake_message_event_cls() -> type['OmegaBaseEvent']:
    """定义轻量自定义消息事件类 (进程内只定义一次, 类体定义遵守 src.* 延迟导入约定)"""
    from src.service.omega_base.internal import OmegaBaseEvent

    class _FakeMessageEvent(OmegaBaseEvent):
        event_type: str = 'fake_message'
        message: Message
        original_message: Message | None = None
        user_id: str = '10001'

        def get_message(self) -> Message:
            return self.message

        def get_user_id(self) -> str:
            return self.user_id

        def get_session_id(self) -> str:
            return f'fake_session_{self.user_id}'

        def is_tome(self) -> bool:
            return True

    return _FakeMessageEvent


def make_fake_message_event(
        *,
        user_id: str = '10001',
        message: Any = None,
        original_message: Any = None,
) -> 'BaseEvent':
    """构造带文本消息的轻量自定义事件 (用于超级用户等不依赖具体适配器的场景)"""
    from nonebot.adapters.onebot.v11 import Message as OneBotV11Message

    return _fake_message_event_cls()(
        message=message if message is not None else OneBotV11Message('/test'),
        original_message=original_message,
        user_id=user_id,
    )


def make_telegram_user_payload(*, user_id: int = 10001, username: str | None = None) -> dict[str, Any]:
    """构造 Telegram 用户负载 (消息事件 payload 的 from 字段)"""
    return {'id': user_id, 'is_bot': False, 'first_name': 'Tester', 'username': username}


def make_telegram_message_event(
        event_kind: str = 'group',
        *,
        chat_id: int = -1001234567,
        user_id: int = 10001,
        username: str | None = None,
        chat_username: str | None = None,
        reply_to: dict[str, Any] | None = None,
        message: list[dict[str, Any]] | None = None,
        with_photo: bool = False,
        original_message: list[dict[str, Any]] | None = None,
) -> 'BaseEvent':
    """构造 Telegram 平台消息事件 (经 model_validate 以正确处理 from 字段别名)

    chat 负载按事件类型构造: 私聊含 first_name, 群/频道含 title;
    with_photo=True 时默认消息为单个 photo 段, 否则为文本 'hi';
    original_message 仅在适配器 parse_event 中填充, 直接 model_validate 需显式提供 (None 则不携带)
    """
    from nonebot.adapters.telegram.event import (
        ChannelPostEvent,
        GroupMessageEvent,
        PrivateMessageEvent,
    )

    chat: dict[str, Any] = {
        'id': chat_id,
        'type': {'group': 'group', 'private': 'private', 'channel': 'channel'}[event_kind],
    }
    if event_kind == 'private':
        chat['first_name'] = 'Tester'
    else:
        chat['title'] = 'Test Chat'
    if chat_username is not None:
        chat['username'] = chat_username

    if message is None:
        message = (
            [{'type': 'photo', 'data': {'file': 'file_id_1'}}]
            if with_photo else [{'type': 'text', 'data': {'text': 'hi'}}]
        )

    payload: dict[str, Any] = {
        'message_id': 1,
        'date': 1,
        'chat': chat,
        'message': message,
    }
    if event_kind != 'channel':
        payload['from'] = make_telegram_user_payload(user_id=user_id, username=username)
    if original_message is not None:
        payload['original_message'] = original_message
    if reply_to is not None:
        payload['reply_to_message'] = reply_to

    event_cls = {'group': GroupMessageEvent, 'private': PrivateMessageEvent, 'channel': ChannelPostEvent}[event_kind]
    return event_cls.model_validate(payload)


def make_telegram_bot_config(token: str = '123456:TEST_TOKEN') -> Any:
    """构造测试用 Telegram BotConfig (Telegram Bot 构造强制要求 config 参数)"""
    from nonebot.adapters.telegram.config import BotConfig as TelegramBotConfig

    return TelegramBotConfig(token=token)


def make_non_plugin_matcher() -> 'Matcher':
    """构造不归属任何插件的 matcher 实例 (plugin_id=None), 各 processor 对非插件 matcher 应直接跳过"""
    from nonebot.matcher import Matcher

    return type('NonPluginMatcher', (Matcher,), {'plugin_id': None, 'temp': False})()


# ------------------------------------------------------------------ #
# Bot 实例构造 (真实适配器 Bot, 通过 isinstance 校验)
# ------------------------------------------------------------------ #

def create_real_obv11_bot(ctx: Any, self_id: str) -> 'Bot':
    """在 nonebug 上下文中创建真实 OneBot V11 Bot (auto_connect=False 隔离连接钩子副作用)

    NoneBot 依赖注入及 omega_base 中间件对 bot 做 isinstance 校验, MagicMock 不通过;
    使用驱动中已注册的真实适配器 (nonebug 已在上下文入口 patch 其 _call_api),
    保证 adapter.get_name() 返回 'OneBot V11' (nonebug create_adapter 的 FakeAdapter 会改写为 'fake')
    """
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    adapter = nonebot.get_adapter(Adapter)
    return ctx.create_bot(self_id=self_id, base=Bot, adapter=adapter, auto_connect=False)


def make_real_obv11_bot(self_id: str = '10086') -> 'Bot':
    """构造真实 OneBot V11 Bot 实例 (非 nonebug 场景直接构造, 不建立连接, 仅满足依赖注入的实例校验)"""
    from nonebot.adapters.onebot.v11 import Adapter, Bot

    return Bot(nonebot.get_adapter(Adapter), self_id)


def create_console_bot(self_id: str) -> 'Bot':
    """构造 Console Bot 实例 (不注册进 driver)

    Console Bot 构造签名为 __init__(adapter, info: Robot), 与 nonebug 的 create_bot(self_id=...) 不兼容
    """
    from nonebot.adapters.console import Adapter
    from nonebot.adapters.console import Bot as ConsoleBot
    from nonechat.model import Robot

    adapter = nonebot.get_adapter(Adapter)
    return ConsoleBot(adapter=adapter, info=Robot(id=self_id))


@asynccontextmanager
async def registered_online_bot(
        ctx: Any,
        *,
        self_id: str,
        base: type['Bot'] | None = None,
        adapter: 'Adapter | None' = None,
        **create_bot_kwargs: Any,
) -> AsyncGenerator['Bot', None]:
    """创建 Bot (auto_connect=False 隔离连接钩子副作用) 并登记进 driver.bots, 退出上下文时移除登记

    omega_base 的 get_bot 等在线判定经 driver.bots 解析, 手动登记的 Bot 必须在测试后移除;
    平台 Bot 的额外构造参数 (如 Telegram 的 config) 经 create_bot_kwargs 透传
    """
    bot = ctx.create_bot(self_id=self_id, base=base, adapter=adapter, auto_connect=False, **create_bot_kwargs)

    driver_bots = nonebot.get_driver().bots
    driver_bots[self_id] = bot
    try:
        yield bot
    finally:
        driver_bots.pop(self_id, None)


# ------------------------------------------------------------------ #
# 数据库行播种 / 全局注册表沙箱
# ------------------------------------------------------------------ #

async def seed_entity_permissions(
        bot: 'BotSelf',
        entity_type: str,
        entity_id: str,
        *,
        enable_global: bool = False,
        permission_level: int | None = None,
        auth_nodes: Iterable[tuple[str, str, str, int]] | None = None,
) -> None:
    """以独立会话为指定实体初始化并授予权限状态 (会话退出即提交)

    :param bot: BotSelf 数据记录 (读取 bot_type/self_id)
    :param enable_global: 开启实体全局功能开关
    :param permission_level: 设置权限等级
    :param auth_nodes: 授权节点 (module, plugin, node, available) 序列
    """
    from src.database.helpers import database_session
    from src.service.omega_base import OmegaEntity

    async with database_session() as session:
        entity = OmegaEntity(
            session=session,
            bot_type=bot.bot_type,
            bot_id=bot.self_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if enable_global:
            await entity.enable_global_permission()
        if permission_level is not None:
            await entity.set_permission_level(level=permission_level)
        for module, plugin, node, available in auth_nodes or []:
            await entity.set_auth_setting(module=module, plugin=plugin, node=node, available=available, value={})


@asynccontextmanager
async def preserve_plugin_row(
        plugin_name: str,
        module_name: str,
        *,
        ensure_enabled: bool = False,
) -> AsyncGenerator[None, None]:
    """快照指定插件行状态, 进入时可确保启用, 退出时恢复原状态 (原不存在则删除)"""
    from sqlalchemy.exc import NoResultFound

    from src.database import PluginDAL
    from src.database.helpers import database_session

    async with database_session() as session:
        dal = PluginDAL(session=session)
        try:
            row = await dal.query_unique(plugin_name=plugin_name, module_name=module_name)
            original_enabled: int | None = int(row.enabled)
            original_info = row.info
        except NoResultFound:
            original_enabled, original_info = None, None
        if ensure_enabled and original_enabled != 1:
            await dal.add_update_exist(
                plugin_name=plugin_name, module_name=module_name, enabled=1, info=original_info,
            )

    yield

    async with database_session() as session:
        dal = PluginDAL(session=session)
        if original_enabled is None:
            await dal.delete(plugin_name=plugin_name, module_name=module_name)
        else:
            await dal.add_update_exist(
                plugin_name=plugin_name, module_name=module_name,
                enabled=original_enabled, info=original_info,
            )


@asynccontextmanager
async def persisted_numeric_obv11_bot() -> AsyncGenerator['BotSelf', None]:
    """创建随机数字 self_id 的 OneBot V11 Bot 并落库, 退出上下文时清理

    omega_base 中间件的 self_id 校验要求 event.self_id == bot.self_id,
    实体初始化 (init_self) 要求 bot 行存在, 故 bot 身份须全程一致;
    清理时先按 bot_index_id 删除全部 entity (ORM 级联清理 auth_setting/friendship 等子表), 再删 bot 行
    """
    from src.database.internal.bot import BotSelfDAL, BotStatus, BotType

    async with BotSelfDAL.create() as dal:
        bot = await dal.add_update_exist(BotType.ONEBOT_V11, random_numeric_bot_self_id(), BotStatus.ENABLED)

    try:
        yield bot
    finally:
        from sqlalchemy import select

        from src.database.helpers import database_session
        from src.database.schema import EntityOrm

        async with database_session() as session:
            result = await session.execute(select(EntityOrm).where(EntityOrm.bot_index_id == bot.id))
            for entity_orm in result.scalars():
                await session.delete(entity_orm)
        async with BotSelfDAL.create() as dal:
            await dal.delete(bot.bot_type, bot.self_id)


@contextmanager
def first_respond_registry_sandbox() -> Generator[dict, None, None]:
    """omega_base 多 Bot 响应去重注册表沙箱: 快照并清空 __FIRST_RESPOND_REGISTRY, 退出时恢复

    __first_responded_bot_limit 预处理器将首次响应某会话的 Bot 登记为会话归属 (TTL 300s),
    共享会话/超管 ID 的用例不清空注册表会导致后续 Bot 的事件被忽略
    """
    import src.service.omega_base.internal.bots as bots_module

    registry: dict = getattr(bots_module, '__FIRST_RESPOND_REGISTRY')
    snapshot = dict(registry)
    registry.clear()
    try:
        yield registry
    finally:
        registry.clear()
        registry.update(snapshot)
