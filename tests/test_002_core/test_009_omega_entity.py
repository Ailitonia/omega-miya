"""
@Author         : Ailitonia
@Date           : 2026/9/6 23:42
@FileName       : test_009_omega_entity
@Project        : omega-miya
@Description    : OmegaEntity 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator, Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from src.database.internal.bot import BotSelf
    from src.database.internal.subscription_source import SubscriptionSource
    from src.service.omega_base.internal.entity import OmegaEntity

_TEST_BOT_TYPE = 'OneBot V11'
"""测试用 Bot 类型"""

_TEST_ENTITY_TYPE = 'onebot_v11_user'
"""测试用 Entity 类型"""

_ASSERT_TIME_TOLERANCE = 2.0
"""时间断言容差(秒), 数据库 DateTime 可能截断到秒"""


def _unique_id(prefix: str) -> str:
    """生成带唯一后缀的测试 ID"""
    return f'{prefix}_{uuid4().hex[:8]}'


def _days_ago(n: int) -> date:
    """相对于今日的日期 (n 天前, 负数为未来日期)"""
    return datetime.now().date() - timedelta(days=n)


def _assert_close_to(target: datetime, expected: datetime) -> None:
    """断言目标时间与期望时间的偏差在容差内"""
    assert abs((target - expected).total_seconds()) <= _ASSERT_TIME_TOLERANCE


async def _query_entity_or_none(bot_self_id: str, entity_type: str, entity_id: str) -> Any | None:
    """以独立会话查询 Entity, 不存在返回 None"""
    from src.database.internal.entity import EntityDAL

    async with EntityDAL.create() as dal:
        try:
            return await dal.query_unique(
                bot_type=_TEST_BOT_TYPE,
                bot_self_id=bot_self_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        except NoResultFound:
            return None


@pytest.fixture(scope='class')
async def test_bot() -> AsyncGenerator['BotSelf', None]:
    """播种测试用 Bot, 测试类结束后清理实体相关表及 Bot 行"""
    from src.database.internal.bot import BotSelfDAL
    from src.database.internal.entity import EntityDAL

    self_id = _unique_id('TEST_OE_BOT')
    async with BotSelfDAL.create() as dal:
        bot = await dal.add_update_exist(_TEST_BOT_TYPE, self_id, 1)

    try:
        yield bot
    finally:
        # 先清理实体及其子表 (外键引用 bot), 再删除 bot 行
        async with EntityDAL.create() as dal:
            await dal._clear_all()
        async with BotSelfDAL.create() as dal:
            await dal.delete(_TEST_BOT_TYPE, self_id)


@pytest.fixture
async def entity_factory(test_bot: 'BotSelf') -> AsyncGenerator[Callable[..., 'OmegaEntity'], None]:
    """OmegaEntity 实例工厂, 绑定独立数据库会话, entity_id/entity_name 默认随机隔离

    会话生命周期与单个测试一致: 测试内的写操作默认在测试结束(夹具收尾)时统一提交,
    需要跨会话验证的用例应显式 await entity.commit_session()
    """
    from src.database.helpers import database_session
    from src.service.omega_base.internal.entity import OmegaEntity

    async with database_session() as session:
        def _factory(**overrides: Any) -> 'OmegaEntity':
            params: dict[str, Any] = {
                'session': session,
                'bot_type': test_bot.bot_type,
                'bot_id': test_bot.self_id,
                'entity_type': _TEST_ENTITY_TYPE,
                'entity_id': _unique_id('TEST_OE_ENT'),
                'entity_name': _unique_id('TEST_OE_NAME'),
            }
            params.update(overrides)
            return OmegaEntity(**params)

        yield _factory


@pytest.fixture(scope='class')
async def subscription_sources() -> AsyncGenerator[tuple['SubscriptionSource', 'SubscriptionSource'], None]:
    """播种两个不同 sub_type 的订阅源, 测试类结束后清理"""
    from src.database.internal.entity import EntityDAL
    from src.database.internal.subscription_source import SubscriptionSourceDAL

    async with SubscriptionSourceDAL.create() as dal:
        source_a = await dal.add_update_exist(
            _unique_id('TEST_OE_SUBTYPE_A'), _unique_id('TEST_OE_SUBID'), 'TEST_SOURCE_A'
        )
        source_b = await dal.add_update_exist(
            _unique_id('TEST_OE_SUBTYPE_B'), _unique_id('TEST_OE_SUBID'), 'TEST_SOURCE_B'
        )

    try:
        yield source_a, source_b
    finally:
        # 先清理订阅关联 (外键引用订阅源), 再清理订阅源
        async with EntityDAL.create() as dal:
            await dal._clear_all()
        async with SubscriptionSourceDAL.create() as dal:
            await dal._clear_all()


class TestModuleContract:
    """模块导出契约测试"""

    def test_module_all(self) -> None:
        import src.service.omega_base.internal.entity as entity_module

        assert entity_module.__all__ == ['EntityAcquireType', 'EntityInitParams', 'OmegaEntity']


class TestEntityInitParams:
    """EntityInitParams 构造参数模型测试"""

    def test_construct_and_kwargs(self) -> None:
        from src.database.internal.bot import BotType
        from src.database.internal.entity import EntityType
        from src.service.omega_base.internal.entity import EntityInitParams

        params = EntityInitParams(
            bot_type='OneBot V11',
            bot_id='10001',
            entity_type='onebot_v11_user',
            entity_id='20002',
            entity_name='test_name',
            entity_extra={'key': 'value'},
            entity_info='test_info',
        )

        assert params.bot_type is BotType.ONEBOT_V11
        assert params.entity_type is EntityType.ONEBOT_V11_USER
        assert params.kwargs == {
            'bot_type': BotType.ONEBOT_V11,
            'bot_id': '10001',
            'entity_type': EntityType.ONEBOT_V11_USER,
            'entity_id': '20002',
            'entity_name': 'test_name',
            'entity_extra': {'key': 'value'},
            'entity_info': 'test_info',
        }

    def test_optional_fields_default_none(self) -> None:
        from src.service.omega_base.internal.entity import EntityInitParams

        params = EntityInitParams(
            bot_type='Console',
            bot_id='1',
            entity_type='console_user',
            entity_id='2',
            entity_extra={},
        )

        assert params.entity_name is None
        assert params.entity_info is None

    def test_frozen_model(self) -> None:
        from src.service.omega_base.internal.entity import EntityInitParams

        params = EntityInitParams(
            bot_type='Console',
            bot_id='1',
            entity_type='console_user',
            entity_id='2',
            entity_extra={},
        )

        with pytest.raises(ValidationError):
            params.entity_id = 'changed'

    def test_extra_fields_ignored(self) -> None:
        from src.service.omega_base.internal.entity import EntityInitParams

        params = EntityInitParams(
            bot_type='Console',
            bot_id='1',
            entity_type='console_user',
            entity_id='2',
            entity_extra={},
            unknown_junk_field='junk',
        )

        assert 'unknown_junk_field' not in params.kwargs

    def test_coerce_numbers_to_str(self) -> None:
        from src.service.omega_base.internal.entity import EntityInitParams

        params = EntityInitParams(
            bot_type='Console',
            bot_id=123456,
            entity_type='console_user',
            entity_id=7890,
            entity_extra={},
        )

        assert params.bot_id == '123456'
        assert params.entity_id == '7890'

    def test_missing_required_field_raises(self) -> None:
        from src.service.omega_base.internal.entity import EntityInitParams

        with pytest.raises(ValidationError):
            EntityInitParams(
                bot_type='Console',
                bot_id='1',
                entity_type='console_user',
                entity_id='2',
            )

    def test_invalid_enum_value_raises(self) -> None:
        from src.service.omega_base.internal.entity import EntityInitParams

        with pytest.raises(ValidationError):
            EntityInitParams(
                bot_type='NotExistBotType',
                bot_id='1',
                entity_type='console_user',
                entity_id='2',
                entity_extra={},
            )


class TestOmegaEntityInit:
    """OmegaEntity 构造与基础属性测试 (不访问数据库)"""

    @staticmethod
    def _make_entity(**overrides: Any) -> 'OmegaEntity':
        from src.service.omega_base.internal.entity import OmegaEntity

        params: dict[str, Any] = {
            'session': MagicMock(),
            'bot_type': 'OneBot V11',
            'bot_id': '10001',
            'entity_type': 'onebot_v11_user',
            'entity_id': '20002',
        }
        params.update(overrides)
        return OmegaEntity(**params)

    def test_enum_coercion(self) -> None:
        from src.database.internal.bot import BotType
        from src.database.internal.entity import EntityType

        entity = self._make_entity()

        assert entity.bot_type is BotType.ONEBOT_V11
        assert entity.entity_type is EntityType.ONEBOT_V11_USER
        assert entity.bot_id == '10001'
        assert entity.entity_id == '20002'

    def test_invalid_bot_type_raises(self) -> None:
        with pytest.raises(ValueError, match='not a valid'):
            self._make_entity(bot_type='NotExistBotType')

    def test_invalid_entity_type_raises(self) -> None:
        with pytest.raises(ValueError, match='not a valid'):
            self._make_entity(entity_type='not_exist_entity_type')

    def test_default_entity_name(self) -> None:
        entity = self._make_entity()

        assert entity.entity_name == 'onebot_v11_user_20002'

    def test_explicit_entity_name(self) -> None:
        entity = self._make_entity(entity_name='custom_name')

        assert entity.entity_name == 'custom_name'

    def test_entity_extra_default_empty_dict(self) -> None:
        entity = self._make_entity()

        assert entity.entity_extra == {}

    def test_entity_extra_explicit(self) -> None:
        entity = self._make_entity(entity_extra={'key': 'value'})

        assert entity.entity_extra == {'key': 'value'}

    def test_entity_info_default_none(self) -> None:
        entity = self._make_entity()

        assert entity.entity_info is None

    def test_tid_property(self) -> None:
        entity = self._make_entity()

        assert entity.tid == 'onebot_v11_user_20002'

    def test_repr(self) -> None:
        entity = self._make_entity()

        assert repr(entity) == 'OmegaEntity(type=onebot_v11_user, entity_id=20002, bot_id=10001)'

    def test_not_init_initially_true(self) -> None:
        entity = self._make_entity()

        assert entity.not_init is True

    def test_init_params_round_trip(self) -> None:
        from src.service.omega_base.internal.entity import EntityInitParams, OmegaEntity

        entity = self._make_entity(entity_extra={'k': 'v'}, entity_info='info')
        params = entity.init_params

        assert isinstance(params, EntityInitParams)
        assert params.bot_id == '10001'
        assert params.entity_id == '20002'
        assert params.entity_name == 'onebot_v11_user_20002'
        assert params.entity_extra == {'k': 'v'}
        assert params.entity_info == 'info'

        # kwargs 可直接用于重构 OmegaEntity
        rebuilt = OmegaEntity(session=MagicMock(), **params.kwargs)
        assert rebuilt.bot_id == entity.bot_id
        assert rebuilt.entity_id == entity.entity_id
        assert rebuilt.entity_name == entity.entity_name
        assert rebuilt.entity_extra == entity.entity_extra
        assert rebuilt.entity_info == entity.entity_info


class TestParseContinuousSignInDay:
    """连续签到日数解析测试 (纯计算, 日期均相对今日动态构造)"""

    async def test_empty_list(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        assert await OmegaEntity._parse_continuous_sign_in_day([]) == (0, _days_ago(0).toordinal())

    async def test_only_today(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        assert await OmegaEntity._parse_continuous_sign_in_day([_days_ago(0)]) == (1, _days_ago(1).toordinal())

    async def test_continuous_days(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        result = await OmegaEntity._parse_continuous_sign_in_day([_days_ago(0), _days_ago(1), _days_ago(2)])

        assert result == (3, _days_ago(3).toordinal())

    async def test_unsorted_input(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        result = await OmegaEntity._parse_continuous_sign_in_day([_days_ago(2), _days_ago(0), _days_ago(1)])

        assert result == (3, _days_ago(3).toordinal())

    async def test_duplicate_dates_deduplicated(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        result = await OmegaEntity._parse_continuous_sign_in_day([_days_ago(0), _days_ago(0), _days_ago(1)])

        assert result == (2, _days_ago(2).toordinal())

    async def test_gap_breaks_streak(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        result = await OmegaEntity._parse_continuous_sign_in_day([_days_ago(0), _days_ago(1), _days_ago(3)])

        assert result == (2, _days_ago(2).toordinal())

    async def test_today_missing_returns_zero(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        result = await OmegaEntity._parse_continuous_sign_in_day([_days_ago(1), _days_ago(2), _days_ago(3)])

        assert result == (0, _days_ago(0).toordinal())

    async def test_single_old_date_returns_zero(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        assert await OmegaEntity._parse_continuous_sign_in_day([_days_ago(5)]) == (0, _days_ago(0).toordinal())

    async def test_far_gap(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        result = await OmegaEntity._parse_continuous_sign_in_day([_days_ago(0), _days_ago(10)])

        assert result == (1, _days_ago(1).toordinal())

    async def test_future_date_only(self) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        assert await OmegaEntity._parse_continuous_sign_in_day([_days_ago(-1)]) == (0, _days_ago(0).toordinal())

    async def test_future_dates_ignored(self) -> None:
        """未来日期不参与连签计算, 今日已签时应正确统计当前连续日数"""
        from src.service.omega_base.internal.entity import OmegaEntity

        result = await OmegaEntity._parse_continuous_sign_in_day([_days_ago(-3), _days_ago(0), _days_ago(1)])

        assert result == (2, _days_ago(2).toordinal())


class TestInitSelfAndQuery:
    """初始化与自身数据查询测试 (真实数据库)"""

    async def test_first_access_auto_creates(self, entity_factory) -> None:
        entity = entity_factory(entity_extra={'platform': 'test', 'level': 1}, entity_info='intro')
        assert entity.not_init is True

        created = await entity.query_entity_self()

        assert entity.not_init is False
        assert created.entity_type.value == _TEST_ENTITY_TYPE
        assert created.entity_id == entity.entity_id
        assert created.entity_name == entity.entity_name
        assert created.entity_extra == {'platform': 'test', 'level': 1}
        assert created.entity_info == 'intro'
        assert (await entity.query_bot_self()).self_id == entity.bot_id

    async def test_init_self_existing_entity_not_overwritten(self, entity_factory) -> None:
        entity_id = _unique_id('TEST_OE_ENT')
        first = entity_factory(entity_id=entity_id, entity_extra={'a': 1}, entity_info='first')
        await first.init_self()

        # 同 id 不同参数再次初始化: add_ignore_exist 语义, 已有数据不被覆盖
        second = entity_factory(entity_id=entity_id, entity_extra={'b': 2}, entity_info='second')
        await second.init_self()

        row = await second.query_entity_self()
        assert row.entity_extra == {'a': 1}
        assert row.entity_name == first.entity_name
        assert row.entity_info == 'first'

    async def test_init_self_missing_bot_raises(self, entity_factory) -> None:
        entity = entity_factory(bot_id=_unique_id('NONEXIST_BOT'))

        with pytest.raises(NoResultFound):
            await entity.init_self()

    async def test_query_bot_self_auto_init(self, entity_factory, test_bot) -> None:
        entity = entity_factory()

        bot = await entity.query_bot_self()

        assert bot.self_id == test_bot.self_id
        assert entity.not_init is False

    async def test_init_from_entity_index_id_round_trip(self, entity_factory) -> None:
        from src.database.helpers import database_session
        from src.service.omega_base.internal.entity import OmegaEntity

        entity = entity_factory(entity_extra={'origin': 'seed'}, entity_info='indexed')
        created = await entity.query_entity_self()
        await entity.commit_session()

        async with database_session() as session:
            loaded = await OmegaEntity.init_from_entity_index_id(session, created.id)

            assert loaded.not_init is False
            assert loaded.entity_id == entity.entity_id
            assert loaded.entity_name == entity.entity_name
            assert loaded.entity_extra == {'origin': 'seed'}
            assert loaded.entity_info == 'indexed'
            assert (await loaded.query_entity_self()).id == created.id
            assert (await loaded.query_bot_self()).self_id == entity.bot_id

    async def test_init_from_entity_index_id_not_found(self, entity_factory) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        entity = entity_factory()

        with pytest.raises(NoResultFound):
            await OmegaEntity.init_from_entity_index_id(entity._db_session, -1)

    async def test_upsert_self_creates_when_missing(self, entity_factory) -> None:
        entity = entity_factory()

        await entity.upsert_self(entity_name='CREATED_BY_UPSERT', entity_info='info-v1')

        row = await entity.query_entity_self()
        assert row.entity_name == 'CREATED_BY_UPSERT'
        assert row.entity_info == 'info-v1'

    async def test_upsert_self_updates_and_preserves(self, entity_factory) -> None:
        entity = entity_factory(entity_extra={'keep': 1})
        await entity.query_entity_self()

        await entity.upsert_self(entity_name='RENAMED', entity_info='info-v1')
        row = await entity.query_entity_self()
        assert row.entity_name == 'RENAMED'
        assert row.entity_info == 'info-v1'
        assert row.entity_extra == {'keep': 1}

        # entity_info 传 None 时保留原值
        await entity.upsert_self(entity_name='RENAMED_AGAIN', entity_info=None)
        row = await entity.query_entity_self()
        assert row.entity_name == 'RENAMED_AGAIN'
        assert row.entity_info == 'info-v1'

    async def test_delete_invalidates_cache_and_reinit_recreates(self, entity_factory, test_bot) -> None:
        entity = entity_factory()
        created = await entity.query_entity_self()

        await entity.delete()
        assert entity.not_init is True

        await entity.commit_session()
        assert await _query_entity_or_none(test_bot.self_id, _TEST_ENTITY_TYPE, entity.entity_id) is None

        # 缓存失效后再次访问将按需重建 Entity
        recreated = await entity.query_entity_self()
        assert entity.not_init is False
        assert recreated.entity_id == created.entity_id
        assert recreated.id != created.id

        await entity.commit_session()
        assert await _query_entity_or_none(test_bot.self_id, _TEST_ENTITY_TYPE, entity.entity_id) is not None

    async def test_commit_and_rollback(self, entity_factory, test_bot) -> None:
        entity = entity_factory()
        await entity.query_entity_self()

        await entity.rollback_session()
        assert await _query_entity_or_none(test_bot.self_id, _TEST_ENTITY_TYPE, entity.entity_id) is None

        committed = entity_factory()
        await committed.query_entity_self()
        await committed.commit_session()
        assert await _query_entity_or_none(test_bot.self_id, _TEST_ENTITY_TYPE, committed.entity_id) is not None


class TestFriendship:
    """好感度相关方法测试 (真实数据库)"""

    async def test_query_friendship_auto_init(self, entity_factory) -> None:
        entity = entity_factory()

        friendship = await entity.query_friendship()

        assert friendship.status == 'normal'
        assert friendship.mood == Decimal('0')
        assert friendship.friendship == Decimal('0')
        assert friendship.energy == Decimal('0')
        assert friendship.currency == Decimal('0')
        assert friendship.rsp_threshold == Decimal('0')

    async def test_set_friendship_full_fields(self, entity_factory) -> None:
        entity = entity_factory()

        friendship = await entity.set_friendship(
            status='happy',
            mood=Decimal('5.55'),
            friendship=Decimal('10.5'),
            energy=Decimal('3.25'),
            currency=Decimal('100.01'),
            rsp_threshold=Decimal('1.5'),
        )

        assert friendship.status == 'happy'
        assert friendship.mood == Decimal('5.55')
        assert friendship.friendship == Decimal('10.5')
        assert friendship.energy == Decimal('3.25')
        assert friendship.currency == Decimal('100.01')
        assert friendship.rsp_threshold == Decimal('1.5')

    async def test_set_friendship_partial_preserves_others(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_friendship(friendship=Decimal('10'), energy=Decimal('3'))

        friendship = await entity.set_friendship(mood=Decimal('5.55'))

        assert friendship.mood == Decimal('5.55')
        assert friendship.friendship == Decimal('10')
        assert friendship.energy == Decimal('3')
        assert friendship.status == 'normal'

    async def test_alter_friendship_increment_and_decrement(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_friendship(friendship=Decimal('10'), energy=Decimal('3'))

        friendship = await entity.alter_friendship(friendship=Decimal('2.5'), energy=Decimal('-1'))

        assert friendship.friendship == Decimal('12.5')
        assert friendship.energy == Decimal('2')

    async def test_alter_friendship_creates_when_missing(self, entity_factory) -> None:
        entity = entity_factory()

        friendship = await entity.alter_friendship(friendship=Decimal('7'), currency=Decimal('0.01'))

        assert friendship.friendship == Decimal('7')
        assert friendship.currency == Decimal('0.01')
        assert friendship.status == 'normal'

    async def test_alter_friendship_decimal_precision(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_friendship(currency=Decimal('0'))

        for _ in range(3):
            friendship = await entity.alter_friendship(currency=Decimal('0.01'))

        assert friendship.currency == Decimal('0.03')

    async def test_friendship_rollback_not_persisted(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.query_entity_self()
        await entity.commit_session()

        await entity.set_friendship(friendship=Decimal('5'))
        await entity.rollback_session()

        # 回滚后好感度行未落库, 重新查询得到的是全新初始化的零值行
        friendship = await entity.query_friendship()
        assert friendship.friendship == Decimal('0')


class TestSignIn:
    """签到相关方法测试 (真实数据库)"""

    async def test_sign_in_default_today(self, entity_factory) -> None:
        entity = entity_factory()

        sign_in = await entity.sign_in()

        assert sign_in.sign_in_date == datetime.now().date()
        assert sign_in.sign_in_info == 'Normal Sign In'

    async def test_check_today_sign_in(self, entity_factory) -> None:
        entity = entity_factory()

        assert await entity.check_today_sign_in() is False

        await entity.sign_in()

        assert await entity.check_today_sign_in() is True

    async def test_sign_in_with_date(self, entity_factory) -> None:
        entity = entity_factory()

        sign_in = await entity.sign_in(date_=date(2020, 1, 2))

        assert sign_in.sign_in_date == date(2020, 1, 2)
        assert sign_in.sign_in_info == 'Fixed Sign In'

    async def test_sign_in_with_datetime_normalized(self, entity_factory) -> None:
        entity = entity_factory()

        sign_in = await entity.sign_in(date_=datetime(2020, 1, 2, 15, 30, 45))

        assert sign_in.sign_in_date == date(2020, 1, 2)
        assert sign_in.sign_in_info == 'Fixed Sign In'

    async def test_duplicate_sign_in_marked(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.sign_in()

        duplicated = await entity.sign_in()

        assert duplicated.sign_in_info == 'Duplicate Sign In'

    async def test_duplicate_sign_in_with_info_overwrites(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.sign_in(sign_in_info='first')

        overwritten = await entity.sign_in(sign_in_info='second')

        assert overwritten.sign_in_info == 'second'

    async def test_query_sign_in_days(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.sign_in(date_=date(2020, 1, 1))
        await entity.sign_in(date_=date(2020, 1, 2))
        await entity.sign_in(date_=date(2020, 1, 4))

        days = await entity.query_sign_in_days()

        assert set(days) == {date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 4)}

    async def test_sign_in_with_alter_friendship(self, entity_factory) -> None:
        entity = entity_factory()

        sign_in_result, friendship_result = await entity.check_and_execute_sign_in_with_alter_friendship(
            alter_friendship=Decimal('5'),
            alter_energy=Decimal('1'),
            alter_currency=Decimal('2'),
        )

        assert sign_in_result.sign_in_date == datetime.now().date()
        assert friendship_result.friendship == Decimal('5')
        assert friendship_result.energy == Decimal('1')
        assert friendship_result.currency == Decimal('2')

    async def test_sign_in_with_alter_friendship_repeated_same_day(self, entity_factory) -> None:
        """同日重复调用: 签到标记为重复, 好感度仍按量变更 (固化现状语义)"""
        entity = entity_factory()
        await entity.check_and_execute_sign_in_with_alter_friendship(alter_friendship=Decimal('5'))

        sign_in_result, friendship_result = await entity.check_and_execute_sign_in_with_alter_friendship(
            alter_friendship=Decimal('5')
        )

        assert sign_in_result.sign_in_info == 'Duplicate Sign In'
        assert friendship_result.friendship == Decimal('10')


class TestAuthSetting:
    """通用授权配置相关方法测试 (真实数据库)"""

    async def test_set_and_query_round_trip(self, entity_factory) -> None:
        entity = entity_factory()

        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=1, value={'key': 'value'})
        auth_setting = await entity.query_auth_setting('MOD', 'PLG', 'ND')

        assert auth_setting.module == 'MOD'
        assert auth_setting.plugin == 'PLG'
        assert auth_setting.node == 'ND'
        assert auth_setting.available == 1
        assert auth_setting.value == {'key': 'value'}

    async def test_query_missing_raises(self, entity_factory) -> None:
        entity = entity_factory()

        with pytest.raises(NoResultFound):
            await entity.query_auth_setting('NO_MOD', 'NO_PLG', 'NO_ND')

    async def test_query_all_and_plugin_filter(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_auth_setting('MOD_A', 'PLG_A', 'ND_1', available=1, value={})
        await entity.set_auth_setting('MOD_A', 'PLG_B', 'ND_2', available=1, value={})
        await entity.set_auth_setting('MOD_B', 'PLG_A', 'ND_3', available=1, value={})

        all_settings = await entity.query_all_auth_setting()
        assert len(all_settings) == 3

        mod_a_settings = await entity.query_plugin_all_auth_setting('MOD_A', 'PLG_A')
        assert len(mod_a_settings) == 1
        assert mod_a_settings[0].node == 'ND_1'

    async def test_verify_missing_returns_zero(self, entity_factory) -> None:
        entity = entity_factory()

        assert await entity.verify_auth_setting('NO_MOD', 'NO_PLG', 'NO_ND') == 0

    async def test_verify_strict_match(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=1, value={})

        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=1, strict_match_available=True) == 1
        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=2, strict_match_available=True) == -1

    async def test_verify_non_strict_match(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=5, value={})

        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=3, strict_match_available=False) == 1
        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=5, strict_match_available=False) == 1
        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=6, strict_match_available=False) == -1

    async def test_set_overwrites_existing(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=1, value={'v': 1})

        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=0, value={'v': 2})
        auth_setting = await entity.query_auth_setting('MOD', 'PLG', 'ND')

        assert auth_setting.available == 0
        assert auth_setting.value == {'v': 2}

    async def test_delete_auth_setting(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=1, value={})

        await entity.delete_auth_setting('MOD', 'PLG', 'ND')

        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND') == 0

    async def test_delete_missing_auth_setting_no_error(self, entity_factory) -> None:
        entity = entity_factory()

        await entity.delete_auth_setting('NO_MOD', 'NO_PLG', 'NO_ND')


class TestInternalPermissions:
    """内置权限分支 (全局开关/权限等级/跳过冷却) 测试 (真实数据库)"""

    async def test_global_permission_default_disabled(self, entity_factory) -> None:
        entity = entity_factory()

        assert await entity.check_global_permission() is False

    async def test_global_permission_enable_disable(self, entity_factory) -> None:
        entity = entity_factory()

        enabled = await entity.enable_global_permission()
        assert enabled.available == 1
        assert await entity.check_global_permission() is True
        assert (await entity.query_global_permission()).available == 1

        disabled = await entity.disable_global_permission()
        assert disabled.available == 0
        assert await entity.check_global_permission() is False

    async def test_permission_level_missing(self, entity_factory) -> None:
        entity = entity_factory()

        assert await entity.check_permission_level(1) is False

    async def test_permission_level_threshold(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_permission_level(10)

        assert await entity.check_permission_level(5) is True
        assert await entity.check_permission_level(10) is True
        assert await entity.check_permission_level(11) is False
        assert (await entity.query_permission_level()).available == 10

    async def test_permission_level_zero(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_permission_level(0)

        assert await entity.check_permission_level(0) is True
        assert await entity.check_permission_level(1) is False

    async def test_permission_level_negative(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_permission_level(-1)

        assert await entity.check_permission_level(-2) is True
        assert await entity.check_permission_level(0) is False

    async def test_skip_cooldown_permission(self, entity_factory) -> None:
        entity = entity_factory()

        assert await entity.check_permission_skip_cooldown('MOD_A', 'PLG_A') is False

        await entity.enable_plugin_skip_cooldown_permission('MOD_A', 'PLG_A')
        assert await entity.check_permission_skip_cooldown('MOD_A', 'PLG_A') is True

        await entity.disable_plugin_skip_cooldown_permission('MOD_A', 'PLG_A')
        assert await entity.check_permission_skip_cooldown('MOD_A', 'PLG_A') is False

    async def test_skip_cooldown_permission_scoped_by_plugin(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.enable_plugin_skip_cooldown_permission('MOD_A', 'PLG_A')

        assert await entity.check_permission_skip_cooldown('MOD_A', 'PLG_B') is False
        assert await entity.check_permission_skip_cooldown('MOD_B', 'PLG_A') is False


class TestCooldown:
    """冷却事件相关方法测试 (真实数据库)"""

    async def test_set_cooldown_with_timedelta(self, entity_factory) -> None:
        entity = entity_factory()

        cooldown = await entity.set_cooldown('TEST_EVENT', timedelta(seconds=60))

        assert cooldown.event == 'TEST_EVENT'
        _assert_close_to(cooldown.stop_at, datetime.now() + timedelta(seconds=60))

        expired, stop_at = await entity.check_cooldown_expired('TEST_EVENT')
        assert expired is False
        assert stop_at == cooldown.stop_at

    async def test_set_cooldown_with_past_datetime(self, entity_factory) -> None:
        entity = entity_factory()
        past = datetime.now() - timedelta(hours=1)

        await entity.set_cooldown('TEST_EVENT', past)

        expired, stop_at = await entity.check_cooldown_expired('TEST_EVENT')
        assert expired is True
        _assert_close_to(stop_at, past)

    async def test_check_missing_cooldown_expired(self, entity_factory) -> None:
        entity = entity_factory()

        expired, stop_at = await entity.check_cooldown_expired('NO_SUCH_EVENT')

        assert expired is True
        _assert_close_to(stop_at, datetime.now())

    async def test_set_cooldown_invalid_type_raises(self, entity_factory) -> None:
        entity = entity_factory()

        with pytest.raises(TypeError):
            await entity.set_cooldown('TEST_EVENT', 'not-a-time')

    async def test_set_cooldown_overwrites_existing(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_cooldown('TEST_EVENT', timedelta(seconds=60), description='first')

        cooldown = await entity.set_cooldown('TEST_EVENT', timedelta(seconds=3600), description='second')

        _assert_close_to(cooldown.stop_at, datetime.now() + timedelta(seconds=3600))
        assert cooldown.description == 'second'

    async def test_query_cooldown_missing_raises(self, entity_factory) -> None:
        entity = entity_factory()

        with pytest.raises(NoResultFound):
            await entity.query_cooldown('NO_SUCH_EVENT')

    async def test_global_cooldown(self, entity_factory) -> None:
        from src.service.omega_base.internal.consts import GLOBAL_COOLDOWN_EVENT

        entity = entity_factory()

        cooldown = await entity.set_global_cooldown(timedelta(seconds=30))

        assert cooldown.event == GLOBAL_COOLDOWN_EVENT
        assert cooldown.description == 'OmegaGlobalCooldown 全局冷却'

        expired, _ = await entity.check_global_cooldown_expired()
        assert expired is False

    async def test_global_cooldown_missing_expired(self, entity_factory) -> None:
        entity = entity_factory()

        expired, stop_at = await entity.check_global_cooldown_expired()

        assert expired is True
        _assert_close_to(stop_at, datetime.now())

    async def test_character_attribute_setter_cooldown(self, entity_factory) -> None:
        entity = entity_factory()

        cooldown = await entity.set_character_attribute_setter_cooldown('level', timedelta(seconds=30))

        assert cooldown.event == 'OmegaICAttrSetter_level'
        assert cooldown.description == "角色'level'属性更新冷却"

        expired, _ = await entity.check_character_attribute_setter_cooldown_expired('level')
        assert expired is False

        missing_expired, _ = await entity.check_character_attribute_setter_cooldown_expired('other')
        assert missing_expired is True

    async def test_character_profile_setter_cooldown(self, entity_factory) -> None:
        entity = entity_factory()

        cooldown = await entity.set_character_profile_setter_cooldown('appearance', timedelta(seconds=30))

        assert cooldown.event == 'OmegaICProfileSetter_appearance'
        assert cooldown.description == "角色'appearance'档案更新冷却"

        expired, _ = await entity.check_character_profile_setter_cooldown_expired('appearance')
        assert expired is False

        missing_expired, _ = await entity.check_character_profile_setter_cooldown_expired('other')
        assert missing_expired is True


class TestCharacterAttributeAndProfile:
    """内置角色属性/档案相关方法测试 (真实数据库)"""

    async def test_attribute_set_and_query_round_trip(self, entity_factory) -> None:
        entity = entity_factory()

        await entity.set_character_attribute('level', 5)

        assert await entity.query_character_attribute('level') == 5

    async def test_attribute_missing_without_factory_raises(self, entity_factory) -> None:
        entity = entity_factory()

        with pytest.raises(NoResultFound):
            await entity.query_character_attribute('no_such_attr')

    async def test_attribute_missing_with_factory_generates_and_persists(self, entity_factory) -> None:
        entity = entity_factory()
        calls = 0

        def _factory() -> int:
            nonlocal calls
            calls += 1
            return 42

        first = await entity.query_character_attribute('luck', default_factory=_factory)
        second = await entity.query_character_attribute('luck', default_factory=_factory)

        assert first == 42
        assert second == 42
        assert calls == 1

    async def test_attribute_unavailable_regenerated_by_factory(self, entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute

        entity = entity_factory()
        await entity.set_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck', available=0, value={'luck': 99}
        )

        value = await entity.query_character_attribute('luck', default_factory=lambda: 7)

        assert value == 7
        auth_setting = await entity.query_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck'
        )
        assert auth_setting.available == 1
        assert auth_setting.value == {'luck': 7}

    async def test_attribute_missing_key_regenerated_by_factory(self, entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute

        entity = entity_factory()
        await entity.set_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck', available=1, value={'other_key': 1}
        )

        value = await entity.query_character_attribute('luck', default_factory=lambda: 8)

        assert value == 8

    async def test_attribute_non_int_value(self, entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute

        entity = entity_factory()
        await entity.set_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck', available=1, value={'luck': 'abc'}
        )

        with pytest.raises(ValueError, match='invalid literal'):
            await entity.query_character_attribute('luck')

        value = await entity.query_character_attribute('luck', default_factory=lambda: 9)
        assert value == 9

    async def test_profile_set_and_query_round_trip(self, entity_factory) -> None:
        entity = entity_factory()

        await entity.set_character_profile('appearance', {'hair': 'black'})

        assert await entity.query_character_profile('appearance') == {'hair': 'black'}

    async def test_profile_missing_without_factory_raises(self, entity_factory) -> None:
        entity = entity_factory()

        with pytest.raises(NoResultFound):
            await entity.query_character_profile('no_such_profile')

    async def test_profile_missing_with_factory_generates_and_persists(self, entity_factory) -> None:
        entity = entity_factory()
        calls = 0

        def _factory() -> dict[str, Any]:
            nonlocal calls
            calls += 1
            return {'generated': True}

        first = await entity.query_character_profile('appearance', default_factory=_factory)
        second = await entity.query_character_profile('appearance', default_factory=_factory)

        assert first == {'generated': True}
        assert second == {'generated': True}
        assert calls == 1

    async def test_profile_unavailable_regenerated_by_factory(self, entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterProfile

        entity = entity_factory()
        await entity.set_auth_setting(
            CharacterProfile.module, CharacterProfile.plugin, 'appearance', available=0, value={'appearance': {}}
        )

        value = await entity.query_character_profile('appearance', default_factory=lambda: {'new': 1})

        assert value == {'new': 1}

    async def test_profile_missing_key_regenerated_by_factory(self, entity_factory) -> None:
        """存储的 value 字典缺少目标键时, 提供 default_factory 应重新生成并持久化"""
        from src.service.omega_base.internal.consts import CharacterProfile

        entity = entity_factory()
        await entity.set_auth_setting(
            CharacterProfile.module, CharacterProfile.plugin, 'appearance', available=1, value={'other_key': {}}
        )

        value = await entity.query_character_profile('appearance', default_factory=lambda: {'gen': True})

        assert value == {'gen': True}
        auth_setting = await entity.query_auth_setting(
            CharacterProfile.module, CharacterProfile.plugin, 'appearance'
        )
        assert auth_setting.value == {'appearance': {'gen': True}}

    async def test_profile_missing_key_without_factory_raises(self, entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterProfile

        entity = entity_factory()
        await entity.set_auth_setting(
            CharacterProfile.module, CharacterProfile.plugin, 'appearance', available=1, value={'other_key': {}}
        )

        with pytest.raises(KeyError):
            await entity.query_character_profile('appearance')

    async def test_delete_character_attribute(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_character_attribute('level', 5)

        await entity.delete_character_attribute('level')

        with pytest.raises(NoResultFound):
            await entity.query_character_attribute('level')

    async def test_delete_character_profile(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_character_profile('appearance', {'hair': 'black'})

        await entity.delete_character_profile('appearance')

        with pytest.raises(NoResultFound):
            await entity.query_character_profile('appearance')

    async def test_query_all_character_attribute_and_profile(self, entity_factory) -> None:
        entity = entity_factory()
        await entity.set_character_attribute('level', 5)
        await entity.set_character_attribute('luck', 7)
        await entity.set_character_profile('appearance', {'hair': 'black'})

        attributes = await entity.query_all_character_attribute()
        assert len(attributes) == 2
        assert {x.node for x in attributes} == {'level', 'luck'}

        profiles = await entity.query_all_character_profile()
        assert len(profiles) == 1
        assert profiles[0].node == 'appearance'


class TestSubscription:
    """订阅相关方法测试 (真实数据库)"""

    async def test_add_and_query_subscription(self, entity_factory, subscription_sources) -> None:
        source_a, _ = subscription_sources
        entity = entity_factory()

        added = await entity.add_subscription(source_a, sub_info='sub-info')

        assert added.id == source_a.id
        assert added.sub_type == source_a.sub_type
        assert added.sub_id == source_a.sub_id

        subscribed = await entity.query_subscribed_source()
        assert len(subscribed) == 1
        assert subscribed[0].id == source_a.id

    async def test_query_subscribed_source_filter_by_sub_type(self, entity_factory, subscription_sources) -> None:
        source_a, source_b = subscription_sources
        entity = entity_factory()
        await entity.add_subscription(source_a)
        await entity.add_subscription(source_b)

        all_subscribed = await entity.query_subscribed_source()
        assert {x.id for x in all_subscribed} == {source_a.id, source_b.id}

        filtered_a = await entity.query_subscribed_source(sub_type=source_a.sub_type)
        assert len(filtered_a) == 1
        assert filtered_a[0].id == source_a.id

        filtered_b = await entity.query_subscribed_source(sub_type=source_b.sub_type)
        assert len(filtered_b) == 1
        assert filtered_b[0].id == source_b.id

    async def test_query_subscribed_source_entity_not_exists(self, entity_factory, test_bot) -> None:
        """Entity 不存在时返回空列表, 且不会自动创建 Entity"""
        entity = entity_factory()

        assert await entity.query_subscribed_source() == []
        assert await _query_entity_or_none(test_bot.self_id, _TEST_ENTITY_TYPE, entity.entity_id) is None

    async def test_add_subscription_duplicate_updates_sub_info(self, entity_factory, subscription_sources) -> None:
        from sqlalchemy import select

        from src.database.helpers import database_session
        from src.database.schema import SubscriptionOrm

        source_a, _ = subscription_sources
        entity = entity_factory()
        await entity.add_subscription(source_a, sub_info='sub-info-v1')
        await entity.add_subscription(source_a, sub_info='sub-info-v2')
        await entity.commit_session()

        entity_row = await entity.query_entity_self()
        async with database_session() as session:
            stmt = select(SubscriptionOrm).where(
                SubscriptionOrm.entity_index_id == entity_row.id,
                SubscriptionOrm.sub_source_index_id == source_a.id,
            )
            links = (await session.execute(stmt)).scalars().all()

        assert len(links) == 1
        assert links[0].sub_info == 'sub-info-v2'

    async def test_delete_subscription(self, entity_factory, subscription_sources) -> None:
        source_a, source_b = subscription_sources
        entity = entity_factory()
        await entity.add_subscription(source_a)
        await entity.add_subscription(source_b)

        await entity.delete_subscription(source_a)

        subscribed = await entity.query_subscribed_source()
        assert len(subscribed) == 1
        assert subscribed[0].id == source_b.id

    async def test_delete_missing_subscription_no_error(self, entity_factory, subscription_sources) -> None:
        source_a, _ = subscription_sources
        entity = entity_factory()

        await entity.delete_subscription(source_a)
