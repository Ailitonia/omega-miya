"""
@Author         : Ailitonia
@Date           : 2026/9/9 13:50
@FileName       : conftest
@Project        : omega-miya
@Description    : omega core 单元测试 fixtures
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator, Callable
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from async_asgi_testclient import TestClient
from nonebug import App

from tests.test_002_core.helpers import delete_global_cache_rows
from tests.utils import unique_test_id

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
        return unique_test_id(prefix)

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
# omega_base / 事件族 fixture
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
def fake_uni_message_send(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """以 UniMessage 替身子类重绑定 omega_base 适配器模块内的 UniMessage 名字, 并返回其 send AsyncMock

    UniMessage 为第三方类 (nonebot_plugin_alconna.uniseg), 直接 patch 其 send 类属性会进程级生效;
    此处仅替换 src.service.omega_base.internal.adapter 模块命名空间内的 UniMessage 名字,
    send 调用经由替身子类路由到返回的 AsyncMock (默认返回 MagicMock, 可覆盖 return_value)
    """
    from nonebot_plugin_alconna.uniseg import UniMessage

    import src.service.omega_base.internal.adapter as adapter_module

    send_mock = AsyncMock(return_value=MagicMock())

    class _FakeUniMessage(UniMessage):
        send = send_mock

    monkeypatch.setattr(adapter_module, 'UniMessage', _FakeUniMessage)
    return send_mock
