"""
@Author         : Ailitonia
@Date           : 2026/8/28 20:16
@FileName       : test_global_cache
@Project        : omega-miya
@Description    : src/database/internal/global_cache.py 数据库 CRUD 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound

if TYPE_CHECKING:
    from src.database.internal.global_cache import GlobalCacheDAL


@pytest.fixture(scope='class')
async def test_global_cache_name() -> str:
    return f'CACHE_NAME_{random.randint(0, 1000)}'


@pytest.fixture(scope='class')
async def test_global_cache_key() -> str:
    return f'CACHE_KEY_{random.randint(0, 1000)}'


@pytest.fixture(scope='class')
async def test_global_cache_value() -> str:
    return f'CACHE_VALUE_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def global_cache_dal() -> AsyncGenerator['GlobalCacheDAL', None]:
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        yield dal


class TestGlobalCacheDAL:
    """GlobalCacheDAL CRUD 单元测试"""

    async def test_check_clear_table(self, global_cache_dal) -> None:
        """清空数据表, 查回验证表行数为空"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        rows_num = await global_cache_dal._count_all()

        assert rows_num == 0

    async def test_clear_all_rollback(
            self,
            global_cache_dal,
            test_global_cache_name,
            test_global_cache_key,
            test_global_cache_value,
    ) -> None:
        """_clear_all 不执行 commit, 外层事务 rollback 后数据应恢复"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=test_global_cache_value,
        )
        await global_cache_dal.commit_session()

        await global_cache_dal._clear_all()
        assert await global_cache_dal._count_all() == 0

        await global_cache_dal.rollback_session()
        assert await global_cache_dal._count_all() == 1

    # ------------------------------------------------------------------ #
    # add
    # ------------------------------------------------------------------ #

    async def test_add_basic(
            self,
            global_cache_dal,
            test_global_cache_name,
            test_global_cache_key,
            test_global_cache_value,
    ) -> None:
        """插入一条记录 (默认过期时间), 查回验证字段正确, expired_at 为 9999-12-31"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        result = await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=test_global_cache_value,
        )
        await global_cache_dal.commit_session()

        assert result.cache_name == test_global_cache_name
        assert result.cache_key == test_global_cache_key
        assert result.cache_value == test_global_cache_value
        assert result.expired_at == datetime(year=9999, month=12, day=31)

        queried = await global_cache_dal.query_unique(test_global_cache_name, test_global_cache_key)
        assert queried.cache_value == test_global_cache_value

    async def test_add_with_timedelta(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """expired_time 为 timedelta 时, expired_at 应在 now 到 now+timedelta 范围内"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        delta = timedelta(seconds=60)
        expected_from = datetime.now() + delta
        result = await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key='key_timedelta',
            cache_value='value_timedelta',
            expired_time=delta,
        )
        await global_cache_dal.commit_session()
        expected_to = datetime.now() + delta

        # 数据库 datetime 可能截断到秒, 留 2 秒容差
        tolerance = timedelta(seconds=2)
        assert expected_from - tolerance <= result.expired_at <= expected_to + tolerance

    async def test_add_with_datetime(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """expired_time 为 datetime 时, expired_at 应等于传入值"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        target = datetime(year=2099, month=6, day=15, hour=12, minute=0, second=0)
        result = await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key='key_datetime',
            cache_value='value_datetime',
            expired_time=target,
        )
        await global_cache_dal.commit_session()

        assert result.expired_at == target

    async def test_add_duplicate_raises(
            self,
            global_cache_dal,
            test_global_cache_name,
            test_global_cache_key,
            test_global_cache_value,
    ) -> None:
        """对同一 (cache_name, cache_key) 插入两次, 预期 IntegrityError"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=test_global_cache_value,
        )
        await global_cache_dal.commit_session()

        with pytest.raises(IntegrityError):
            await global_cache_dal.add(
                cache_name=test_global_cache_name,
                cache_key=test_global_cache_key,
                cache_value='another_value',
            )

        # 回滚到正常状态
        await global_cache_dal.rollback_session()

        queried = await global_cache_dal.query_unique(test_global_cache_name, test_global_cache_key)
        assert queried.cache_value == test_global_cache_value

    async def test_add_expired_datetime(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """expired_time 为过去时间, 插入后默认查询查不到 (抛 NoResultFound)"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        past = datetime(1990, 1, 1, 0, 0, 0)
        await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key='key_expired',
            cache_value='value_expired',
            expired_time=past,
        )
        await global_cache_dal.commit_session()

        with pytest.raises(NoResultFound):
            await global_cache_dal.query_unique(test_global_cache_name, 'key_expired')

    # ------------------------------------------------------------------ #
    # query_unique
    # ------------------------------------------------------------------ #

    async def test_query_unique_not_found(
            self,
            global_cache_dal,
    ) -> None:
        """查询不存在的 key, 预期 NoResultFound"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        with pytest.raises(NoResultFound):
            await global_cache_dal.query_unique('nonexistent_name', 'nonexistent_key')

    async def test_query_unique_exclude_expired(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """插入过期记录, 默认查询查不到; include_expired=True 能查到"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        past = datetime(1990, 1, 1, 0, 0, 0)
        await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key='key_expired',
            cache_value='value_expired',
            expired_time=past,
        )
        await global_cache_dal.commit_session()

        # 默认排除过期 -- 查不到
        with pytest.raises(NoResultFound):
            await global_cache_dal.query_unique(test_global_cache_name, 'key_expired')

        # include_expired=True -- 能查到
        queried = await global_cache_dal.query_unique(
            test_global_cache_name, 'key_expired', include_expired=True,
        )
        assert queried.cache_value == 'value_expired'

    async def test_query_unique_normal(
            self,
            global_cache_dal,
            test_global_cache_name,
            test_global_cache_key,
            test_global_cache_value,
    ) -> None:
        """插入未过期记录, 正常查回"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=test_global_cache_value,
        )
        await global_cache_dal.commit_session()

        queried = await global_cache_dal.query_unique(test_global_cache_name, test_global_cache_key)
        assert queried.cache_name == test_global_cache_name
        assert queried.cache_key == test_global_cache_key
        assert queried.cache_value == test_global_cache_value

    # ------------------------------------------------------------------ #
    # query_series
    # ------------------------------------------------------------------ #

    async def test_query_series_multiple(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """同一 cache_name 插入多条不同 cache_key, 查回列表长度正确"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        keys = ['series_key_1', 'series_key_2', 'series_key_3']
        for key in keys:
            await global_cache_dal.add(
                cache_name=test_global_cache_name,
                cache_key=key,
                cache_value=f'value_{key}',
            )
        await global_cache_dal.commit_session()

        result = await global_cache_dal.query_series(test_global_cache_name)
        assert len(result) == len(keys)
        result_keys = {item.cache_key for item in result}
        assert result_keys == set(keys)

    async def test_query_series_exclude_expired(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """同一 cache_name 下混入过期记录, 默认查询排除; include_expired=True 全部查回"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        past = datetime(1990, 1, 1, 0, 0, 0)
        future = datetime(year=9999, month=12, day=31)

        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='expired_1', cache_value='v1', expired_time=past,
        )
        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='active_1', cache_value='v2', expired_time=future,
        )
        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='active_2', cache_value='v3', expired_time=future,
        )
        await global_cache_dal.commit_session()

        # 默认排除过期
        active = await global_cache_dal.query_series(test_global_cache_name)
        assert len(active) == 2
        assert {item.cache_key for item in active} == {'active_1', 'active_2'}

        # include_expired=True
        all_items = await global_cache_dal.query_series(test_global_cache_name, include_expired=True)
        assert len(all_items) == 3
        assert {item.cache_key for item in all_items} == {'active_1', 'active_2', 'expired_1'}

    async def test_query_series_empty(
            self,
            global_cache_dal,
    ) -> None:
        """查询不存在的 cache_name, 返回空列表"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        result = await global_cache_dal.query_series('nonexistent_cache_name')
        assert result == []

    async def test_add_update_exist_insert(
            self,
            global_cache_dal,
            test_global_cache_name,
            test_global_cache_key,
            test_global_cache_value,
    ) -> None:
        """首次调用 add_update_exist, 验证为插入行为"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        result = await global_cache_dal.add_update_exist(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=test_global_cache_value,
        )
        await global_cache_dal.commit_session()

        assert result.cache_name == test_global_cache_name
        assert result.cache_key == test_global_cache_key
        assert result.cache_value == test_global_cache_value

        # 确认确实写入了一条
        queried = await global_cache_dal.query_unique(test_global_cache_name, test_global_cache_key)
        assert queried.cache_value == test_global_cache_value

    # ------------------------------------------------------------------ #
    # add_update_exist
    # ------------------------------------------------------------------ #

    async def test_add_update_exist_update(
            self,
            global_cache_dal,
            test_global_cache_name,
            test_global_cache_key,
            test_global_cache_value,
    ) -> None:
        """先 add 插入, 再 add_update_exist 更新为新 value, 验证返回新值"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=test_global_cache_value,
        )
        await global_cache_dal.commit_session()

        new_value = f'{test_global_cache_value}_updated'
        result = await global_cache_dal.add_update_exist(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=new_value,
        )
        await global_cache_dal.commit_session()

        assert result.cache_name == test_global_cache_name
        assert result.cache_key == test_global_cache_key
        assert result.cache_value == new_value

        queried = await global_cache_dal.query_unique(
            test_global_cache_name, test_global_cache_key, include_expired=True,
        )
        assert queried.cache_value == new_value

    async def test_add_update_exist_with_timedelta(
            self,
            global_cache_dal,
            test_global_cache_name,
            test_global_cache_key,
            test_global_cache_value,
    ) -> None:
        """add_update_exist 带 timedelta 过期时间, 验证更新后 expired_at 变化"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        # 先插入一条带默认过期时间 (9999-12-31) 的记录
        await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=test_global_cache_value,
        )
        await global_cache_dal.commit_session()

        # 用 add_update_exist 更新, 设置 60 秒后过期
        delta = timedelta(seconds=60)
        expected_from = datetime.now() + delta
        result = await global_cache_dal.add_update_exist(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value='new_value',
            expired_time=delta,
        )
        await global_cache_dal.commit_session()
        expected_to = datetime.now() + delta

        assert result.cache_name == test_global_cache_name
        assert result.cache_key == test_global_cache_key
        assert result.cache_value == 'new_value'
        # 数据库 datetime 可能截断到秒, 留 2 秒容差
        tolerance = timedelta(seconds=2)
        assert expected_from - tolerance <= result.expired_at <= expected_to + tolerance

    async def test_add_update_exist_expired_record(
            self,
            global_cache_dal,
            test_global_cache_name,
            test_global_cache_key,
            test_global_cache_value,
    ) -> None:
        """对已过期记录调用 add_update_exist, 应为更新续期而非插入新行"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        past = datetime(1990, 1, 1, 0, 0, 0)
        await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=test_global_cache_value,
            expired_time=past,
        )
        await global_cache_dal.commit_session()

        result = await global_cache_dal.add_update_exist(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value='renewed_value',
        )
        await global_cache_dal.commit_session()

        assert result.cache_value == 'renewed_value'

        # 过期时间被续期为默认值 (9999-12-31), 默认查询 (排除过期) 可以查到
        queried = await global_cache_dal.query_unique(test_global_cache_name, test_global_cache_key)
        assert queried.cache_value == 'renewed_value'
        assert queried.expired_at == datetime(year=9999, month=12, day=31)

        # 全表仍只有一条记录, 证明是更新而非插入
        assert await global_cache_dal._count_all() == 1

    async def test_add_update_exist_with_datetime(
            self,
            global_cache_dal,
            test_global_cache_name,
            test_global_cache_key,
            test_global_cache_value,
    ) -> None:
        """add_update_exist 带 datetime 过期时间更新已有记录, expired_at 应等于传入值"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        await global_cache_dal.add(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value=test_global_cache_value,
        )
        await global_cache_dal.commit_session()

        target = datetime(year=2099, month=6, day=15, hour=12, minute=0, second=0)
        result = await global_cache_dal.add_update_exist(
            cache_name=test_global_cache_name,
            cache_key=test_global_cache_key,
            cache_value='new_value',
            expired_time=target,
        )
        await global_cache_dal.commit_session()

        assert result.cache_value == 'new_value'
        assert result.expired_at == target

    # ------------------------------------------------------------------ #
    # delete_series_expired
    # ------------------------------------------------------------------ #

    async def test_delete_series_expired(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """同一 cache_name 下有过期和未过期记录, delete_series_expired 仅删除过期项"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        past = datetime(1990, 1, 1, 0, 0, 0)
        future = datetime(year=9999, month=12, day=31)

        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='exp_1', cache_value='v1', expired_time=past,
        )
        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='exp_2', cache_value='v2', expired_time=past,
        )
        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='alive_1', cache_value='v3', expired_time=future,
        )
        await global_cache_dal.commit_session()

        await global_cache_dal.delete_series_expired(test_global_cache_name)
        await global_cache_dal.commit_session()

        remaining = await global_cache_dal.query_series(test_global_cache_name, include_expired=True)
        remaining_keys = {item.cache_key for item in remaining}
        assert remaining_keys == {'alive_1'}

    async def test_delete_series_expired_only_affects_target_name(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """delete_series_expired 只删除指定 cache_name 的过期记录, 不影响其他 cache_name"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        past = datetime(1990, 1, 1, 0, 0, 0)

        # 目标 cache_name 的过期记录
        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='exp_1', cache_value='v1', expired_time=past,
        )
        # 另一个 cache_name 的过期记录 (不应被删除)
        await global_cache_dal.add(
            cache_name='other_cache_name', cache_key='exp_other', cache_value='v2', expired_time=past,
        )
        await global_cache_dal.commit_session()

        await global_cache_dal.delete_series_expired(test_global_cache_name)
        await global_cache_dal.commit_session()

        # 目标 cache_name 已清空
        target_remaining = await global_cache_dal.query_series(test_global_cache_name, include_expired=True)
        assert len(target_remaining) == 0

        # other_cache_name 的过期记录仍在
        other_remaining = await global_cache_dal.query_series('other_cache_name', include_expired=True)
        assert len(other_remaining) == 1
        assert other_remaining[0].cache_key == 'exp_other'

    # ------------------------------------------------------------------ #
    # delete_all_expired
    # ------------------------------------------------------------------ #

    async def test_delete_all_expired(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """跨多个 cache_name 的过期与未过期记录, delete_all_expired 删除所有过期项"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        past = datetime(1990, 1, 1, 0, 0, 0)
        future = datetime(year=9999, month=12, day=31)

        # 两个 cache_name, 各自一条过期 + 一条未过期
        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='exp_1', cache_value='v1', expired_time=past,
        )
        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='alive_1', cache_value='v2', expired_time=future,
        )
        await global_cache_dal.add(
            cache_name='other_cache_name', cache_key='exp_2', cache_value='v3', expired_time=past,
        )
        await global_cache_dal.add(
            cache_name='other_cache_name', cache_key='alive_2', cache_value='v4', expired_time=future,
        )
        await global_cache_dal.commit_session()

        await global_cache_dal.delete_all_expired()
        await global_cache_dal.commit_session()

        # 目标 cache_name 只剩未过期
        target = await global_cache_dal.query_series(test_global_cache_name, include_expired=True)
        assert {item.cache_key for item in target} == {'alive_1'}

        # other_cache_name 只剩未过期
        other = await global_cache_dal.query_series('other_cache_name', include_expired=True)
        assert {item.cache_key for item in other} == {'alive_2'}

        # 全表只剩 2 条
        assert await global_cache_dal._count_all() == 2

    async def test_delete_all_expired_when_no_expired(
            self,
            global_cache_dal,
            test_global_cache_name,
    ) -> None:
        """无过期记录时, delete_all_expired 不影响任何数据"""
        await global_cache_dal._clear_all()
        await global_cache_dal.commit_session()

        future = datetime(year=9999, month=12, day=31)
        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='alive_1', cache_value='v1', expired_time=future,
        )
        await global_cache_dal.add(
            cache_name=test_global_cache_name, cache_key='alive_2', cache_value='v2', expired_time=future,
        )
        await global_cache_dal.commit_session()

        await global_cache_dal.delete_all_expired()
        await global_cache_dal.commit_session()

        assert await global_cache_dal._count_all() == 2
        remaining = await global_cache_dal.query_series(test_global_cache_name, include_expired=True)
        assert len(remaining) == 2
