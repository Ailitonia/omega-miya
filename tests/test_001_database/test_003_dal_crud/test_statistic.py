"""
@Author         : Ailitonia
@Date           : 2026/8/29 23:47
@FileName       : test_statistic
@Project        : omega-miya
@Description    : statistic.py 数据库 CRUD 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from src.database.internal.statistic import StatisticDAL


@pytest.fixture(scope='class')
async def test_statistic_plugin_name() -> str:
    return f'PLUGIN_NAME_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_statistic_plugin_module() -> str:
    return f'PLUGIN_MODULE_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_statistic_call_entity_meta() -> dict[str, Any]:
    return {
        'id': random.randint(100000, 999999),
        'name': "".join(random.sample(string.ascii_letters + string.digits, k=8)),
        'message': "".join(random.sample(string.ascii_letters + string.digits, k=16)),
    }


@pytest.fixture(scope='class')
async def test_statistic_call_data() -> dict[str, Any]:
    return {
        'command': "".join(random.sample(string.ascii_letters + string.digits, k=8)),
        'data': {
            'target': "".join(random.sample(string.ascii_letters + string.digits, k=8)),
            'payload': "".join(random.sample(string.ascii_letters + string.digits, k=8)),
        },
        'token': "".join(random.sample(string.ascii_letters + string.digits, k=8)),
    }


@pytest.fixture(scope='class')
async def statistic_dal() -> AsyncGenerator['StatisticDAL', None]:
    from src.database.internal.statistic import StatisticDAL

    async with StatisticDAL.create() as dal:
        yield dal


class TestStatisticDAL:
    """StatisticDAL CRUD 单元测试"""

    async def test_check_clear_table(self, statistic_dal) -> None:
        """清空数据表, 查回验证表行数为空"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        rows_num = await statistic_dal._count_all()

        assert rows_num == 0

    async def test_clear_all_rollback(
            self,
            statistic_dal,
            test_statistic_plugin_name,
            test_statistic_plugin_module,
            test_statistic_call_entity_meta,
            test_statistic_call_data,
    ) -> None:
        """_clear_all 不执行 commit, 外层事务 rollback 后数据应恢复"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        now_timestamp = int(datetime.now().timestamp())
        await statistic_dal.add(
            plugin_name=test_statistic_plugin_name,
            module_name=test_statistic_plugin_module,
            call_timestamp=now_timestamp,
            call_entity_meta=test_statistic_call_entity_meta,
            call_data=test_statistic_call_data,
        )
        await statistic_dal.commit_session()

        await statistic_dal._clear_all()
        assert await statistic_dal._count_all() == 0

        await statistic_dal.db_session.rollback()
        assert await statistic_dal._count_all() == 1

    # ------------------------------------------------------------------ #
    # add
    # ------------------------------------------------------------------ #

    async def test_add_basic(
            self,
            statistic_dal,
            test_statistic_plugin_name,
            test_statistic_plugin_module,
            test_statistic_call_entity_meta,
            test_statistic_call_data,
    ) -> None:
        """插入一条记录, 验证返回值所有字段正确 (含 JSON 字段往返)"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        now_timestamp = int(datetime.now().timestamp())
        result = await statistic_dal.add(
            plugin_name=test_statistic_plugin_name,
            module_name=test_statistic_plugin_module,
            call_timestamp=now_timestamp,
            call_entity_meta=test_statistic_call_entity_meta,
            call_data=test_statistic_call_data,
        )
        await statistic_dal.commit_session()

        assert result.plugin_name == test_statistic_plugin_name
        assert result.module_name == test_statistic_plugin_module
        assert result.call_timestamp == now_timestamp
        assert result.call_entity_meta == test_statistic_call_entity_meta
        assert result.call_data == test_statistic_call_data

    async def test_add_json_roundtrip(
            self,
            statistic_dal,
            test_statistic_plugin_name,
            test_statistic_plugin_module,
    ) -> None:
        """插入含嵌套 dict 的 JSON 字段, 查回验证嵌套结构完整"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        nested_entity_meta = {'level1': {'level2': {'level3': 'deep_value'}, 'num': 42}}
        nested_call_data = {'cmd': 'search', 'params': {'q': 'test', 'page': 1, 'filters': ['a', 'b', 'c']}}

        now_timestamp = int(datetime.now().timestamp())
        await statistic_dal.add(
            plugin_name=test_statistic_plugin_name,
            module_name=test_statistic_plugin_module,
            call_timestamp=now_timestamp,
            call_entity_meta=nested_entity_meta,
            call_data=nested_call_data,
        )
        await statistic_dal.commit_session()

        result = await statistic_dal.query_by_condition(plugin_name=test_statistic_plugin_name)
        assert len(result) == 1
        assert result[0].call_entity_meta == nested_entity_meta
        assert result[0].call_data == nested_call_data

    async def test_add_multiple(
            self,
            statistic_dal,
            test_statistic_plugin_name,
            test_statistic_plugin_module,
            test_statistic_call_entity_meta,
            test_statistic_call_data,
    ) -> None:
        """连续插入多条, 验证 id 递增且 _count_all 递增"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = int(datetime.now().timestamp())
        ids = []
        for i in range(5):
            result = await statistic_dal.add(
                plugin_name=test_statistic_plugin_name,
                module_name=test_statistic_plugin_module,
                call_timestamp=base_ts + i,
                call_entity_meta=test_statistic_call_entity_meta,
                call_data=test_statistic_call_data,
            )
            ids.append(result.id)
            assert await statistic_dal._count_all() == i + 1

        # id 递增
        assert ids == sorted(ids)
        assert len(set(ids)) == 5

    async def test_add_empty_dicts(
            self,
            statistic_dal,
            test_statistic_plugin_name,
            test_statistic_plugin_module,
    ) -> None:
        """call_entity_meta={} 和 call_data={} 插入验证不报错且查回为空 dict"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        now_timestamp = int(datetime.now().timestamp())
        result = await statistic_dal.add(
            plugin_name=test_statistic_plugin_name,
            module_name=test_statistic_plugin_module,
            call_timestamp=now_timestamp,
            call_entity_meta={},
            call_data={},
        )
        await statistic_dal.commit_session()

        assert result.call_entity_meta == {}
        assert result.call_data == {}

    # ------------------------------------------------------------------ #
    # query_by_condition
    # ------------------------------------------------------------------ #

    async def test_query_no_filter(self, statistic_dal) -> None:
        """不带任何条件查询全部, 验证按 call_timestamp DESC 排序"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts + 10,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_b', call_timestamp=base_ts + 30,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_c', module_name='mod_c', call_timestamp=base_ts + 20,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        result = await statistic_dal.query_by_condition()
        assert len(result) == 3
        timestamps = [item.call_timestamp for item in result]
        assert timestamps == [base_ts + 30, base_ts + 20, base_ts + 10]

    async def test_query_by_plugin_name(self, statistic_dal) -> None:
        """仅按 plugin_name 过滤"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts + 1,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_b', call_timestamp=base_ts + 2,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_c', call_timestamp=base_ts + 3,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        result = await statistic_dal.query_by_condition(plugin_name='plugin_a')
        assert len(result) == 2
        assert all(item.plugin_name == 'plugin_a' for item in result)

    async def test_query_by_module_name(self, statistic_dal) -> None:
        """仅按 module_name 过滤"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_x', call_timestamp=base_ts + 1,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_y', call_timestamp=base_ts + 2,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_c', module_name='mod_x', call_timestamp=base_ts + 3,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        result = await statistic_dal.query_by_condition(module_name='mod_x')
        assert len(result) == 2
        assert all(item.module_name == 'mod_x' for item in result)

    async def test_query_by_plugin_and_module(self, statistic_dal) -> None:
        """同时按 plugin_name + module_name 过滤"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_shared', call_timestamp=base_ts + 1,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_other', call_timestamp=base_ts + 2,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_shared', call_timestamp=base_ts + 3,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        result = await statistic_dal.query_by_condition(plugin_name='plugin_a', module_name='mod_shared')
        assert len(result) == 1
        assert result[0].plugin_name == 'plugin_a'
        assert result[0].module_name == 'mod_shared'

    async def test_query_by_start_timestamp_int(self, statistic_dal) -> None:
        """start_timestamp 为 int, 只返回 >= start_timestamp 的记录"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_b', call_timestamp=base_ts + 100,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_c', module_name='mod_c', call_timestamp=base_ts + 200,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        result = await statistic_dal.query_by_condition(start_timestamp=base_ts + 100)
        assert len(result) == 2
        timestamps = {item.call_timestamp for item in result}
        assert timestamps == {base_ts + 100, base_ts + 200}

    async def test_query_by_start_timestamp_datetime(self, statistic_dal) -> None:
        """start_timestamp 为 datetime, 验证过滤生效 (内部转 timestamp)"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_dt = datetime(2025, 1, 1, 0, 0, 0)
        base_ts = int(base_dt.timestamp())
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts - 100,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_b', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_c', module_name='mod_c', call_timestamp=base_ts + 100,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        result = await statistic_dal.query_by_condition(start_timestamp=base_dt)
        assert len(result) == 2
        timestamps = {item.call_timestamp for item in result}
        assert timestamps == {base_ts, base_ts + 100}

    async def test_query_ordering_desc(self, statistic_dal) -> None:
        """插入不同 timestamp 记录, 验证结果按 DESC 排序"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        timestamps = [1000000000, 1000000005, 1000000003, 1000000001, 1000000004]
        for ts in timestamps:
            await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=ts, call_entity_meta={},
                                    call_data={})
        await statistic_dal.commit_session()

        result = await statistic_dal.query_by_condition()
        result_timestamps = [item.call_timestamp for item in result]
        assert result_timestamps == sorted(timestamps, reverse=True)

    async def test_query_empty_result(self, statistic_dal) -> None:
        """条件不匹配时返回空列表"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=1000000000,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        result = await statistic_dal.query_by_condition(plugin_name='nonexistent_plugin')
        assert result == []

    # ------------------------------------------------------------------ #
    # count_by_condition
    # ------------------------------------------------------------------ #

    async def test_count_no_filter(self, statistic_dal) -> None:
        """不带条件返回全表行数"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_b', call_timestamp=base_ts + 1,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal.count_by_condition() == 2

    async def test_count_by_plugin_name(self, statistic_dal) -> None:
        """按 plugin_name 过滤的计数"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_b', call_timestamp=base_ts + 1,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_c', call_timestamp=base_ts + 2,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal.count_by_condition(plugin_name='plugin_a') == 2
        assert await statistic_dal.count_by_condition(plugin_name='plugin_b') == 1

    async def test_count_by_plugin_and_module(self, statistic_dal) -> None:
        """双条件计数"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_shared', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_other', call_timestamp=base_ts + 1,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_shared', call_timestamp=base_ts + 2,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal.count_by_condition(plugin_name='plugin_a', module_name='mod_shared') == 1
        assert await statistic_dal.count_by_condition(plugin_name='plugin_a', module_name='mod_other') == 1
        assert await statistic_dal.count_by_condition(plugin_name='plugin_b', module_name='mod_shared') == 1

    async def test_count_by_start_timestamp(self, statistic_dal) -> None:
        """按 start_timestamp 过滤的计数"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_b', call_timestamp=base_ts + 100,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_c', module_name='mod_c', call_timestamp=base_ts + 200,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal.count_by_condition(start_timestamp=base_ts + 100) == 2
        assert await statistic_dal.count_by_condition(start_timestamp=base_ts + 201) == 0

    async def test_count_zero(self, statistic_dal) -> None:
        """条件不匹配时返回 0"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=1000000000,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal.count_by_condition(plugin_name='nonexistent') == 0

    # ------------------------------------------------------------------ #
    # delete_period_older
    # ------------------------------------------------------------------ #

    async def test_delete_period_older_basic(self, statistic_dal) -> None:
        """删除 call_timestamp <= before_timestamp 的记录, 验证剩余记录"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_b', call_timestamp=base_ts + 100,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_c', module_name='mod_c', call_timestamp=base_ts + 200,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal._count_all() == 3

        await statistic_dal.delete_period_older(base_ts + 100)
        await statistic_dal.commit_session()

        remaining = await statistic_dal.query_by_condition()
        assert len(remaining) == 1
        assert remaining[0].call_timestamp == base_ts + 200

    async def test_delete_period_older_with_plugin_name(self, statistic_dal) -> None:
        """指定 plugin_name 时只删除该 plugin 的过期记录, 其他 plugin 的同 timestamp 记录保留"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_b', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_c', call_timestamp=base_ts + 200,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal._count_all() == 3

        await statistic_dal.delete_period_older(base_ts, plugin_name='plugin_a')
        await statistic_dal.commit_session()

        remaining = await statistic_dal.query_by_condition()
        assert len(remaining) == 2
        remaining_plugins = {item.plugin_name for item in remaining}
        assert remaining_plugins == {'plugin_b', 'plugin_a'}
        remaining_a = [item for item in remaining if item.plugin_name == 'plugin_a']
        assert len(remaining_a) == 1
        assert remaining_a[0].call_timestamp == base_ts + 200

    async def test_delete_period_older_with_module_name(self, statistic_dal) -> None:
        """指定 module_name 时只删除该 module 的过期记录"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_target', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_other', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_c', module_name='mod_target', call_timestamp=base_ts + 200,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal._count_all() == 3

        await statistic_dal.delete_period_older(base_ts, module_name='mod_target')
        await statistic_dal.commit_session()

        remaining = await statistic_dal.query_by_condition()
        assert len(remaining) == 2
        remaining_modules = {item.module_name for item in remaining}
        assert remaining_modules == {'mod_other', 'mod_target'}

    async def test_delete_period_older_no_match(self, statistic_dal) -> None:
        """before_timestamp 小于所有记录, 不删除任何数据"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_b', call_timestamp=base_ts + 100,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal._count_all() == 2

        await statistic_dal.delete_period_older(base_ts - 1)
        await statistic_dal.commit_session()

        assert await statistic_dal._count_all() == 2

    async def test_delete_period_older_all(self, statistic_dal) -> None:
        """before_timestamp 大于所有记录, 全部删除"""
        await statistic_dal._clear_all()
        await statistic_dal.commit_session()

        base_ts = 1000000000
        await statistic_dal.add(plugin_name='plugin_a', module_name='mod_a', call_timestamp=base_ts,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_b', module_name='mod_b', call_timestamp=base_ts + 100,
                                call_entity_meta={}, call_data={})
        await statistic_dal.add(plugin_name='plugin_c', module_name='mod_c', call_timestamp=base_ts + 200,
                                call_entity_meta={}, call_data={})
        await statistic_dal.commit_session()

        assert await statistic_dal._count_all() == 3

        await statistic_dal.delete_period_older(base_ts + 200)
        await statistic_dal.commit_session()

        assert await statistic_dal._count_all() == 0
