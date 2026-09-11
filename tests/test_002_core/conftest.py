"""
@Author         : Ailitonia
@Date           : 2026/9/9 13:50
@FileName       : conftest
@Project        : omega-miya
@Description    : omega core 单元测试 fixtures
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from async_asgi_testclient import TestClient
from nonebug import App

from tests.test_002_core.helpers import delete_global_cache_rows

if TYPE_CHECKING:
    from src.database.internal.bot import BotSelf
    from src.database.internal.entity import Entity
    from src.database.internal.subscription_source import SubscriptionSource
    from src.service.omega_base import OmegaEntity


class _TestDataFactory:
    """测试数据及数据库会话工厂

    敏感操作警告: 本类方法会直接修改 .env.test 配置的测试数据库, 禁止将测试环境指向生产数据库
    """

    def __init__(self) -> None:
        self._bots: dict[tuple[str, str], BotSelf] = {}
        self._entities: dict[tuple[str, str], Entity] = {}
        self._subscription_sources: dict[tuple[str, str], SubscriptionSource] = {}

    @property
    def has_test_bot(self) -> bool:
        return bool(self._bots)

    @property
    def has_test_entity(self) -> bool:
        return bool(self._entities)

    @staticmethod
    def unique_id(prefix: str) -> str:
        """生成带唯一后缀的测试 ID"""
        return f'{prefix}_{uuid4().hex[:8]}'

    async def clear_all(self) -> None:
        from src.database.internal.bot import BotSelfDAL
        from src.database.internal.entity import EntityDAL
        from src.database.internal.subscription_source import SubscriptionSourceDAL

        # entity 表保留全表清空: entity_factory 测试内自动创建/显式提交的行未被 factory 跟踪, 无法精确删除, 作为兜底
        async with EntityDAL.create() as dal:
            await dal._clear_all()
        # bot/subscription_source 仅删除 factory 创建的行, 避免误删其他途径播种的行 (如运行时连接钩子写入的行)
        async with BotSelfDAL.create() as dal:
            for bot_type, self_id in self._bots:
                await dal.delete(bot_type, self_id)
        async with SubscriptionSourceDAL.create() as dal:
            for sub_type, sub_id in self._subscription_sources:
                await dal.delete(sub_type, sub_id)

        self._bots.clear()
        self._entities.clear()
        self._subscription_sources.clear()

    async def create_test_bot(self, bot_type: str, *, bot_self_id: str | None = None) -> 'BotSelf':
        from src.database.internal.bot import BotSelfDAL, BotStatus

        self_id = bot_self_id or self.unique_id('TEST_BOT')
        async with BotSelfDAL.create() as dal:
            bot = await dal.add_update_exist(bot_type, self_id, BotStatus.ENABLED)

        self._bots[(bot_type, self_id)] = bot
        return bot

    async def delete_test_bot(self, bot: 'BotSelf') -> None:
        from src.database.internal.bot import BotSelfDAL

        # 子表会被级联删除
        async with BotSelfDAL.create() as dal:
            await dal.delete(bot.bot_type, bot.self_id)

        self._bots.pop((bot.bot_type, bot.self_id), None)

    def get_test_bot(self, bot_type: str | None = None, bot_self_id: str | None = None) -> 'BotSelf':
        """获取一个已生成的随机或指定 Bot"""
        candidates = [
            x
            for x in self._bots.values()
            if (bot_type is None or x.bot_type == bot_type) and (bot_self_id is None or x.self_id == bot_self_id)
        ]
        if not candidates:
            raise ValueError(f'There are no test bots to get, bot_type={bot_type!r}, bot_self_id={bot_self_id!r}')
        return candidates[0]

    async def create_test_entity(self, bot_type: str, entity_type: str, *, entity_id: str | None = None) -> 'Entity':
        from src.database.internal.entity import EntityDAL

        bot = self.get_test_bot(bot_type=bot_type)
        entity_id = entity_id or self.unique_id('TEST_ENTITY')
        async with EntityDAL.create() as dal:
            entity = await dal.add_update_exist(
                bot_type=bot.bot_type,
                bot_self_id=bot.self_id,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=self.unique_id('TEST_ENTITY_NAME'),
                entity_extra={},
            )

        self._entities[(entity_type, entity_id)] = entity
        return entity

    async def delete_test_entity(self, entity: 'Entity') -> None:
        from src.database.internal.entity import EntityDAL

        # 子表会被级联删除
        async with EntityDAL.create() as dal:
            await dal.delete_from_index(entity.id)

        self._entities.pop((entity.entity_type, entity.entity_id), None)

    def get_test_entity(self, entity_type: str | None = None, entity_id: str | None = None) -> 'Entity':
        """获取一个已生成的随机或指定 Entity"""
        candidates = [
            x
            for x in self._entities.values()
            if (entity_type is None or x.entity_type == entity_type) and (entity_id is None or x.entity_id == entity_id)
        ]
        if not candidates:
            raise ValueError(f'There are no test entities to get, entity_type={entity_type!r}, entity_id={entity_id!r}')
        return candidates[0]

    async def create_test_subscription_source(self, sub_type: str) -> 'SubscriptionSource':
        from src.database.internal.subscription_source import SubscriptionSourceDAL

        sub_id = self.unique_id('TEST_SUBSCRIPTION_SOURCES')
        sub_user_name = self.unique_id('TEST_SUBSCRIPTION_SOURCES_USER')
        async with SubscriptionSourceDAL.create() as dal:
            subscription_source = await dal.add_update_exist(sub_type, sub_id, sub_user_name, 'test_sub')

        self._subscription_sources[(sub_type, sub_id)] = subscription_source
        return subscription_source

    async def delete_test_subscription_source(self, subscription_sources: 'SubscriptionSource') -> None:
        from src.database.internal.subscription_source import SubscriptionSourceDAL

        # 子表会被级联删除
        async with SubscriptionSourceDAL.create() as dal:
            await dal.delete(subscription_sources.sub_type, subscription_sources.sub_id)

        self._subscription_sources.pop((subscription_sources.sub_type, subscription_sources.sub_id), None)

    def get_test_subscription_source(
            self,
            sub_type: str | None = None,
            sub_id: str | None = None,
    ) -> 'SubscriptionSource':
        """获取一个已生成的随机或指定订阅源"""
        candidates = [
            x
            for x in self._subscription_sources.values()
            if (sub_type is None or x.sub_type == sub_type) and (sub_id is None or x.sub_id == sub_id)
        ]
        if not candidates:
            raise ValueError(f'There are no test subscription sources to get, sub_type={sub_type!r}, sub_id={sub_id!r}')
        return candidates[0]


@pytest.fixture
def test_nonexist_id() -> str:
    """随机生成一个不存在的 ID"""
    return f'TEST_NONEXIST_{uuid4().hex}'


@pytest.fixture(scope='class')
async def test_db_data_factory() -> AsyncGenerator[_TestDataFactory, None]:
    """测试数据对象及数据库会话工厂, 测试结束后自动清理

    收尾清理为破坏性操作: entity 表全表清空, 并删除 factory 创建的 bot/订阅源行
    """
    factory = _TestDataFactory()
    try:
        yield factory
    finally:
        await factory.clear_all()


@pytest.fixture(scope='class')
async def test_onebot_v11_bot(test_db_data_factory) -> AsyncGenerator['BotSelf', None]:
    """测试用 OneBot V11 Bot, 测试类结束后清理"""
    from src.database.internal.bot import BotType

    bot = await test_db_data_factory.create_test_bot(bot_type=BotType.ONEBOT_V11)

    try:
        yield bot
    finally:
        await test_db_data_factory.delete_test_bot(bot=bot)


@pytest.fixture(scope='class')
async def test_console_bot(test_db_data_factory) -> AsyncGenerator['BotSelf', None]:
    """测试用 Console Bot, 测试类结束后清理"""
    from src.database.internal.bot import BotType

    bot = await test_db_data_factory.create_test_bot(bot_type=BotType.CONSOLE)

    try:
        yield bot
    finally:
        await test_db_data_factory.delete_test_bot(bot=bot)


@pytest.fixture(scope='class')
async def test_telegram_bot(test_db_data_factory) -> AsyncGenerator['BotSelf', None]:
    """测试用 Telegram Bot, 测试类结束后清理"""
    from src.database.internal.bot import BotType

    bot = await test_db_data_factory.create_test_bot(bot_type=BotType.TELEGRAM)

    try:
        yield bot
    finally:
        await test_db_data_factory.delete_test_bot(bot=bot)


@pytest.fixture
async def test_onebot_v11_entity_factory(test_onebot_v11_bot) -> AsyncGenerator[Callable[..., 'OmegaEntity'], None]:
    """OmegaEntity 实例工厂, 绑定独立数据库会话, Bot/Entity 默认 OneBot V11 平台随机生成

    会话生命周期与单个测试一致: 测试内的写操作默认在测试结束(夹具收尾)时统一提交,
    需要跨会话验证的用例应当显式 await entity.commit_session()
    """
    from src.database.helpers import database_session
    from src.database.internal.entity import EntityType
    from src.service.omega_base.internal.entity import OmegaEntity

    async with database_session() as session:
        def _factory(**overrides: Any) -> 'OmegaEntity':
            params: dict[str, Any] = {
                'session': session,
                'bot_type': test_onebot_v11_bot.bot_type,
                'bot_id': test_onebot_v11_bot.self_id,
                'entity_type': EntityType.ONEBOT_V11_USER,
                'entity_id': _TestDataFactory.unique_id('TEST_ENTITY'),
                'entity_name': _TestDataFactory.unique_id('TEST_ENTITY_NAME'),
                'entity_extra': {},
            }
            params.update(overrides)
            return OmegaEntity(**params)

        yield _factory


@pytest.fixture(scope='class')
async def test_onebot_v11_user(test_db_data_factory, test_onebot_v11_bot) -> AsyncGenerator['Entity', None]:
    """测试用 OneBot V11 用户 Entity, 测试类结束后清理"""
    from src.database.internal.bot import BotType
    from src.database.internal.entity import EntityType

    entity = await test_db_data_factory.create_test_entity(
        bot_type=BotType.ONEBOT_V11,
        entity_type=EntityType.ONEBOT_V11_USER,
    )

    try:
        yield entity
    finally:
        await test_db_data_factory.delete_test_entity(entity=entity)


@pytest.fixture(scope='class')
async def test_onebot_v11_group(test_db_data_factory, test_onebot_v11_bot) -> AsyncGenerator['Entity', None]:
    """测试用 OneBot V11 群组 Entity, 测试类结束后清理"""
    from src.database.internal.bot import BotType
    from src.database.internal.entity import EntityType

    entity = await test_db_data_factory.create_test_entity(
        bot_type=BotType.ONEBOT_V11,
        entity_type=EntityType.ONEBOT_V11_GROUP,
    )

    try:
        yield entity
    finally:
        await test_db_data_factory.delete_test_entity(entity=entity)


@pytest.fixture(scope='class')
async def test_subscription_source(test_db_data_factory) -> AsyncGenerator['SubscriptionSource', None]:
    """测试用订阅源, 测试类结束后清理"""

    sub_type = test_db_data_factory.unique_id('TEST_SUBTYPE')
    source = await test_db_data_factory.create_test_subscription_source(sub_type=sub_type)

    try:
        yield source
    finally:
        await test_db_data_factory.delete_test_subscription_source(subscription_sources=source)


@pytest.fixture(scope='class')
async def test_subscription_sources(
        test_db_data_factory,
) -> AsyncGenerator[tuple['SubscriptionSource', 'SubscriptionSource'], None]:
    """两个不同 sub_type 的订阅源, 测试类结束后清理"""

    sub_type_a = test_db_data_factory.unique_id('TEST_SUBTYPE_A')
    sub_type_b = test_db_data_factory.unique_id('TEST_SUBTYPE_B')
    source_a = await test_db_data_factory.create_test_subscription_source(sub_type=sub_type_a)
    source_b = await test_db_data_factory.create_test_subscription_source(sub_type=sub_type_b)

    try:
        yield source_a, source_b
    finally:
        await test_db_data_factory.delete_test_subscription_source(subscription_sources=source_a)
        await test_db_data_factory.delete_test_subscription_source(subscription_sources=source_b)


@pytest.fixture
async def mounted_app_client(app: App) -> AsyncGenerator[TestClient, None]:
    """经主应用挂载访问子应用的 HTTP 客户端(复用 nonebug 全局 lifespan 客户端)"""
    async with app.test_server() as ctx:
        yield ctx.get_client()


@pytest.fixture
async def global_cache_row_tracker_factory() -> AsyncGenerator[Callable[[str], list[str]], None]:
    """全局缓存行跟踪器工厂

    make_tracker(cache_name) 返回一个跟踪列表, 测试将产生的 cache_key 追加进去,
    测试结束后按 cache_name 定点清理被跟踪的数据库行(适用于测试 import 期注册单例的模块, 不注销注册表)
    """
    trackers: list[tuple[str, list[str]]] = []

    def _make_tracker(cache_name: str) -> list[str]:
        tracker: list[str] = []
        trackers.append((cache_name, tracker))
        return tracker

    yield _make_tracker

    for cache_name, tracker in trackers:
        await delete_global_cache_rows(cache_name, tracker)


# ------------------------------------------------------------------ #
# omega_base / 事件族 fixture (自 test_010 / test_012 上移, 保持测试方法体零改动)
# ------------------------------------------------------------------ #

@pytest.fixture
def entity_target_register_sandbox(monkeypatch: pytest.MonkeyPatch):
    """EntityTarget 注册表测试沙箱

    以空表替换内部注册表 (monkeypatch 在测试后恢复原表), 测试内的注册操作不影响全局
    """
    from src.service.omega_base.internal import ENTITY_TARGET_REGISTER

    monkeypatch.setattr(ENTITY_TARGET_REGISTER, '_map', {})
    return ENTITY_TARGET_REGISTER


@pytest.fixture
def event_depend_register_sandbox(monkeypatch: pytest.MonkeyPatch):
    """EventDepend 注册表测试沙箱

    以空表替换内部注册表 (monkeypatch 在测试后恢复原表), 测试内的注册操作不影响全局
    """
    from src.service.omega_base.internal import EVENT_DEPEND_REGISTER

    monkeypatch.setattr(EVENT_DEPEND_REGISTER, '_map', {})
    return EVENT_DEPEND_REGISTER


@pytest.fixture
def online_bots_sandbox(monkeypatch: pytest.MonkeyPatch):
    """bots 模块全局状态测试沙箱

    快照并清空全局 __ONLINE_BOTS 与 __FIRST_RESPOND_REGISTRY (测试后恢复), 同时将模块内引用的
    handle_event 替换为 AsyncMock, 避免连接/断开钩子触发真实事件管线及数据库副作用
    """
    import src.service.omega_base.internal.bots as bots_module

    online_bots_snapshot: dict[tuple[str, str], Any] = dict(getattr(bots_module, '__ONLINE_BOTS'))
    getattr(bots_module, '__ONLINE_BOTS').clear()
    registry_snapshot: dict[str, tuple[str, float]] = dict(getattr(bots_module, '__FIRST_RESPOND_REGISTRY'))
    getattr(bots_module, '__FIRST_RESPOND_REGISTRY').clear()
    handle_event_mock = AsyncMock()
    monkeypatch.setattr(bots_module, 'handle_event', handle_event_mock)

    yield bots_module, handle_event_mock

    getattr(bots_module, '__ONLINE_BOTS').clear()
    getattr(bots_module, '__ONLINE_BOTS').update(online_bots_snapshot)
    getattr(bots_module, '__FIRST_RESPOND_REGISTRY').clear()
    getattr(bots_module, '__FIRST_RESPOND_REGISTRY').update(registry_snapshot)


@pytest.fixture(scope='class')
async def test_onebot_v11_numeric_bot(test_db_data_factory) -> AsyncGenerator['BotSelf', None]:
    """管线测试用 Bot: 数字 self_id (OneBot V11 事件模型要求 int) 且已落库

    omega_base 中间件的 self_id 校验预处理器要求 event.self_id == bot.self_id,
    且好感度/历史后处理器会经实体初始化要求 bot 行存在, 故 bot 身份须全程一致
    """
    from src.database.internal.bot import BotType

    self_id = str(random.randint(10_000_000, 99_999_999))
    bot = await test_db_data_factory.create_test_bot(bot_type=BotType.ONEBOT_V11, bot_self_id=self_id)

    try:
        yield bot
    finally:
        await test_db_data_factory.delete_test_bot(bot=bot)
