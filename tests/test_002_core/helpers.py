"""
@Author         : Ailitonia
@Date           : 2026/9/12 10:00
@FileName       : helpers
@Project        : omega-miya
@Description    : omega core 单元测试共用 helper 函数

    本模块仅放置纯函数 helper, fixture 统一定义在 conftest.py
    遵守项目约定: `src.*` 导入必须留在函数体内(测试模块在 nonebot 初始化前被收集导入)

@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
from uuid import NAMESPACE_URL, uuid4, uuid5

import nonebot
from sqlalchemy import delete
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from nonebot.adapters import Adapter, Bot
    from nonebot.adapters import Event as BaseEvent
    from nonebot.matcher import Matcher

    from src.database.internal.global_cache import GlobalCache
    from src.service.omega_base.internal.entity import EntityInitParams
    from src.service.omega_base.internal.event import OmegaBaseEvent

TEST_DATETIME_PAST = datetime(1990, 1, 1)
"""测试用已过期时间点"""

ASSERT_TIME_TOLERANCE = 2.0
"""时间断言容差(秒), 数据库 DateTime 可能截断到秒"""


def make_uuid5(name: str) -> str:
    """按 omega_global_cache 族模块实现计算指定名称对应的 uuid5 hex(32 位小写十六进制)"""
    return uuid5(namespace=NAMESPACE_URL, name=name).hex


def assert_datetime_close(actual: datetime, expected: datetime, *, tolerance: float = ASSERT_TIME_TOLERANCE) -> None:
    """断言两个时间的偏差在容差内"""
    assert abs((actual - expected).total_seconds()) <= tolerance


def assert_close_to_now(
        target: datetime,
        expected_delta: timedelta,
        *,
        tolerance: float = ASSERT_TIME_TOLERANCE,
) -> None:
    """断言目标时间与 当前时间+expected_delta 的偏差在容差内"""
    assert_datetime_close(target, datetime.now() + expected_delta, tolerance=tolerance)


async def seed_global_cache_row(
        cache_name: str,
        cache_key: str,
        cache_value: str,
        expired_time: datetime | timedelta | None = None,
) -> None:
    """以独立会话直接向数据库写入(或更新)缓存行并提交, 模拟外部写入(不经过被测模块的内存缓存)"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        await dal.add_update_exist(
            cache_name=cache_name,
            cache_key=cache_key,
            cache_value=cache_value,
            expired_time=expired_time,
        )
        await dal.commit_session()


async def query_global_cache_row_or_none(
        cache_name: str,
        cache_key: str,
        *,
        include_expired: bool = True,
) -> 'GlobalCache | None':
    """以独立会话查询缓存行, 不存在返回 None"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        try:
            return await dal.query_unique(cache_name, cache_key, include_expired=include_expired)
        except NoResultFound:
            return None


async def query_all_global_cache_rows(cache_name: str, *, include_expired: bool = True) -> list['GlobalCache']:
    """以独立会话查询指定 cache_name 的全部缓存行"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        return await dal.query_series(cache_name, include_expired=include_expired)


async def delete_global_cache_rows(cache_name: str, cache_keys: list[str] | None = None) -> None:
    """物理删除缓存行

    - cache_keys 为 None: 删除指定 cache_name 的全部行(含未过期), 供持有独立命名空间的调用方使用
    - cache_keys 为空列表: 不执行任何操作
    - cache_keys 非空: 仅定点删除指定键, 供测试 import 期注册单例的调用方使用(避免误删其他来源写入的行)
    """
    if cache_keys is not None and not cache_keys:
        return

    from src.database.helpers import database_session
    from src.database.schema import GlobalCacheOrm

    statement = delete(GlobalCacheOrm).where(GlobalCacheOrm.cache_name == cache_name)
    if cache_keys is not None:
        statement = statement.where(GlobalCacheOrm.cache_key.in_(cache_keys))

    async with database_session() as session:
        await session.execute(statement)


# ------------------------------------------------------------------ #
# omega_base / 事件构造族 helper
# ------------------------------------------------------------------ #

def unique_test_id(prefix: str) -> str:
    """生成带唯一后缀的测试 ID"""
    return f'{prefix}_{uuid4().hex[:8]}'


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
    """构造轻量 mock Bot (为三处本地实现配置属性的并集: self_id / adapter.get_name / type / config)

    注意: 仅在不需要经 NoneBot 依赖注入 (如 SUPERUSER) 的场景使用;
    涉及实体落库的调用必须将 self_id 设置为数据库中已存在的 Bot (如 test_onebot_v11_bot.self_id)
    """
    bot = MagicMock()
    bot.self_id = self_id
    bot.type = 'fake_adapter'
    bot.adapter.get_name.return_value = adapter_name
    # SUPERUSER 等依赖读取 bot.config, 提供真实 Driver 配置
    bot.config = nonebot.get_driver().config
    return bot


def make_obv11_private_message_event(
        *,
        user_id: int = 10001,
        text: str = '/test',
        self_id: int = 10086,
        message_id: int = 1,
) -> 'BaseEvent':
    """构造 OneBot V11 私聊消息事件"""
    from nonebot.adapters.onebot.v11 import Message
    from nonebot.adapters.onebot.v11.event import PrivateMessageEvent, Sender

    return PrivateMessageEvent(
        time=1,
        self_id=self_id,
        post_type='message',
        message_type='private',
        sub_type='friend',
        message_id=message_id,
        user_id=user_id,
        message=Message(text),
        original_message=Message(text),
        raw_message=text,
        font=0,
        sender=Sender(user_id=user_id, nickname='tester'),
    )


def make_obv11_group_message_event(
        *,
        group_id: int,
        user_id: int = 10001,
        text: str = '/test',
        self_id: int = 10086,
        message_id: int = 1,
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
        sender=Sender(user_id=user_id, nickname='tester'),
    )


@lru_cache(maxsize=1)
def _fake_message_event_cls() -> type['OmegaBaseEvent']:
    """定义轻量自定义消息事件类 (进程内只定义一次, 类体定义遵守 src.* 延迟导入约定)"""
    from nonebot.adapters.onebot.v11 import Message

    from src.service.omega_base.internal import OmegaBaseEvent

    class _FakeMessageEvent(OmegaBaseEvent):
        event_type: str = 'fake_message'
        message: Message
        user_id: str

        def get_message(self) -> Message:
            return self.message

        def get_user_id(self) -> str:
            return self.user_id

        def get_session_id(self) -> str:
            return f'fake_session_{self.user_id}'

        def is_tome(self) -> bool:
            return True

    return _FakeMessageEvent


def make_fake_message_event(*, user_id: str = '10001') -> 'BaseEvent':
    """构造带文本消息的轻量自定义事件 (用于超级用户等不依赖具体适配器的场景)"""
    from nonebot.adapters.onebot.v11 import Message

    return _fake_message_event_cls()(message=Message('/test'), user_id=user_id)


def make_non_plugin_matcher() -> 'Matcher':
    """构造不归属任何插件的 matcher 实例 (plugin_id=None), 各 processor 对非插件 matcher 应直接跳过"""
    from nonebot.matcher import Matcher

    return type('NonPluginMatcher', (Matcher,), {'plugin_id': None, 'temp': False})()


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
