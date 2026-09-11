"""
@Author         : Ailitonia
@Date           : 2026/9/6 23:42
@FileName       : test_009_omega_entity
@Project        : omega-miya
@Description    : OmegaEntity 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import NoResultFound

from tests.test_002_core.helpers import assert_datetime_close

if TYPE_CHECKING:
    from src.service.omega_base.internal.entity import OmegaEntity


def _days_ago(n: int) -> date:
    """相对于今日的日期 (n 天前, 负数为未来日期)"""
    return datetime.now().date() - timedelta(days=n)


async def _query_entity_or_none(
        bot_self_id: str,
        entity_type: str,
        entity_id: str,
        *,
        bot_type: str | None = None,
) -> Any | None:
    """以独立会话查询 Entity, 不存在返回 None"""
    from src.database.internal.bot import BotType
    from src.database.internal.entity import EntityDAL

    async with EntityDAL.create() as dal:
        try:
            return await dal.query_unique(
                bot_type=bot_type or BotType.ONEBOT_V11,
                bot_self_id=bot_self_id,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        except NoResultFound:
            return None


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

    @pytest.mark.parametrize(
        ('days_ago_offsets', 'expected_streak'),
        [
            ([], 0),
            ([0], 1),
            ([0, 1, 2], 3),
            ([2, 0, 1], 3),
            ([0, 0, 1], 2),
            ([0, 1, 3], 2),
            ([1, 2, 3], 0),
            ([5], 0),
            ([0, 10], 1),
            ([-1], 0),
            ([-3, 0, 1], 2),
        ],
        ids=[
            'empty_list',
            'only_today',
            'continuous_days',
            'unsorted_input',
            'duplicate_dates_deduplicated',
            'gap_breaks_streak',
            'today_missing_returns_zero',
            'single_old_date_returns_zero',
            'far_gap',
            'future_date_only',
            'future_dates_ignored',
        ],
    )
    async def test_parse_continuous_sign_in_day(
            self,
            days_ago_offsets: list[int],
            expected_streak: int,
    ) -> None:
        """输入以相对今日天数偏移构造的签到日期列表, 期望返回 (连续签到日数, 连续段起始日前一日的序数)

        覆盖: 空列表/仅今日/连续多日/乱序输入/重复日期去重/断签截断/缺今日/单个旧日期/远端断签/仅未来日期/未来日期忽略
        """
        from src.service.omega_base.internal.entity import OmegaEntity

        result = await OmegaEntity._parse_continuous_sign_in_day([_days_ago(n) for n in days_ago_offsets])

        assert result == (expected_streak, _days_ago(expected_streak).toordinal())


class TestInitSelfAndQuery:
    """初始化与自身数据查询测试 (真实数据库)"""

    async def test_first_access_auto_creates(self, test_onebot_v11_entity_factory) -> None:
        from src.database.internal.entity import EntityType

        entity = test_onebot_v11_entity_factory(entity_extra={'platform': 'test', 'level': 1}, entity_info='intro')
        assert entity.not_init is True

        created = await entity.query_entity_self()

        assert entity.not_init is False
        assert created.entity_type.value == EntityType.ONEBOT_V11_USER
        assert created.entity_id == entity.entity_id
        assert created.entity_name == entity.entity_name
        assert created.entity_extra == {'platform': 'test', 'level': 1}
        assert created.entity_info == 'intro'
        assert (await entity.query_bot_self()).self_id == entity.bot_id

    async def test_init_self_existing_entity_not_overwritten(
            self,
            test_nonexist_id,
            test_onebot_v11_entity_factory,
    ) -> None:
        first = test_onebot_v11_entity_factory(
            entity_id=test_nonexist_id,
            entity_extra={'a': 1},
            entity_info='first',
        )
        await first.init_self()

        # 同 id 不同参数再次初始化: add_ignore_exist 语义, 已有数据不被覆盖
        second = test_onebot_v11_entity_factory(
            entity_id=test_nonexist_id,
            entity_extra={'b': 2},
            entity_info='second',
        )
        await second.init_self()

        row = await second.query_entity_self()
        assert row.entity_extra == {'a': 1}
        assert row.entity_name == first.entity_name
        assert row.entity_info == 'first'

    async def test_init_self_missing_bot_raises(
            self,
            test_nonexist_id,
            test_onebot_v11_entity_factory,
    ) -> None:
        entity = test_onebot_v11_entity_factory(bot_id=test_nonexist_id)

        with pytest.raises(NoResultFound):
            await entity.init_self()

    async def test_query_bot_self_auto_init(self, test_onebot_v11_entity_factory, test_onebot_v11_bot) -> None:
        entity = test_onebot_v11_entity_factory()

        bot = await entity.query_bot_self()

        assert bot.self_id == test_onebot_v11_bot.self_id
        assert entity.not_init is False

    async def test_init_from_entity_index_id_round_trip(self, test_onebot_v11_entity_factory) -> None:
        from src.database.helpers import database_session
        from src.service.omega_base.internal.entity import OmegaEntity

        entity = test_onebot_v11_entity_factory(entity_extra={'origin': 'seed'}, entity_info='indexed')
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

    async def test_init_from_entity_index_id_not_found(self, test_onebot_v11_entity_factory) -> None:
        from src.service.omega_base.internal.entity import OmegaEntity

        entity = test_onebot_v11_entity_factory()

        with pytest.raises(NoResultFound):
            await OmegaEntity.init_from_entity_index_id(entity._db_session, -1)

    async def test_upsert_self_creates_when_missing(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        await entity.upsert_self(entity_name='CREATED_BY_UPSERT', entity_info='info-v1')

        row = await entity.query_entity_self()
        assert row.entity_name == 'CREATED_BY_UPSERT'
        assert row.entity_info == 'info-v1'

    async def test_upsert_self_updates_and_preserves(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory(entity_extra={'keep': 1})
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

    async def test_delete_invalidates_cache_and_reinit_recreates(
            self,
            test_onebot_v11_entity_factory,
            test_onebot_v11_bot,
    ) -> None:
        from src.database.internal.entity import EntityType

        entity = test_onebot_v11_entity_factory()
        created = await entity.query_entity_self()

        await entity.delete()
        assert entity.not_init is True

        await entity.commit_session()
        assert await _query_entity_or_none(
            test_onebot_v11_bot.self_id,
            EntityType.ONEBOT_V11_USER,
            entity.entity_id,
        ) is None

        # 缓存失效后再次访问将按需重建 Entity
        recreated = await entity.query_entity_self()
        assert entity.not_init is False
        assert recreated.entity_id == created.entity_id
        assert recreated.id != created.id

        await entity.commit_session()
        assert await _query_entity_or_none(
            test_onebot_v11_bot.self_id,
            EntityType.ONEBOT_V11_USER,
            entity.entity_id,
        ) is not None

    async def test_commit_and_rollback(self, test_onebot_v11_entity_factory, test_onebot_v11_bot) -> None:
        from src.database.internal.entity import EntityType

        entity = test_onebot_v11_entity_factory()
        await entity.query_entity_self()

        await entity.rollback_session()
        assert await _query_entity_or_none(
            test_onebot_v11_bot.self_id,
            EntityType.ONEBOT_V11_USER,
            entity.entity_id,
        ) is None

        committed = test_onebot_v11_entity_factory()
        await committed.query_entity_self()
        await committed.commit_session()
        assert await _query_entity_or_none(
            test_onebot_v11_bot.self_id,
            EntityType.ONEBOT_V11_USER,
            committed.entity_id,
        ) is not None


class TestFriendship:
    """好感度相关方法测试 (真实数据库)"""

    async def test_query_friendship_auto_init(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        friendship = await entity.query_friendship()

        assert friendship.status == 'normal'
        assert friendship.mood == Decimal('0')
        assert friendship.friendship == Decimal('0')
        assert friendship.energy == Decimal('0')
        assert friendship.currency == Decimal('0')
        assert friendship.rsp_threshold == Decimal('0')

    async def test_set_friendship_full_fields(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

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

    async def test_set_friendship_partial_preserves_others(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_friendship(friendship=Decimal('10'), energy=Decimal('3'))

        friendship = await entity.set_friendship(mood=Decimal('5.55'))

        assert friendship.mood == Decimal('5.55')
        assert friendship.friendship == Decimal('10')
        assert friendship.energy == Decimal('3')
        assert friendship.status == 'normal'

    async def test_alter_friendship_increment_and_decrement(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_friendship(friendship=Decimal('10'), energy=Decimal('3'))

        friendship = await entity.alter_friendship(friendship=Decimal('2.5'), energy=Decimal('-1'))

        assert friendship.friendship == Decimal('12.5')
        assert friendship.energy == Decimal('2')

    async def test_alter_friendship_creates_when_missing(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        friendship = await entity.alter_friendship(friendship=Decimal('7'), currency=Decimal('0.01'))

        assert friendship.friendship == Decimal('7')
        assert friendship.currency == Decimal('0.01')
        assert friendship.status == 'normal'

    async def test_alter_friendship_decimal_precision(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_friendship(currency=Decimal('0'))

        for _ in range(3):
            friendship = await entity.alter_friendship(currency=Decimal('0.01'))

        assert friendship.currency == Decimal('0.03')

    async def test_friendship_rollback_not_persisted(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.query_entity_self()
        await entity.commit_session()

        await entity.set_friendship(friendship=Decimal('5'))
        await entity.rollback_session()

        # 回滚后好感度行未落库, 重新查询得到的是全新初始化的零值行
        friendship = await entity.query_friendship()
        assert friendship.friendship == Decimal('0')


class TestSignIn:
    """签到相关方法测试 (真实数据库)"""

    async def test_sign_in_default_today(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        sign_in = await entity.sign_in()

        assert sign_in.sign_in_date == datetime.now().date()
        assert sign_in.sign_in_info == 'Normal Sign In'

    async def test_check_today_sign_in(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        assert await entity.check_today_sign_in() is False

        await entity.sign_in()

        assert await entity.check_today_sign_in() is True

    async def test_sign_in_with_date(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        sign_in = await entity.sign_in(date_=date(2020, 1, 2))

        assert sign_in.sign_in_date == date(2020, 1, 2)
        assert sign_in.sign_in_info == 'Fixed Sign In'

    async def test_sign_in_with_datetime_normalized(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        sign_in = await entity.sign_in(date_=datetime(2020, 1, 2, 15, 30, 45))

        assert sign_in.sign_in_date == date(2020, 1, 2)
        assert sign_in.sign_in_info == 'Fixed Sign In'

    async def test_duplicate_sign_in_marked(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.sign_in()

        duplicated = await entity.sign_in()

        assert duplicated.sign_in_info == 'Duplicate Sign In'

    async def test_duplicate_sign_in_with_info_overwrites(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.sign_in(sign_in_info='first')

        overwritten = await entity.sign_in(sign_in_info='second')

        assert overwritten.sign_in_info == 'second'

    async def test_query_sign_in_days(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.sign_in(date_=date(2020, 1, 1))
        await entity.sign_in(date_=date(2020, 1, 2))
        await entity.sign_in(date_=date(2020, 1, 4))

        days = await entity.query_sign_in_days()

        assert set(days) == {date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 4)}

    async def test_first_sign_in_rewards_full_amounts(self, test_onebot_v11_entity_factory) -> None:
        """首次签到: 记录今日签到日期与 Normal Sign In 信息, 好感度/能量/货币按给定数值全额发放"""
        entity = test_onebot_v11_entity_factory()

        sign_in_result, friendship_result = await entity.check_and_execute_sign_in_with_alter_friendship(
            alter_friendship=Decimal('5'),
            alter_energy=Decimal('1'),
            alter_currency=Decimal('2'),
        )

        assert sign_in_result.sign_in_date == datetime.now().date()
        assert sign_in_result.sign_in_info == 'Normal Sign In'
        assert friendship_result.friendship == Decimal('5')
        assert friendship_result.energy == Decimal('1')
        assert friendship_result.currency == Decimal('2')

    async def test_repeated_sign_in_same_day_no_double_reward(self, test_onebot_v11_entity_factory) -> None:
        """同日重复签到: 签到标记为 Duplicate Sign In, 好感度保持首签数值, 能量/货币不重复发放"""
        entity = test_onebot_v11_entity_factory()
        await entity.check_and_execute_sign_in_with_alter_friendship(alter_friendship=Decimal('5'))

        sign_in_result, friendship_result = await entity.check_and_execute_sign_in_with_alter_friendship(
            alter_friendship=Decimal('5'),
            alter_energy=Decimal('2'),
            alter_currency=Decimal('3'),
        )

        assert sign_in_result.sign_in_info == 'Duplicate Sign In'
        assert friendship_result.friendship == Decimal('5')
        assert friendship_result.energy == Decimal('0')
        assert friendship_result.currency == Decimal('0')

    async def test_repeated_explicit_date_no_double_reward(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        past_date = date(2020, 1, 1)

        await entity.check_and_execute_sign_in_with_alter_friendship(date_=past_date, alter_friendship=Decimal('7'))

        sign_in_result, friendship_result = await entity.check_and_execute_sign_in_with_alter_friendship(
            date_=past_date,
            alter_friendship=Decimal('7'),
        )

        assert sign_in_result.sign_in_info == 'Duplicate Sign In'
        assert friendship_result.friendship == Decimal('7')

        # 补签历史日期不影响今日正常签到发放
        today_sign_in, today_friendship = await entity.check_and_execute_sign_in_with_alter_friendship(
            alter_friendship=Decimal('1'),
        )
        assert today_sign_in.sign_in_info == 'Normal Sign In'
        assert today_friendship.friendship == Decimal('8')

    async def test_repeated_with_explicit_info_overrides_without_reward(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.check_and_execute_sign_in_with_alter_friendship(alter_friendship=Decimal('5'))

        sign_in_result, friendship_result = await entity.check_and_execute_sign_in_with_alter_friendship(
            alter_friendship=Decimal('5'),
            sign_in_info='Manual re-check',
        )

        assert sign_in_result.sign_in_info == 'Manual re-check'
        assert friendship_result.friendship == Decimal('5')


class TestSignInWithFriendshipConcurrency:
    """签到与好感度组合方法的并发安全与日期归一化测试"""

    async def test_sign_in_lock_acquired_before_check(
            self,
            monkeypatch: pytest.MonkeyPatch,
            test_onebot_v11_entity_factory,
    ) -> None:
        """事务内应先以 FOR UPDATE 锁定 Entity 行, 再执行重复签到检查"""
        from src.database.internal.entity import EntityDAL

        entity = test_onebot_v11_entity_factory()

        call_order: list[str] = []

        origin_query_unique = EntityDAL.query_unique
        origin_check = EntityDAL.check_entity_date_is_sign_in

        async def _spy_query_unique(self_dal: Any, *args: Any, **kwargs: Any) -> Any:
            if kwargs.get('with_for_update'):
                call_order.append('lock')
            return await origin_query_unique(self_dal, *args, **kwargs)

        async def _spy_check(self_dal: Any, *args: Any, **kwargs: Any) -> Any:
            call_order.append('check')
            return await origin_check(self_dal, *args, **kwargs)

        monkeypatch.setattr(EntityDAL, 'query_unique', _spy_query_unique)
        monkeypatch.setattr(EntityDAL, 'check_entity_date_is_sign_in', _spy_check)

        await entity.check_and_execute_sign_in_with_alter_friendship(alter_friendship=Decimal('1'))

        assert call_order == ['lock', 'check']

    async def test_sign_in_date_normalized_consistently(self, test_onebot_v11_entity_factory) -> None:
        """签到日期应在方法内归一化: 显式 datetime 落在其 date; 缺省当天保持 Normal Sign In 语义"""
        entity = test_onebot_v11_entity_factory()

        past = datetime.now() - timedelta(days=3)
        sign_in_result, _ = await entity.check_and_execute_sign_in_with_alter_friendship(
            date_=past,
            alter_friendship=Decimal('1'),
        )

        assert sign_in_result.sign_in_date == past.date()
        assert sign_in_result.sign_in_info == 'Fixed Sign In'

        sign_in_today, _ = await entity.check_and_execute_sign_in_with_alter_friendship(
            alter_friendship=Decimal('1'),
        )
        assert sign_in_today.sign_in_date == datetime.now().date()
        assert sign_in_today.sign_in_info == 'Normal Sign In'

    async def test_concurrent_sign_in_single_reward(
            self,
            test_onebot_v11_bot,
            test_onebot_v11_entity_factory,
    ) -> None:
        """两个独立会话并发签到同一 Entity, 好感度奖励只应发放一次

        后到事务要么 NOWAIT 快速失败抛出 RuntimeError (由业务层处理),
        要么在锁空闲后到达并经锁定读判重为重复签到, 两种交错下奖励均不重复发放;
        行锁/NOWAIT 依赖 MySQL/PostgreSQL 后端, SQLite 为空操作故跳过;
        注意须使用非 scoped 的独立会话 (scoped session 在非事件上下文中共享同一作用域键, 无法并发)
        """
        from src.database.connector import get_engine, get_session_factory
        from src.service.omega_base.internal.entity import OmegaEntity

        if get_engine().dialect.name == 'sqlite':
            pytest.skip('行锁/NOWAIT 对 SQLite 为空操作, 并发竞态仅 MySQL/PostgreSQL 后端可复现')

        entity = test_onebot_v11_entity_factory()
        await entity.query_entity_self()
        await entity.commit_session()

        init_kwargs: dict[str, Any] = {
            'bot_type': entity.bot_type,
            'bot_id': entity.bot_id,
            'entity_type': entity.entity_type,
            'entity_id': entity.entity_id,
        }

        async def _sign_in() -> tuple[Any, Any]:
            session_factory = get_session_factory()
            async with session_factory() as session:
                try:
                    omega_entity = OmegaEntity(session=session, **init_kwargs)
                    result = await omega_entity.check_and_execute_sign_in_with_alter_friendship(
                        alter_friendship=Decimal('1'),
                    )
                    await session.commit()
                    return result
                except:  # noqa: E722
                    await session.rollback()
                    raise

        results = await asyncio.gather(_sign_in(), _sign_in(), return_exceptions=True)

        succeeded = [x for x in results if not isinstance(x, BaseException)]
        failed = [x for x in results if isinstance(x, BaseException)]

        # 不变量: 好感度奖励只发放一次; 成功方恰为首个签到者, 失败方只能是 RuntimeError 快速失败
        assert len(succeeded) >= 1
        for sign_in, friendship in succeeded:
            assert friendship.friendship == Decimal('1')
        assert sorted(x[0].sign_in_info or '' for x in succeeded) in (
            ['Normal Sign In'],
            ['Duplicate Sign In', 'Normal Sign In'],
        )
        for exc in failed:
            assert isinstance(exc, RuntimeError)

    async def test_sign_in_lock_held_raises_runtime_error(
            self,
            test_onebot_v11_bot,
            test_onebot_v11_entity_factory,
    ) -> None:
        """Entity 行锁被其他事务持有时, 组合方法应 NOWAIT 快速失败抛出 RuntimeError

        行锁/NOWAIT 依赖 MySQL/PostgreSQL 后端, SQLite 为空操作故跳过
        """
        from src.database.connector import get_engine, get_session_factory
        from src.database.internal.entity import EntityDAL

        if get_engine().dialect.name == 'sqlite':
            pytest.skip('行锁/NOWAIT 对 SQLite 为空操作')

        entity = test_onebot_v11_entity_factory()
        await entity.query_entity_self()
        await entity.commit_session()

        session_factory = get_session_factory()
        async with session_factory() as lock_holder_session:
            try:
                # 会话1: 持有实体行锁不提交
                await EntityDAL(lock_holder_session).query_unique(
                    bot_type=entity.bot_type,
                    bot_self_id=entity.bot_id,
                    entity_type=entity.entity_type,
                    entity_id=entity.entity_id,
                    with_for_update=True,
                )

                # 会话2: 同一对象并发签到应立即失败
                async with session_factory() as session:
                    from src.service.omega_base.internal.entity import OmegaEntity

                    omega_entity = OmegaEntity(
                        session=session,
                        bot_type=entity.bot_type,
                        bot_id=entity.bot_id,
                        entity_type=entity.entity_type,
                        entity_id=entity.entity_id,
                    )
                    with pytest.raises(RuntimeError, match='并发签到处理中'):
                        await omega_entity.check_and_execute_sign_in_with_alter_friendship(
                            alter_friendship=Decimal('1'),
                        )
                    await session.rollback()
            finally:
                await lock_holder_session.rollback()

    async def test_stale_snapshot_raises_runtime_error(
            self,
            test_onebot_v11_bot,
            test_onebot_v11_entity_factory,
    ) -> None:
        """事务快照过期 (锁空闲但快照确立后有并发提交) 时, 普通读不一致应抛出 RuntimeError

        REPEATABLE READ 下旧快照看不到并发事务已提交的好感度行, 触发兜底转换;
        依赖 MySQL/PostgreSQL 后端, SQLite 跳过
        """
        from src.database.connector import get_engine, get_session_factory
        from src.service.omega_base.internal.entity import OmegaEntity

        if get_engine().dialect.name == 'sqlite':
            pytest.skip('快照可见性语义依赖 MySQL/PostgreSQL 后端的 REPEATABLE READ')

        entity = test_onebot_v11_entity_factory()
        await entity.query_entity_self()
        await entity.commit_session()

        init_kwargs: dict[str, Any] = {
            'bot_type': entity.bot_type,
            'bot_id': entity.bot_id,
            'entity_type': entity.entity_type,
            'entity_id': entity.entity_id,
        }

        session_factory = get_session_factory()

        # 会话S: 先执行一次普通读, 确立本事务的一致性读快照
        async with session_factory() as stale_session:
            stale_entity = OmegaEntity(session=stale_session, **init_kwargs)
            await stale_entity.query_entity_self()

            # 独立会话: 完成一次签到并提交 (好感度行在此提交中创建)
            async with session_factory() as session:
                omega_entity = OmegaEntity(session=session, **init_kwargs)
                await omega_entity.check_and_execute_sign_in_with_alter_friendship(
                    alter_friendship=Decimal('1'),
                )
                await session.commit()

            # 会话S: 锁空闲可获取, 但快照过期, 重复签到路径的好感度行在旧快照中不可见
            with pytest.raises(RuntimeError, match='读视图不一致'):
                await stale_entity.check_and_execute_sign_in_with_alter_friendship(
                    alter_friendship=Decimal('1'),
                )
            await stale_session.rollback()


class TestAuthSetting:
    """通用授权配置相关方法测试 (真实数据库)"""

    async def test_set_and_query_round_trip(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=1, value={'key': 'value'})
        auth_setting = await entity.query_auth_setting('MOD', 'PLG', 'ND')

        assert auth_setting.module == 'MOD'
        assert auth_setting.plugin == 'PLG'
        assert auth_setting.node == 'ND'
        assert auth_setting.available == 1
        assert auth_setting.value == {'key': 'value'}

    async def test_query_missing_raises(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        with pytest.raises(NoResultFound):
            await entity.query_auth_setting('NO_MOD', 'NO_PLG', 'NO_ND')

    async def test_query_all_and_plugin_filter(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting('MOD_A', 'PLG_A', 'ND_1', available=1, value={})
        await entity.set_auth_setting('MOD_A', 'PLG_B', 'ND_2', available=1, value={})
        await entity.set_auth_setting('MOD_B', 'PLG_A', 'ND_3', available=1, value={})

        all_settings = await entity.query_all_auth_setting()
        assert len(all_settings) == 3

        mod_a_settings = await entity.query_plugin_all_auth_setting('MOD_A', 'PLG_A')
        assert len(mod_a_settings) == 1
        assert mod_a_settings[0].node == 'ND_1'

    async def test_verify_missing_returns_zero(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        assert await entity.verify_auth_setting('NO_MOD', 'NO_PLG', 'NO_ND') == 0

    async def test_verify_strict_match(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=1, value={})

        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=1, strict_match_available=True) == 1
        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=2, strict_match_available=True) == -1

    async def test_verify_non_strict_match(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=5, value={})

        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=3, strict_match_available=False) == 1
        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=5, strict_match_available=False) == 1
        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND', available=6, strict_match_available=False) == -1

    async def test_set_overwrites_existing(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=1, value={'v': 1})

        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=0, value={'v': 2})
        auth_setting = await entity.query_auth_setting('MOD', 'PLG', 'ND')

        assert auth_setting.available == 0
        assert auth_setting.value == {'v': 2}

    async def test_delete_auth_setting(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting('MOD', 'PLG', 'ND', available=1, value={})

        await entity.delete_auth_setting('MOD', 'PLG', 'ND')

        assert await entity.verify_auth_setting('MOD', 'PLG', 'ND') == 0

    async def test_delete_missing_auth_setting_no_error(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        await entity.delete_auth_setting('NO_MOD', 'NO_PLG', 'NO_ND')


class TestInternalPermissions:
    """内置权限分支 (全局开关/权限等级/跳过冷却) 测试 (真实数据库)"""

    async def test_global_permission_default_disabled(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        assert await entity.check_global_permission() is False

    async def test_global_permission_enable_disable(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        enabled = await entity.enable_global_permission()
        assert enabled.available == 1
        assert await entity.check_global_permission() is True
        assert (await entity.query_global_permission()).available == 1

        disabled = await entity.disable_global_permission()
        assert disabled.available == 0
        assert await entity.check_global_permission() is False

    async def test_permission_level_missing(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        assert await entity.check_permission_level(1) is False

    async def test_permission_level_threshold(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_permission_level(10)

        assert await entity.check_permission_level(5) is True
        assert await entity.check_permission_level(10) is True
        assert await entity.check_permission_level(11) is False
        assert (await entity.query_permission_level()).available == 10

    async def test_permission_level_zero(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_permission_level(0)

        assert await entity.check_permission_level(0) is True
        assert await entity.check_permission_level(1) is False

    async def test_permission_level_negative(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_permission_level(-1)

        assert await entity.check_permission_level(-2) is True
        assert await entity.check_permission_level(0) is False

    async def test_skip_cooldown_permission(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        assert await entity.check_permission_skip_cooldown('MOD_A', 'PLG_A') is False

        await entity.enable_plugin_skip_cooldown_permission('MOD_A', 'PLG_A')
        assert await entity.check_permission_skip_cooldown('MOD_A', 'PLG_A') is True

        await entity.disable_plugin_skip_cooldown_permission('MOD_A', 'PLG_A')
        assert await entity.check_permission_skip_cooldown('MOD_A', 'PLG_A') is False

    async def test_skip_cooldown_permission_scoped_by_plugin(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.enable_plugin_skip_cooldown_permission('MOD_A', 'PLG_A')

        assert await entity.check_permission_skip_cooldown('MOD_A', 'PLG_B') is False
        assert await entity.check_permission_skip_cooldown('MOD_B', 'PLG_A') is False


class TestCooldown:
    """冷却事件相关方法测试 (真实数据库)"""

    async def test_set_cooldown_with_timedelta(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        cooldown = await entity.set_cooldown('TEST_EVENT', timedelta(seconds=60))

        assert cooldown.event == 'TEST_EVENT'
        assert_datetime_close(cooldown.stop_at, datetime.now() + timedelta(seconds=60))

        expired, stop_at = await entity.check_cooldown_expired('TEST_EVENT')
        assert expired is False
        assert stop_at == cooldown.stop_at

    async def test_set_cooldown_with_past_datetime(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        past = datetime.now() - timedelta(hours=1)

        await entity.set_cooldown('TEST_EVENT', past)

        expired, stop_at = await entity.check_cooldown_expired('TEST_EVENT')
        assert expired is True
        assert_datetime_close(stop_at, past)

    async def test_check_missing_cooldown_expired(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        expired, stop_at = await entity.check_cooldown_expired('NO_SUCH_EVENT')

        assert expired is True
        assert_datetime_close(stop_at, datetime.now())

    async def test_set_cooldown_invalid_type_raises(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        with pytest.raises(TypeError):
            await entity.set_cooldown('TEST_EVENT', 'not-a-time')

    async def test_set_cooldown_overwrites_existing(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_cooldown('TEST_EVENT', timedelta(seconds=60), description='first')

        cooldown = await entity.set_cooldown('TEST_EVENT', timedelta(seconds=3600), description='second')

        assert_datetime_close(cooldown.stop_at, datetime.now() + timedelta(seconds=3600))
        assert cooldown.description == 'second'

    async def test_query_cooldown_missing_raises(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        with pytest.raises(NoResultFound):
            await entity.query_cooldown('NO_SUCH_EVENT')

    async def test_global_cooldown(self, test_onebot_v11_entity_factory) -> None:
        from src.service.omega_base.internal.consts import GLOBAL_COOLDOWN_EVENT

        entity = test_onebot_v11_entity_factory()

        cooldown = await entity.set_global_cooldown(timedelta(seconds=30))

        assert cooldown.event == GLOBAL_COOLDOWN_EVENT
        assert cooldown.description == 'OmegaGlobalCooldown 全局冷却'

        expired, _ = await entity.check_global_cooldown_expired()
        assert expired is False

    async def test_global_cooldown_missing_expired(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        expired, stop_at = await entity.check_global_cooldown_expired()

        assert expired is True
        assert_datetime_close(stop_at, datetime.now())

    async def test_character_attribute_setter_cooldown(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        cooldown = await entity.set_character_attribute_setter_cooldown('level', timedelta(seconds=30))

        assert cooldown.event == 'OmegaICAttrSetter_level'
        assert cooldown.description == "角色'level'属性更新冷却"

        expired, _ = await entity.check_character_attribute_setter_cooldown_expired('level')
        assert expired is False

        missing_expired, _ = await entity.check_character_attribute_setter_cooldown_expired('other')
        assert missing_expired is True

    async def test_character_profile_setter_cooldown(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        cooldown = await entity.set_character_profile_setter_cooldown('appearance', timedelta(seconds=30))

        assert cooldown.event == 'OmegaICProfileSetter_appearance'
        assert cooldown.description == "角色'appearance'档案更新冷却"

        expired, _ = await entity.check_character_profile_setter_cooldown_expired('appearance')
        assert expired is False

        missing_expired, _ = await entity.check_character_profile_setter_cooldown_expired('other')
        assert missing_expired is True


class TestCharacterAttributeAndProfile:
    """内置角色属性/档案相关方法测试 (真实数据库)"""

    async def test_attribute_set_and_query_round_trip(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        await entity.set_character_attribute('level', 5)

        assert await entity.query_character_attribute('level') == 5

    async def test_attribute_missing_without_factory_raises(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        with pytest.raises(NoResultFound):
            await entity.query_character_attribute('no_such_attr')

    async def test_attribute_missing_with_factory_generates_and_persists(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
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

    async def test_attribute_unavailable_regenerated_by_factory(self, test_onebot_v11_entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute

        entity = test_onebot_v11_entity_factory()
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

    async def test_attribute_missing_key_regenerated_by_factory(self, test_onebot_v11_entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute

        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck', available=1, value={'other_key': 1}
        )

        value = await entity.query_character_attribute('luck', default_factory=lambda: 8)

        assert value == 8

    async def test_attribute_non_int_value(self, test_onebot_v11_entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute

        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck', available=1, value={'luck': 'abc'}
        )

        with pytest.raises(ValueError, match='invalid literal'):
            await entity.query_character_attribute('luck')

        value = await entity.query_character_attribute('luck', default_factory=lambda: 9)
        assert value == 9

    async def test_profile_set_and_query_round_trip(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        await entity.set_character_profile('appearance', {'hair': 'black'})

        assert await entity.query_character_profile('appearance') == {'hair': 'black'}

    async def test_profile_missing_without_factory_raises(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()

        with pytest.raises(NoResultFound):
            await entity.query_character_profile('no_such_profile')

    async def test_profile_missing_with_factory_generates_and_persists(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
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

    async def test_profile_unavailable_regenerated_by_factory(self, test_onebot_v11_entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterProfile

        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting(
            CharacterProfile.module, CharacterProfile.plugin, 'appearance', available=0, value={'appearance': {}}
        )

        value = await entity.query_character_profile('appearance', default_factory=lambda: {'new': 1})

        assert value == {'new': 1}

    async def test_profile_missing_key_regenerated_by_factory(self, test_onebot_v11_entity_factory) -> None:
        """存储的 value 字典缺少目标键时, 提供 default_factory 应重新生成并持久化"""
        from src.service.omega_base.internal.consts import CharacterProfile

        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting(
            CharacterProfile.module, CharacterProfile.plugin, 'appearance', available=1, value={'other_key': {}}
        )

        value = await entity.query_character_profile('appearance', default_factory=lambda: {'gen': True})

        assert value == {'gen': True}
        auth_setting = await entity.query_auth_setting(
            CharacterProfile.module, CharacterProfile.plugin, 'appearance'
        )
        assert auth_setting.value == {'appearance': {'gen': True}}

    async def test_profile_missing_key_without_factory_raises(self, test_onebot_v11_entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterProfile

        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting(
            CharacterProfile.module, CharacterProfile.plugin, 'appearance', available=1, value={'other_key': {}}
        )

        with pytest.raises(KeyError):
            await entity.query_character_profile('appearance')

    async def test_delete_character_attribute(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_character_attribute('level', 5)

        await entity.delete_character_attribute('level')

        with pytest.raises(NoResultFound):
            await entity.query_character_attribute('level')

    async def test_delete_character_profile(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_character_profile('appearance', {'hair': 'black'})

        await entity.delete_character_profile('appearance')

        with pytest.raises(NoResultFound):
            await entity.query_character_profile('appearance')

    async def test_query_all_character_attribute_and_profile(self, test_onebot_v11_entity_factory) -> None:
        entity = test_onebot_v11_entity_factory()
        await entity.set_character_attribute('level', 5)
        await entity.set_character_attribute('luck', 7)
        await entity.set_character_profile('appearance', {'hair': 'black'})

        attributes = await entity.query_all_character_attribute()
        assert len(attributes) == 2
        assert {x.node for x in attributes} == {'level', 'luck'}

        profiles = await entity.query_all_character_profile()
        assert len(profiles) == 1
        assert profiles[0].node == 'appearance'

    async def test_attribute_none_value_with_factory_regenerates(self, test_onebot_v11_entity_factory) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute

        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck', available=1, value={'luck': None},
        )

        assert await entity.query_character_attribute('luck', default_factory=lambda: 42) == 42

        auth_setting = await entity.query_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck',
        )
        assert auth_setting.available == 1
        assert auth_setting.value == {'luck': 42}

    async def test_attribute_none_value_without_factory_raises_type_error(
            self, test_onebot_v11_entity_factory,
    ) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute

        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck', available=1, value={'luck': None},
        )

        with pytest.raises(TypeError):
            await entity.query_character_attribute('luck')

    async def test_unavailable_attribute_error_message_distinguished(
            self, test_onebot_v11_entity_factory,
    ) -> None:
        from src.service.omega_base.internal.consts import CharacterAttribute

        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting(
            CharacterAttribute.module, CharacterAttribute.plugin, 'luck', available=0, value={'luck': 99},
        )

        with pytest.raises(ValueError, match="CharacterAttribute 'luck' is not available"):
            await entity.query_character_attribute('luck')

    async def test_unavailable_profile_error_message_distinguished(
            self, test_onebot_v11_entity_factory,
    ) -> None:
        from src.service.omega_base.internal.consts import CharacterProfile

        entity = test_onebot_v11_entity_factory()
        await entity.set_auth_setting(
            CharacterProfile.module, CharacterProfile.plugin, 'pf', available=0, value={'pf': {'k': 'v'}},
        )

        with pytest.raises(ValueError, match="CharacterProfile 'pf' is not available"):
            await entity.query_character_profile('pf')


class TestSubscription:
    """订阅相关方法测试 (真实数据库)"""

    async def test_add_and_query_subscription(self, test_onebot_v11_entity_factory, test_subscription_source) -> None:
        entity = test_onebot_v11_entity_factory()

        added = await entity.add_subscription(test_subscription_source, sub_info='sub-info')

        assert added.id == test_subscription_source.id
        assert added.sub_type == test_subscription_source.sub_type
        assert added.sub_id == test_subscription_source.sub_id

        subscribed = await entity.query_subscribed_source()
        assert len(subscribed) == 1
        assert subscribed[0].id == test_subscription_source.id

    async def test_query_subscribed_source_filter_by_sub_type(
            self, test_onebot_v11_entity_factory, test_subscription_sources,
    ) -> None:
        source_a, source_b = test_subscription_sources
        entity = test_onebot_v11_entity_factory()
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

    async def test_query_subscribed_source_entity_not_exists(
            self,
            test_onebot_v11_entity_factory,
            test_onebot_v11_bot,
    ) -> None:
        """Entity 不存在时返回空列表, 且不会自动创建 Entity"""
        from src.database.internal.entity import EntityType

        entity = test_onebot_v11_entity_factory()

        assert await entity.query_subscribed_source() == []
        assert await _query_entity_or_none(
            test_onebot_v11_bot.self_id,
            EntityType.ONEBOT_V11_USER,
            entity.entity_id,
        ) is None

    async def test_add_subscription_duplicate_updates_sub_info(
            self,
            test_onebot_v11_entity_factory,
            test_subscription_source,
    ) -> None:
        from sqlalchemy import select

        from src.database.helpers import database_session
        from src.database.schema import SubscriptionOrm

        entity = test_onebot_v11_entity_factory()
        await entity.add_subscription(test_subscription_source, sub_info='sub-info-v1')
        await entity.add_subscription(test_subscription_source, sub_info='sub-info-v2')
        await entity.commit_session()

        entity_row = await entity.query_entity_self()
        async with database_session() as session:
            stmt = select(SubscriptionOrm).where(
                SubscriptionOrm.entity_index_id == entity_row.id,
                SubscriptionOrm.sub_source_index_id == test_subscription_source.id,
            )
            links = (await session.execute(stmt)).scalars().all()

        assert len(links) == 1
        assert links[0].sub_info == 'sub-info-v2'

    async def test_delete_subscription(self, test_onebot_v11_entity_factory, test_subscription_sources) -> None:
        source_a, source_b = test_subscription_sources
        entity = test_onebot_v11_entity_factory()
        await entity.add_subscription(source_a)
        await entity.add_subscription(source_b)

        await entity.delete_subscription(source_a)

        subscribed = await entity.query_subscribed_source()
        assert len(subscribed) == 1
        assert subscribed[0].id == source_b.id

    async def test_delete_missing_subscription_no_error(
            self, test_onebot_v11_entity_factory, test_subscription_source,
    ) -> None:
        entity = test_onebot_v11_entity_factory()

        await entity.delete_subscription(test_subscription_source)
