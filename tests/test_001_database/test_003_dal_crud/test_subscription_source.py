"""
@Author         : Ailitonia
@Date           : 2026/9/1 17:23
@FileName       : test_subscription_source
@Project        : omega-miya
@Description    : subscription_source.py  数据库 CRUD 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from src.database.internal.subscription_source import SubscriptionSourceDAL


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
async def subscription_source_dal() -> AsyncGenerator['SubscriptionSourceDAL', None]:
    from src.database.internal.subscription_source import SubscriptionSourceDAL

    async with SubscriptionSourceDAL.create() as dal:
        yield dal


class TestSubscriptionSourceDAL:
    """SubscriptionSourceDAL CRUD 单元测试"""

    async def test_check_clear_table(self, subscription_source_dal) -> None:
        """清空数据表, 查回验证表行数为空"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        rows_num = await subscription_source_dal._count_all()

        assert rows_num == 0

    async def test_clear_all_rollback(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """_clear_all 不执行 commit, 外层事务 rollback 后数据应恢复"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
        )
        await subscription_source_dal.commit_session()

        await subscription_source_dal._clear_all()
        assert await subscription_source_dal._count_all() == 0

        await subscription_source_dal.rollback_session()
        assert await subscription_source_dal._count_all() == 1

    # ------------------------------------------------------------------ #
    # query_unique
    # ------------------------------------------------------------------ #

    async def test_query_unique_normal(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """插入后按 (sub_type, sub_id) 查回验证字段"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
            sub_info='test info',
        )
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.query_unique(test_sub_type, test_sub_id)
        assert result.sub_type == test_sub_type
        assert result.sub_id == test_sub_id
        assert result.sub_user_name == test_sub_user_name
        assert result.sub_info == 'test info'
        assert result.entities_subscription_source_had == []

    async def test_query_unique_not_found(self, subscription_source_dal) -> None:
        """查询不存在的记录, 预期 NoResultFound"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        with pytest.raises(NoResultFound):
            await subscription_source_dal.query_unique('nonexistent_type', 'nonexistent_id')

    # ------------------------------------------------------------------ #
    # 级联关系加载 (entities_subscription_source_had)
    # ------------------------------------------------------------------ #

    async def test_query_unique_with_subscribed_entities(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """存在订阅实体时, query_unique/query_all 应正确加载 entities_subscription_source_had"""
        from src.database.schema import BotSelfOrm, EntityOrm, SubscriptionOrm, SubscriptionSourceOrm

        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        # 构造 Bot -> Entity -> SubscriptionSource -> Subscription 链路 (命名带随机后缀避免重跑冲突)
        session = subscription_source_dal.db_session
        bot_obj = BotSelfOrm(bot_type='Console', self_id=f'sub_test_bot_q_{test_sub_id}', bot_status=1)
        source_obj = SubscriptionSourceOrm(
            sub_type=test_sub_type, sub_id=test_sub_id, sub_user_name=test_sub_user_name,
        )
        session.add_all([bot_obj, source_obj])
        await session.flush()

        entity_obj = EntityOrm(
            bot_index_id=bot_obj.id,
            entity_id=f'sub_test_entity_q_{test_sub_id}',
            entity_type='console_user',
            entity_name='sub test entity',
        )
        session.add(entity_obj)
        await session.flush()

        session.add(SubscriptionOrm(sub_source_index_id=source_obj.id, entity_index_id=entity_obj.id))
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.query_unique(test_sub_type, test_sub_id)
        assert len(result.entities_subscription_source_had) == 1
        subscribed = result.entities_subscription_source_had[0]
        assert subscribed.id == entity_obj.id
        assert subscribed.bot_index_id == bot_obj.id
        assert subscribed.entity_type == 'console_user'
        assert subscribed.entity_id == f'sub_test_entity_q_{test_sub_id}'
        assert subscribed.entity_name == 'sub test entity'

        result_all = await subscription_source_dal.query_all()
        assert len(result_all) == 1
        assert len(result_all[0].entities_subscription_source_had) == 1

    # ------------------------------------------------------------------ #
    # query_all
    # ------------------------------------------------------------------ #

    async def test_query_all_multiple(self, subscription_source_dal) -> None:
        """插入多条, 验证返回全部且按 (sub_type, sub_id) 排序"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        # 故意按非字典序插入
        await subscription_source_dal.add_update_exist(sub_type='type_b', sub_id='id_3', sub_user_name='user_c')
        await subscription_source_dal.add_update_exist(sub_type='type_a', sub_id='id_2', sub_user_name='user_b')
        await subscription_source_dal.add_update_exist(sub_type='type_a', sub_id='id_1', sub_user_name='user_a')
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.query_all()
        assert len(result) == 3
        result_keys = [(item.sub_type, item.sub_id) for item in result]
        assert result_keys == [('type_a', 'id_1'), ('type_a', 'id_2'), ('type_b', 'id_3')]

    async def test_query_all_empty(self, subscription_source_dal) -> None:
        """空表返回空列表"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.query_all()
        assert result == []

    # ------------------------------------------------------------------ #
    # query_type_all
    # ------------------------------------------------------------------ #

    async def test_query_type_all_filtered(self, subscription_source_dal) -> None:
        """插入多个 sub_type, 查询指定 sub_type 只返回匹配项"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.add_update_exist(sub_type='type_a', sub_id='id_1', sub_user_name='user_a')
        await subscription_source_dal.add_update_exist(sub_type='type_a', sub_id='id_2', sub_user_name='user_b')
        await subscription_source_dal.add_update_exist(sub_type='type_b', sub_id='id_3', sub_user_name='user_c')
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.query_type_all('type_a')
        assert len(result) == 2
        assert all(item.sub_type == 'type_a' for item in result)

        result_b = await subscription_source_dal.query_type_all('type_b')
        assert len(result_b) == 1
        assert result_b[0].sub_id == 'id_3'

    async def test_query_type_all_ordering(self, subscription_source_dal) -> None:
        """验证结果按 (sub_type, sub_id) 排序"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        # 故意按非字典序插入
        await subscription_source_dal.add_update_exist(sub_type='type_a', sub_id='id_3', sub_user_name='user_c')
        await subscription_source_dal.add_update_exist(sub_type='type_a', sub_id='id_1', sub_user_name='user_a')
        await subscription_source_dal.add_update_exist(sub_type='type_a', sub_id='id_2', sub_user_name='user_b')
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.query_type_all('type_a')
        result_ids = [item.sub_id for item in result]
        assert result_ids == ['id_1', 'id_2', 'id_3']

    async def test_query_type_all_empty(self, subscription_source_dal) -> None:
        """不存在的 sub_type 返回空列表"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.query_type_all('nonexistent_type')
        assert result == []

    # ------------------------------------------------------------------ #
    # add_update_exist
    # ------------------------------------------------------------------ #

    async def test_add_update_exist_insert(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """首次调用 add_update_exist, 验证为插入行为"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
            sub_info='insert info',
        )
        await subscription_source_dal.commit_session()

        assert result.sub_type == test_sub_type
        assert result.sub_id == test_sub_id
        assert result.sub_user_name == test_sub_user_name
        assert result.sub_info == 'insert info'
        assert result.entities_subscription_source_had == []

        assert await subscription_source_dal._count_all() == 1

    async def test_add_update_exist_insert_without_info(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """sub_info=None 插入验证"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
        )
        await subscription_source_dal.commit_session()

        assert result.sub_info is None

        queried = await subscription_source_dal.query_unique(test_sub_type, test_sub_id)
        assert queried.sub_info is None

    async def test_add_update_exist_insert_with_info(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """sub_info='explicit info' 插入验证"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
            sub_info='explicit info',
        )
        await subscription_source_dal.commit_session()

        assert result.sub_info == 'explicit info'

        queried = await subscription_source_dal.query_unique(test_sub_type, test_sub_id)
        assert queried.sub_info == 'explicit info'

    async def test_add_update_exist_update(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """同 (sub_type, sub_id) 再次调用更新 user_name/info, 验证返回新值"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
            sub_info='original info',
        )
        await subscription_source_dal.commit_session()

        new_name = f'{test_sub_user_name}_updated'
        result = await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=new_name,
            sub_info='updated info',
        )
        await subscription_source_dal.commit_session()

        assert result.sub_user_name == new_name
        assert result.sub_info == 'updated info'

        # 更新而非新增, 全表仍只有一行
        assert await subscription_source_dal._count_all() == 1

        queried = await subscription_source_dal.query_unique(test_sub_type, test_sub_id)
        assert queried.sub_user_name == new_name
        assert queried.sub_info == 'updated info'

    async def test_add_update_exist_update_with_none_info(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """先带 info 插入, 再 add_update_exist 用 sub_info=None 更新, 验证 info 被更新为 None"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
            sub_info='original info',
        )
        await subscription_source_dal.commit_session()

        result = await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
            sub_info=None,
        )
        await subscription_source_dal.commit_session()

        assert result.sub_info is None

        queried = await subscription_source_dal.query_unique(test_sub_type, test_sub_id)
        assert queried.sub_info is None

    # ------------------------------------------------------------------ #
    # add_update_exist — 嵌套事务 (SAVEPOINT) 路径
    # ------------------------------------------------------------------ #

    async def test_add_update_exist_in_nested_transaction_insert(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """外层已有活动事务时插入分支走 SAVEPOINT, 外层 rollback 后插入应被撤销

        注意: SQLite 后端 (aiosqlite 默认 legacy 事务控制, 会话事务不显式发送 BEGIN) 下,
        外层事务的首个语句若为 SAVEPOINT 则物理事务由 SAVEPOINT 开启且 RELEASE 即提交,
        外层 rollback 无法撤销插入, 属驱动层限制而非 DAL 逻辑问题, 故本平台跳过该用例
        """
        from src.database.config import database_config
        if database_config.database == 'sqlite':
            pytest.skip('SQLite 驱动 legacy 事务控制下嵌套插入无法被外层事务回滚, 跳过')

        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.db_session.begin()
        result = await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
            sub_info='nested info',
        )
        assert result.sub_id == test_sub_id
        assert result.sub_info == 'nested info'
        assert await subscription_source_dal._count_all() == 1

        await subscription_source_dal.rollback_session()
        assert await subscription_source_dal._count_all() == 0

    async def test_add_update_exist_in_nested_transaction_update(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """外层已有活动事务时更新分支走 SAVEPOINT, 外层 rollback 后更新应被撤销"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
            sub_info='original info',
        )
        await subscription_source_dal.commit_session()

        await subscription_source_dal.db_session.begin()
        result = await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=f'{test_sub_user_name}_nested',
            sub_info='nested updated info',
        )
        assert result.sub_user_name == f'{test_sub_user_name}_nested'
        assert result.sub_info == 'nested updated info'

        # 外层事务内可见更新
        queried = await subscription_source_dal.query_unique(test_sub_type, test_sub_id)
        assert queried.sub_user_name == f'{test_sub_user_name}_nested'
        assert queried.sub_info == 'nested updated info'

        await subscription_source_dal.rollback_session()

        # 外层 rollback 后恢复为更新前的值
        queried = await subscription_source_dal.query_unique(test_sub_type, test_sub_id)
        assert queried.sub_user_name == test_sub_user_name
        assert queried.sub_info == 'original info'

    # ------------------------------------------------------------------ #
    # delete
    # ------------------------------------------------------------------ #

    async def test_delete_existing(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """插入后 delete, 用 query_unique 查不到 (NoResultFound)"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type,
            sub_id=test_sub_id,
            sub_user_name=test_sub_user_name,
        )
        await subscription_source_dal.commit_session()

        await subscription_source_dal.delete(test_sub_type, test_sub_id)
        await subscription_source_dal.commit_session()

        with pytest.raises(NoResultFound):
            await subscription_source_dal.query_unique(test_sub_type, test_sub_id)

    async def test_delete_non_existing(self, subscription_source_dal) -> None:
        """删除不存在的记录, 不抛异常"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.delete('nonexistent_type', 'nonexistent_id')
        await subscription_source_dal.commit_session()

        assert await subscription_source_dal._count_all() == 0

    async def test_delete_only_affects_target(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """插入多条, delete 只删除目标记录, 其他不受影响"""
        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type, sub_id=test_sub_id, sub_user_name=test_sub_user_name,
        )
        await subscription_source_dal.add_update_exist(
            sub_type=test_sub_type, sub_id='other_id', sub_user_name='other_user',
        )
        await subscription_source_dal.commit_session()

        await subscription_source_dal.delete(test_sub_type, test_sub_id)
        await subscription_source_dal.commit_session()

        # 目标记录已删除
        with pytest.raises(NoResultFound):
            await subscription_source_dal.query_unique(test_sub_type, test_sub_id)

        # 其他记录仍在
        remaining = await subscription_source_dal.query_type_all(test_sub_type)
        assert len(remaining) == 1
        assert remaining[0].sub_id == 'other_id'

        assert await subscription_source_dal._count_all() == 1

    async def test_delete_cascade_subscription(
            self,
            subscription_source_dal,
            test_sub_type,
            test_sub_id,
            test_sub_user_name,
    ) -> None:
        """删除订阅源后, subscription 表中的关联行应被级联清除"""
        from sqlalchemy import func, select

        from src.database.schema import BotSelfOrm, EntityOrm, SubscriptionOrm, SubscriptionSourceOrm

        await subscription_source_dal._clear_all()
        await subscription_source_dal.commit_session()

        # 构造 Bot -> Entity -> SubscriptionSource -> Subscription 链路 (命名带随机后缀避免重跑冲突)
        session = subscription_source_dal.db_session
        bot_obj = BotSelfOrm(bot_type='Console', self_id=f'sub_test_bot_d_{test_sub_id}', bot_status=1)
        source_obj = SubscriptionSourceOrm(
            sub_type=test_sub_type, sub_id=test_sub_id, sub_user_name=test_sub_user_name,
        )
        session.add_all([bot_obj, source_obj])
        await session.flush()

        entity_obj = EntityOrm(
            bot_index_id=bot_obj.id,
            entity_id=f'sub_test_entity_d_{test_sub_id}',
            entity_type='console_user',
            entity_name='sub test entity',
        )
        session.add(entity_obj)
        await session.flush()

        session.add(SubscriptionOrm(sub_source_index_id=source_obj.id, entity_index_id=entity_obj.id))
        await subscription_source_dal.commit_session()

        # 删除订阅源
        await subscription_source_dal.delete(test_sub_type, test_sub_id)
        await subscription_source_dal.commit_session()

        # 关联订阅行已被级联清除
        stmt = (select(func.count())
                .select_from(SubscriptionOrm)
                .where(SubscriptionOrm.sub_source_index_id == source_obj.id))
        assert (await session.execute(stmt)).scalar_one() == 0
