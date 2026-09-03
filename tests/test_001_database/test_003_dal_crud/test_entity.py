"""
@Author         : Ailitonia
@Date           : 2026/9/2 19:16
@FileName       : test_entity
@Project        : omega-miya
@Description    : entity.py 数据库 CRUD 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from collections.abc import AsyncGenerator
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from src.database.internal.bot import BotSelf, BotSelfDAL
    from src.database.internal.entity import EntityDAL
    from src.database.internal.subscription_source import SubscriptionSource, SubscriptionSourceDAL


@pytest.fixture(scope='class')
async def test_bot_type() -> str:
    return 'OneBot V11'


@pytest.fixture(scope='class')
async def test_bot_self_id() -> str:
    return f'TEST_BOT_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_entity_type() -> str:
    return 'onebot_v11_user'


@pytest.fixture(scope='class')
async def test_entity_id() -> str:
    return f'TEST_ENTITY_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_entity_name() -> str:
    return f'TEST_ENTITY_NAME_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_sub_type() -> str:
    return f'TEST_SUB_TYPE_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_sub_id() -> str:
    return f'TEST_SUB_ID_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_sub_user_name() -> str:
    return f'TEST_SUB_USER_NAME_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def bot_dal(
        test_bot_type,
        test_bot_self_id,
) -> AsyncGenerator['BotSelfDAL', None]:
    from src.database.internal.bot import BotSelfDAL

    async with BotSelfDAL.create() as dal:
        try:
            await dal._clear_all()
            await dal.add_update_exist(test_bot_type, test_bot_self_id, 1)
            yield dal
        finally:
            await dal._clear_all()


@pytest.fixture(scope='class')
async def test_bot(
        bot_dal,
        test_bot_type,
        test_bot_self_id,
) -> 'BotSelf':
    return await bot_dal.query_unique(test_bot_type, test_bot_self_id, None)


@pytest.fixture(scope='class')
async def subscription_source_dal(
        test_sub_type,
        test_sub_id,
        test_sub_user_name,
) -> AsyncGenerator['SubscriptionSourceDAL', None]:
    from src.database.internal.subscription_source import SubscriptionSourceDAL

    async with SubscriptionSourceDAL.create() as dal:
        try:
            await dal._clear_all()
            await dal.add_update_exist(test_sub_type, test_sub_id, test_sub_user_name)
            yield dal
        finally:
            await dal._clear_all()


@pytest.fixture(scope='class')
async def test_subscription_source(
        subscription_source_dal,
        test_sub_type,
        test_sub_id,
) -> 'SubscriptionSource':
    return await subscription_source_dal.query_unique(test_sub_type, test_sub_id)


@pytest.fixture(scope='class')
async def entity_dal(bot_dal, subscription_source_dal) -> AsyncGenerator['EntityDAL', None]:
    from src.database.internal.entity import EntityDAL

    async with EntityDAL.create() as dal:
        yield dal


class TestEntityDAL:
    """EntityDAL CRUD 单元测试"""

    async def test_check_clear_table(self, entity_dal) -> None:
        """清空数据表, 查回验证表行数为空"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        assert await entity_dal._count_entity_all() == 0
        assert await entity_dal._count_entity_friendship_all() == 0
        assert await entity_dal._count_entity_sign_in_all() == 0
        assert await entity_dal._count_entity_auth_setting_all() == 0
        assert await entity_dal._count_entity_cooldown_all() == 0
        assert await entity_dal._count_entity_subscription_all() == 0

    async def test_clear_all_rollback(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
            test_subscription_source,
    ) -> None:
        """_clear_all 不执行 commit, 外层事务 rollback 后主表与全部子表数据应恢复"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.set_entity_friendship(entity.id, friendship=Decimal('10'))
        await entity_dal.set_entity_sign_in(entity.id, date_=date(2026, 1, 1))
        await entity_dal.set_entity_auth_setting(entity.id, 'mod', 'plug', 'node', available=1, value={})
        await entity_dal.set_entity_cooldown(entity.id, 'event', datetime(2099, 1, 1))
        await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id)
        await entity_dal.commit_session()

        await entity_dal._clear_all()
        assert await entity_dal._count_entity_all() == 0
        assert await entity_dal._count_entity_friendship_all() == 0
        assert await entity_dal._count_entity_sign_in_all() == 0
        assert await entity_dal._count_entity_auth_setting_all() == 0
        assert await entity_dal._count_entity_cooldown_all() == 0
        assert await entity_dal._count_entity_subscription_all() == 0

        await entity_dal.rollback_session()
        assert await entity_dal._count_entity_all() == 1
        assert await entity_dal._count_entity_friendship_all() == 1
        assert await entity_dal._count_entity_sign_in_all() == 1
        assert await entity_dal._count_entity_auth_setting_all() == 1
        assert await entity_dal._count_entity_cooldown_all() == 1
        assert await entity_dal._count_entity_subscription_all() == 1

    # ------------------------------------------------------------------ #
    # Entity 自身 — add_update_exist
    # ------------------------------------------------------------------ #

    async def test_add_update_exist_insert(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """首次插入验证字段 + entity_parent_bot 加载"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        result = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
            entity_info='test info',
        )
        await entity_dal.commit_session()

        assert result.entity_type == test_entity_type
        assert result.entity_id == test_entity_id
        assert result.entity_name == test_entity_name
        assert result.entity_info == 'test info'
        assert result.bot_index_id == test_bot.id
        assert result.entity_parent_bot.self_id == test_bot.self_id

    async def test_add_update_exist_insert_without_info(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """entity_info=None 插入"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        result = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        assert result.entity_info is None

    async def test_add_update_exist_update(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """同 (bot, entity_type, entity_id) 再次调用更新 name/info"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
            entity_info='original',
        )
        await entity_dal.commit_session()

        result = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name='updated_name',
            entity_info='updated_info',
        )
        await entity_dal.commit_session()

        assert result.entity_name == 'updated_name'
        assert result.entity_info == 'updated_info'
        assert await entity_dal._count_entity_all() == 1

    async def test_add_update_exist_update_with_none_info(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """先带 info 插入, 再更新 info=None"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
            entity_info='original',
        )
        await entity_dal.commit_session()

        result = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
            entity_info=None,
        )
        await entity_dal.commit_session()

        assert result.entity_info is None

    # ------------------------------------------------------------------ #
    # Entity 自身 — add_update_exist 嵌套事务 (SAVEPOINT) 路径
    # ------------------------------------------------------------------ #

    async def test_add_update_exist_in_nested_transaction_insert(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """外层已有活动事务时插入分支走 SAVEPOINT, 外层 rollback 后插入应被撤销

        注意: SQLite 后端 (aiosqlite 默认 legacy 事务控制, 会话事务不显式发送 BEGIN) 下,
        外层事务的首个语句若为 SAVEPOINT 则物理事务由 SAVEPOINT 开启且 RELEASE 即提交,
        外层 rollback 无法撤销插入, 属驱动层限制而非 DAL 逻辑问题, 故本平台跳过该用例
        """
        from src.database.config import database_config
        if database_config.database == 'sqlite':
            pytest.skip('SQLite 驱动 legacy 事务控制下嵌套插入无法被外层事务回滚, 跳过')

        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.db_session.begin()
        result = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        assert result.entity_id == test_entity_id
        assert await entity_dal._count_entity_all() == 1

        await entity_dal.rollback_session()
        assert await entity_dal._count_entity_all() == 0

    async def test_add_update_exist_in_nested_transaction_update(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """外层已有活动事务时更新分支走 SAVEPOINT, 外层 rollback 后更新应被撤销"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.db_session.begin()
        result = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=f'{test_entity_name}_nested',
            entity_info='nested info',
        )
        assert result.entity_name == f'{test_entity_name}_nested'
        assert result.entity_info == 'nested info'

        await entity_dal.rollback_session()

        # 外层 rollback 后恢复为更新前的值
        queried = await entity_dal.query_unique(
            test_bot.bot_type, test_bot.self_id, test_entity_type, test_entity_id, None,
        )
        assert queried.entity_name == test_entity_name
        assert queried.entity_info is None

    # ------------------------------------------------------------------ #
    # Entity 自身 — add_ignore_exist
    # ------------------------------------------------------------------ #

    async def test_add_ignore_exist_insert(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """首次插入"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        result = await entity_dal.add_ignore_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
            entity_info='info',
        )
        await entity_dal.commit_session()

        assert result.entity_id == test_entity_id
        assert result.entity_name == test_entity_name
        assert result.entity_info == 'info'

    async def test_add_ignore_exist_ignored(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """已存在时忽略, 返回原数据不变"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
            entity_info='original',
        )
        await entity_dal.commit_session()

        result = await entity_dal.add_ignore_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name='ignored_name',
            entity_info='ignored_info',
        )
        await entity_dal.commit_session()

        assert result.entity_name == test_entity_name
        assert result.entity_info == 'original'

    async def test_add_update_exist_bot_not_found(
            self,
            entity_dal,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """所属 Bot 不存在时调用 add_update_exist, 预期 NoResultFound"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        with pytest.raises(NoResultFound):
            await entity_dal.add_update_exist(
                bot_type='Console',
                bot_self_id='nonexistent_bot_self_id',
                entity_type=test_entity_type,
                entity_id=test_entity_id,
                entity_name=test_entity_name,
            )

    async def test_add_ignore_exist_bot_not_found(
            self,
            entity_dal,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """所属 Bot 不存在时调用 add_ignore_exist, 预期 NoResultFound"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        with pytest.raises(NoResultFound):
            await entity_dal.add_ignore_exist(
                bot_type='Console',
                bot_self_id='nonexistent_bot_self_id',
                entity_type=test_entity_type,
                entity_id=test_entity_id,
                entity_name=test_entity_name,
            )

    # ------------------------------------------------------------------ #
    # Entity 自身 — query_unique
    # ------------------------------------------------------------------ #

    async def test_query_unique_by_bot_self_id(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """按 (bot_type, bot_self_id, entity_type, entity_id) 查"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_unique(
            test_bot.bot_type,
            test_bot.self_id,
            test_entity_type,
            test_entity_id,
            None,
        )
        assert result.entity_id == test_entity_id
        assert result.entity_name == test_entity_name

    async def test_query_unique_by_index_id(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """按 index_id 查"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        added = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_unique(None, None, None, None, added.id)
        assert result.id == added.id
        assert result.entity_id == test_entity_id

    async def test_query_unique_index_id_takes_precedence(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_name,
    ) -> None:
        """同时提供时 index_id 优先"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_a',
            entity_name=test_entity_name,
        )
        a2 = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_b',
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_unique(
            test_bot.bot_type,
            test_bot.self_id,
            test_entity_type,
            'eid_a',
            a2.id,
        )
        assert result.id == a2.id
        assert result.entity_id == 'eid_b'

    async def test_query_unique_not_found(self, entity_dal) -> None:
        """查询不存在, 预期 NoResultFound"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        with pytest.raises(NoResultFound):
            await entity_dal.query_unique('Console', 'nonexistent', 'console_user', 'nonexistent', None)

    async def test_query_unique_insufficient_params_raises(self, entity_dal) -> None:
        """不全提供 bot_type 等参数时 ValueError"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        with pytest.raises(ValueError, match='must both be provided'):
            await entity_dal.query_unique('Console', None, None, None, None)

    async def test_query_unique_load_all_rel(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """load_all_rel=True 返回 EntityWithFullRel 带级联属性"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_unique(
            test_bot.bot_type,
            test_bot.self_id,
            test_entity_type,
            test_entity_id,
            None,
            load_all_rel=True,
        )
        assert result.friendship_belonged_to_entity == []
        assert result.sign_in_belonged_to_entity == []
        assert result.auth_belonged_to_entity == []
        assert result.cooldown_belonged_to_entity == []
        assert result.subscription_sources_entity_had == []

    async def test_query_unique_load_all_rel_populated(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
            test_subscription_source,
    ) -> None:
        """load_all_rel=True 且存在关联数据时, 应正确带出全部级联属性"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.set_entity_friendship(entity.id, friendship=Decimal('100'))
        await entity_dal.set_entity_sign_in(entity.id, date_=date(2026, 1, 1), sign_in_info='rel test')
        await entity_dal.set_entity_auth_setting(entity.id, 'mod', 'plug', 'node', available=1, value={'k': 'v'})
        await entity_dal.set_entity_cooldown(entity.id, 'event', datetime(2099, 1, 1))
        await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id)
        await entity_dal.commit_session()

        result = await entity_dal.query_unique(
            test_bot.bot_type,
            test_bot.self_id,
            test_entity_type,
            test_entity_id,
            None,
            load_all_rel=True,
        )

        assert len(result.friendship_belonged_to_entity) == 1
        assert result.friendship_belonged_to_entity[0].friendship == Decimal('100')
        assert result.friendship_belonged_to_entity[0].friendship_parent_entity.id == entity.id

        assert len(result.sign_in_belonged_to_entity) == 1
        assert result.sign_in_belonged_to_entity[0].sign_in_date == date(2026, 1, 1)
        assert result.sign_in_belonged_to_entity[0].sign_in_info == 'rel test'

        assert len(result.auth_belonged_to_entity) == 1
        assert result.auth_belonged_to_entity[0].module == 'mod'
        assert result.auth_belonged_to_entity[0].value == {'k': 'v'}

        assert len(result.cooldown_belonged_to_entity) == 1
        assert result.cooldown_belonged_to_entity[0].event == 'event'

        assert len(result.subscription_sources_entity_had) == 1
        assert result.subscription_sources_entity_had[0].id == test_subscription_source.id
        assert result.subscription_sources_entity_had[0].sub_type == test_subscription_source.sub_type

    # ------------------------------------------------------------------ #
    # Entity 自身 — query_all / query_type_all / delete_from_index
    # ------------------------------------------------------------------ #

    async def test_query_all_multiple(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_name,
    ) -> None:
        """多条 + 排序"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_c',
            entity_name=test_entity_name,
        )
        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_a',
            entity_name=test_entity_name,
        )
        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_b',
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_all()
        assert len(result) == 3
        assert [item.entity_id for item in result] == ['eid_a', 'eid_b', 'eid_c']

    async def test_query_all_empty(self, entity_dal) -> None:
        """空表"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        assert await entity_dal.query_all() == []

    async def test_query_type_all_filtered(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_name,
    ) -> None:
        """按 bot+type 过滤"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_a',
            entity_name=test_entity_name,
        )
        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type='onebot_v11_group',
            entity_id='gid_a',
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_type_all(test_bot.bot_type, test_bot.self_id, test_entity_type)
        assert len(result) == 1
        assert result[0].entity_id == 'eid_a'

    async def test_query_type_all_empty(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
    ) -> None:
        """不匹配返回空"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        result = await entity_dal.query_type_all(test_bot.bot_type, test_bot.self_id, test_entity_type)
        assert result == []

    async def test_delete_from_index(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """删除后查不到"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        added = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.delete_from_index(added.id)
        await entity_dal.commit_session()

        with pytest.raises(NoResultFound):
            await entity_dal.query_unique(None, None, None, None, added.id)

    async def test_delete_from_index_non_existing(self, entity_dal) -> None:
        """不存在不抛异常"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        await entity_dal.delete_from_index(999999)
        await entity_dal.commit_session()

    # ------------------------------------------------------------------ #
    # Friendship
    # ------------------------------------------------------------------ #

    async def test_set_friendship_insert(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """首次设置验证字段 (Decimal)"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_friendship(
            entity.id,
            status='happy',
            mood=Decimal('5.5'),
            friendship=Decimal('100'),
            energy=Decimal('50'),
            currency=Decimal('25'),
            rsp_threshold=Decimal('3'),
        )
        await entity_dal.commit_session()

        assert result.status == 'happy'
        assert result.mood == Decimal('5.5')
        assert result.friendship == Decimal('100')
        assert result.energy == Decimal('50')
        assert result.currency == Decimal('25')
        assert result.rsp_threshold == Decimal('3')
        assert result.entity_index_id == entity.id

    async def test_set_friendship_update(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """再次设置更新值"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_friendship(
            entity.id,
            mood=Decimal('1'),
            friendship=Decimal('10'),
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_friendship(
            entity.id,
            status='sad',
            mood=Decimal('2'),
            friendship=Decimal('20'),
        )
        await entity_dal.commit_session()

        assert result.status == 'sad'
        assert result.mood == Decimal('2')
        assert result.friendship == Decimal('20')

    async def test_set_friendship_default_values(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """默认值全为 0 / status='normal'"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_friendship(entity.id)
        await entity_dal.commit_session()

        assert result.status == 'normal'
        assert result.mood == Decimal('0')
        assert result.friendship == Decimal('0')
        assert result.energy == Decimal('0')
        assert result.currency == Decimal('0')
        assert result.rsp_threshold == Decimal('0')

    async def test_set_friendship_partial_update_preserves_others(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """部分更新语义: 仅传入的字段被更新, 未传入的字段 (None) 保持原值"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_friendship(
            entity.id,
            status='happy',
            mood=Decimal('5'),
            friendship=Decimal('100'),
            energy=Decimal('50'),
            currency=Decimal('25'),
            rsp_threshold=Decimal('3'),
        )
        await entity_dal.commit_session()

        # 仅更新 currency, 其余字段应保持不变
        result = await entity_dal.set_entity_friendship(entity.id, currency=Decimal('999'))
        await entity_dal.commit_session()

        assert result.currency == Decimal('999')
        assert result.status == 'happy'
        assert result.mood == Decimal('5')
        assert result.friendship == Decimal('100')
        assert result.energy == Decimal('50')
        assert result.rsp_threshold == Decimal('3')

    async def test_set_friendship_all_none_no_change(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """全部参数缺省时 (仅提供 entity_index_id), 已有记录的字段不应被修改"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_friendship(entity.id, status='happy', friendship=Decimal('42'))
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_friendship(entity.id)
        await entity_dal.commit_session()

        assert result.status == 'happy'
        assert result.friendship == Decimal('42')

    async def test_change_friendship_increment(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """先 set 再 change, 验证增量累加"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_friendship(
            entity.id,
            mood=Decimal('10'),
            friendship=Decimal('100'),
            energy=Decimal('50'),
        )
        await entity_dal.commit_session()

        result = await entity_dal.change_entity_friendship(
            entity.id,
            mood=Decimal('5'),
            friendship=Decimal('20'),
            energy=Decimal('-10'),
        )
        await entity_dal.commit_session()

        assert result.mood == Decimal('15')
        assert result.friendship == Decimal('120')
        assert result.energy == Decimal('40')

    async def test_change_friendship_insert_new(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """无好感度记录时直接 change, 应插入新行且 delta 即为初始值"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.change_entity_friendship(
            entity.id,
            mood=Decimal('5'),
            friendship=Decimal('20'),
            energy=Decimal('-10'),
        )
        await entity_dal.commit_session()

        assert result.status == 'normal'
        assert result.mood == Decimal('5')
        assert result.friendship == Decimal('20')
        assert result.energy == Decimal('-10')
        assert await entity_dal._count_entity_friendship_all() == 1

    async def test_query_friendship_exists(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """已有 friendship 直接返回"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_friendship(entity.id, friendship=Decimal('50'))
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_friendship(entity.id)
        assert result.friendship == Decimal('50')

    async def test_query_friendship_auto_init(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """没有 friendship 时自动初始化默认值"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_friendship(entity.id)
        assert result.status == 'normal'
        assert result.friendship == Decimal('0')

    # ------------------------------------------------------------------ #
    # SignIn
    # ------------------------------------------------------------------ #

    async def test_set_sign_in_with_date(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """指定 date 对象, info 默认 'Fixed Sign In'"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_sign_in(entity.id, date_=date(2026, 1, 1))
        await entity_dal.commit_session()

        assert result.sign_in_date == date(2026, 1, 1)
        assert result.sign_in_info == 'Fixed Sign In'

    async def test_set_sign_in_with_datetime(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """指定 datetime 对象, 自动取 .date()"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_sign_in(
            entity.id,
            date_=datetime(2026, 1, 1, 12, 30, 30),
            sign_in_info='custom',
        )
        await entity_dal.commit_session()

        assert result.sign_in_date == date(2026, 1, 1)
        assert result.sign_in_info == 'custom'

    async def test_set_sign_in_none_date(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """date_=None 用今天, info 默认 'Normal Sign In'"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_sign_in(entity.id)
        await entity_dal.commit_session()

        assert result.sign_in_date == datetime.now().date()
        assert result.sign_in_info == 'Normal Sign In'

    async def test_set_sign_in_duplicate(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """同日重复签到且未指定 sign_in_info 时, 签到信息应标记为 'Duplicate Sign In'"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_sign_in(entity.id, date_=date(2026, 1, 1), sign_in_info='first')
        await entity_dal.commit_session()

        # 重复签到且未指定 sign_in_info, 应标记为 'Duplicate Sign In'
        result = await entity_dal.set_entity_sign_in(entity.id, date_=date(2026, 1, 1))
        await entity_dal.commit_session()

        assert result.sign_in_info == 'Duplicate Sign In'

    async def test_check_sign_in_true(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """已签到返回 True"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_sign_in(entity.id, date_=date(2026, 1, 1))
        await entity_dal.commit_session()

        assert await entity_dal.check_entity_today_is_sign_in(entity.id, date_=date(2026, 1, 1)) is True

    async def test_check_sign_in_false(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """未签到返回 False"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type, bot_self_id=test_bot.self_id,
            entity_type=test_entity_type, entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        assert await entity_dal.check_entity_today_is_sign_in(entity.id, date_=date(2026, 1, 1)) is False

    async def test_query_sign_in_days(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """多天签到返回日期列表"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_sign_in(entity.id, date_=date(2024, 2, 4))
        await entity_dal.set_entity_sign_in(entity.id, date_=date(2025, 10, 17))
        await entity_dal.set_entity_sign_in(entity.id, date_=date(2026, 5, 28))
        await entity_dal.commit_session()

        days = await entity_dal.query_entity_sign_in_days(entity.id)
        assert set(days) == {date(2026, 5, 28), date(2025, 10, 17), date(2024, 2, 4)}

    # ------------------------------------------------------------------ #
    # AuthSetting
    # ------------------------------------------------------------------ #

    async def test_set_auth_insert(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """首次设置验证字段 + JSON value"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_auth_setting(
            entity.id,
            'test_module',
            'test_plugin',
            'test_node',
            available=1,
            value={'key': 'val', 'nested': {'a': 1}},
        )
        await entity_dal.commit_session()

        assert result.module == 'test_module'
        assert result.plugin == 'test_plugin'
        assert result.node == 'test_node'
        assert result.available == 1
        assert result.value == {'key': 'val', 'nested': {'a': 1}}

    async def test_set_auth_update(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """更新 available 和 value"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(
            entity.id,
            'test_module',
            'test_plugin',
            'test_node',
            available=0,
            value={'a': 1},
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_auth_setting(
            entity.id,
            'test_module',
            'test_plugin',
            'test_node',
            available=1,
            value={'b': 2},
        )
        await entity_dal.commit_session()

        assert result.available == 1
        assert result.value == {'b': 2}

    async def test_set_auth_empty_value(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """value 为空 {}"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_auth_setting(
            entity.id,
            'test_module',
            'test_plugin',
            'test_node',
            available=1,
            value={},
        )
        await entity_dal.commit_session()

        assert result.value == {}

    async def test_query_auth_setting_normal(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """查回验证"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(
            entity.id,
            'test_module',
            'test_plugin',
            'test_node',
            available=1,
            value={'test_value': True},
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_auth_setting(
            entity.id,
            'test_module',
            'test_plugin',
            'test_node',
        )
        assert result.available == 1
        assert result.value == {'test_value': True}

    async def test_query_auth_setting_not_found(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """NoResultFound"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        with pytest.raises(NoResultFound):
            await entity_dal.query_entity_auth_setting(entity.id, 'test_module', 'test_plugin', 'test_node')

    async def test_query_any_auth_all(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """查全部 auth"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(entity.id, 'mod_a', 'plug_a', 'node_1', available=1, value={})
        await entity_dal.set_entity_auth_setting(entity.id, 'mod_b', 'plug_b', 'node_2', available=0, value={})
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_any_auth_settings(entity.id)
        assert len(result) == 2

    async def test_query_any_auth_by_module(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """按 module 过滤"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type, bot_self_id=test_bot.self_id,
            entity_type=test_entity_type, entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(entity.id, 'mod_a', 'plug_a', 'node_1', available=1, value={})
        await entity_dal.set_entity_auth_setting(entity.id, 'mod_a', 'plug_b', 'node_2', available=1, value={})
        await entity_dal.set_entity_auth_setting(entity.id, 'mod_b', 'plug_c', 'node_3', available=1, value={})
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_any_auth_settings(entity.id, module='mod_a')
        assert len(result) == 2
        assert all(item.module == 'mod_a' for item in result)

    async def test_query_any_auth_by_module_plugin(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """按 module+plugin 过滤"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type, bot_self_id=test_bot.self_id,
            entity_type=test_entity_type, entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(entity.id, 'mod_a', 'plug_a', 'node_1', available=1, value={})
        await entity_dal.set_entity_auth_setting(entity.id, 'mod_a', 'plug_b', 'node_2', available=1, value={})
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_any_auth_settings(entity.id, module='mod_a', plugin='plug_a')
        assert len(result) == 1
        assert result[0].node == 'node_1'

    async def test_query_any_auth_empty(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """无配置返回空"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_any_auth_settings(entity.id)
        assert result == []

    async def test_query_module_plugin_auth(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_name,
    ) -> None:
        """跨实体查询某 module+plugin 的所有配置"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        e1 = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_a',
            entity_name=test_entity_name,
        )
        e2 = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_b',
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(e1.id, 'mod', 'plug', 'node_1', available=1, value={})
        await entity_dal.set_entity_auth_setting(e2.id, 'mod', 'plug', 'node_2', available=0, value={})
        await entity_dal.commit_session()

        result = await entity_dal.query_module_plugin_any_auth_settings('mod', 'plug')
        assert len(result) == 2

    async def test_query_entities_has_auth(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_name,
    ) -> None:
        """查有特定权限节点的实体"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        e1 = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_a',
            entity_name=test_entity_name,
        )
        await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_b',
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(e1.id, 'mod', 'plug', 'node', available=1, value={})
        await entity_dal.commit_session()

        result = await entity_dal.query_entities_has_auth_setting('mod', 'plug', 'node')
        assert len(result) == 1
        assert result[0].entity_id == 'eid_a'

    async def test_query_entities_has_auth_strict_match(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_name,
    ) -> None:
        """strict_match=True 只匹配 available==1"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        e1 = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_a',
            entity_name=test_entity_name,
        )
        e2 = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_b',
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(e1.id, 'mod', 'plug', 'node', available=1, value={})
        await entity_dal.set_entity_auth_setting(e2.id, 'mod', 'plug', 'node', available=2, value={})
        await entity_dal.commit_session()

        result = await entity_dal.query_entities_has_auth_setting(
            'mod',
            'plug',
            'node',
            available=1,
            strict_match=True,
        )
        assert len(result) == 1
        assert result[0].entity_id == 'eid_a'

    async def test_query_entities_has_auth_non_strict(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_name,
    ) -> None:
        """strict_match=False 匹配 available>=1"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        e1 = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_a',
            entity_name=test_entity_name,
        )
        e2 = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id='eid_b',
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(e1.id, 'mod', 'plug', 'node', available=1, value={})
        await entity_dal.set_entity_auth_setting(e2.id, 'mod', 'plug', 'node', available=2, value={})
        await entity_dal.commit_session()

        result = await entity_dal.query_entities_has_auth_setting(
            'mod',
            'plug',
            'node',
            available=1,
            strict_match=False,
        )
        assert len(result) == 2

    async def test_delete_auth_setting(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """删除后查不到"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_auth_setting(entity.id, 'mod', 'plug', 'node', available=1, value={})
        await entity_dal.commit_session()

        await entity_dal.delete_entity_auth_setting(entity.id, 'mod', 'plug', 'node')
        await entity_dal.commit_session()

        with pytest.raises(NoResultFound):
            await entity_dal.query_entity_auth_setting(entity.id, 'mod', 'plug', 'node')

    async def test_delete_auth_setting_non_existing(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """不存在不抛异常"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.delete_entity_auth_setting(entity.id, 'mod', 'plug', 'node')
        await entity_dal.commit_session()

    # ------------------------------------------------------------------ #
    # Cooldown
    # ------------------------------------------------------------------ #

    async def test_set_cooldown_datetime(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """expired_time 为 datetime"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        stop = datetime(2099, 1, 1, 0, 0, 0)
        result = await entity_dal.set_entity_cooldown(entity.id, 'test_event', stop, 'desc')
        await entity_dal.commit_session()

        assert result.stop_at == stop
        assert result.description == 'desc'
        assert result.event == 'test_event'

    async def test_set_cooldown_timedelta(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """expired_time 为 timedelta"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        before = datetime.now()
        result = await entity_dal.set_entity_cooldown(entity.id, 'test_event', timedelta(seconds=60))
        await entity_dal.commit_session()

        # 数据库 datetime 可能截断到秒, 留 1 秒容差
        tolerance = timedelta(seconds=1)
        assert before + timedelta(seconds=60) - tolerance <= result.stop_at

    async def test_set_cooldown_invalid_type_raises(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """非 datetime/timedelta 抛 TypeError"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type, bot_self_id=test_bot.self_id,
            entity_type=test_entity_type, entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        with pytest.raises(TypeError):
            await entity_dal.set_entity_cooldown(entity.id, 'test_event', 'invalid')

    async def test_set_cooldown_update(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """同 event 再次设置更新 stop_at"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_cooldown(entity.id, 'event', datetime(2020, 1, 1))
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_cooldown(entity.id, 'event', datetime(2099, 1, 1))
        await entity_dal.commit_session()

        assert result.stop_at == datetime(2099, 1, 1)

    async def test_query_cooldown_normal(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """查回验证"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_cooldown(entity.id, 'event', datetime(2099, 1, 1))
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_cooldown(entity.id, 'event')
        assert result.event == 'event'
        assert result.stop_at == datetime(2099, 1, 1)

    async def test_query_cooldown_not_found(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """NoResultFound"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        with pytest.raises(NoResultFound):
            await entity_dal.query_entity_cooldown(entity.id, 'event')

    async def test_check_cooldown_expired(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """stop_at 已过返回 (True, stop_at)"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        past = datetime(1990, 1, 1)
        await entity_dal.set_entity_cooldown(entity.id, 'event', past)
        await entity_dal.commit_session()

        expired, stop_at = await entity_dal.check_entity_cooldown_is_expired(entity.id, 'event')
        assert expired is True
        assert stop_at == past

    async def test_check_cooldown_not_expired(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """stop_at 未过返回 (False, stop_at)"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        future = datetime(2099, 1, 1)
        await entity_dal.set_entity_cooldown(entity.id, 'event', future)
        await entity_dal.commit_session()

        expired, stop_at = await entity_dal.check_entity_cooldown_is_expired(entity.id, 'event')
        assert expired is False
        assert stop_at == future

    async def test_check_cooldown_not_exist(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """不存在返回 (True, now)"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        before = datetime.now()
        expired, stop_at = await entity_dal.check_entity_cooldown_is_expired(entity.id, 'event')
        assert expired is True
        assert stop_at >= before

    async def test_delete_cooldown(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """删除后查不到"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_cooldown(entity.id, 'event', datetime(2099, 1, 1))
        await entity_dal.commit_session()

        await entity_dal.delete_entity_cooldown(entity.id, 'event')
        await entity_dal.commit_session()

        with pytest.raises(NoResultFound):
            await entity_dal.query_entity_cooldown(entity.id, 'event')

    async def test_clear_expired_cooldown(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """只删过期的, 未过期保留"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_cooldown(entity.id, 'past_event', datetime(1990, 1, 1))
        await entity_dal.set_entity_cooldown(entity.id, 'future_event', datetime(2099, 1, 1))
        await entity_dal.commit_session()

        await entity_dal.clear_all_expired_cooldown()
        await entity_dal.commit_session()

        assert await entity_dal._count_entity_cooldown_all() == 1
        remaining = await entity_dal.query_entity_cooldown(entity.id, 'future_event')
        assert remaining.event == 'future_event'

    # ------------------------------------------------------------------ #
    # Subscription
    # ------------------------------------------------------------------ #

    async def test_set_subscription_insert(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
            test_subscription_source,
    ) -> None:
        """首次设置验证"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_subscription(
            entity.id,
            test_subscription_source.id,
            sub_info='sub info',
        )
        await entity_dal.commit_session()

        assert result.entity_index_id == entity.id
        assert result.sub_source_index_id == test_subscription_source.id
        assert result.sub_info == 'sub info'

    async def test_set_subscription_update(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
            test_subscription_source,
    ) -> None:
        """再次设置更新 sub_info"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id, 'original')
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id, 'updated')
        await entity_dal.commit_session()

        assert result.sub_info == 'updated'

    async def test_set_subscription_update_with_none_info(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
            test_subscription_source,
    ) -> None:
        """sub_info=None 不更新已有值"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id, 'original')
        await entity_dal.commit_session()

        result = await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id, None)
        await entity_dal.commit_session()

        assert result.sub_info == 'original'

    async def test_query_subscribed_source_all(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
            test_subscription_source,
    ) -> None:
        """查全部订阅源"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id)
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_subscribed_source(entity.id)
        assert len(result) == 1
        assert result[0].sub_id == test_subscription_source.sub_id

    async def test_query_subscribed_source_by_type(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
            test_subscription_source,
            test_sub_type,
    ) -> None:
        """按 sub_type 过滤"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id)
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_subscribed_source(entity.id, sub_type=test_sub_type)
        assert len(result) == 1

        result_empty = await entity_dal.query_entity_subscribed_source(entity.id, sub_type='nonexistent')
        assert result_empty == []

    async def test_query_subscribed_source_empty(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
    ) -> None:
        """无订阅返回空"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_subscribed_source(entity.id)
        assert result == []

    async def test_delete_subscription(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
            test_subscription_source,
    ) -> None:
        """删除后查不到"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id)
        await entity_dal.commit_session()

        await entity_dal.delete_entity_subscription(entity.id, test_subscription_source.id)
        await entity_dal.commit_session()

        result = await entity_dal.query_entity_subscribed_source(entity.id)
        assert result == []

    # ------------------------------------------------------------------ #
    # delete_from_index 级联验证
    # ------------------------------------------------------------------ #

    async def test_delete_from_index_cascade(
            self,
            entity_dal,
            test_bot,
            test_entity_type,
            test_entity_id,
            test_entity_name,
            test_subscription_source,
    ) -> None:
        """删除 entity 后 friendship/sign_in/auth/cooldown/subscription 均被级联删除"""
        await entity_dal._clear_all()
        await entity_dal.commit_session()

        entity = await entity_dal.add_update_exist(
            bot_type=test_bot.bot_type,
            bot_self_id=test_bot.self_id,
            entity_type=test_entity_type,
            entity_id=test_entity_id,
            entity_name=test_entity_name,
        )
        await entity_dal.commit_session()

        await entity_dal.set_entity_friendship(entity.id, friendship=Decimal('10'))
        await entity_dal.set_entity_sign_in(entity.id, date_=date(2026, 1, 1))
        await entity_dal.set_entity_auth_setting(entity.id, 'mod', 'plug', 'node', available=1, value={})
        await entity_dal.set_entity_cooldown(entity.id, 'event', datetime(2099, 1, 1))
        await entity_dal.set_entity_subscription(entity.id, test_subscription_source.id)
        await entity_dal.commit_session()

        assert await entity_dal._count_entity_friendship_all() == 1
        assert await entity_dal._count_entity_sign_in_all() == 1
        assert await entity_dal._count_entity_auth_setting_all() == 1
        assert await entity_dal._count_entity_cooldown_all() == 1
        assert await entity_dal._count_entity_subscription_all() == 1

        await entity_dal.delete_from_index(entity.id)
        await entity_dal.commit_session()

        assert await entity_dal._count_entity_all() == 0
        assert await entity_dal._count_entity_friendship_all() == 0
        assert await entity_dal._count_entity_sign_in_all() == 0
        assert await entity_dal._count_entity_auth_setting_all() == 0
        assert await entity_dal._count_entity_cooldown_all() == 0
        assert await entity_dal._count_entity_subscription_all() == 0
