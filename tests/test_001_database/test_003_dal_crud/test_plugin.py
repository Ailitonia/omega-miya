"""
@Author         : Ailitonia
@Date           : 2026/8/29 23:00
@FileName       : test_plugin
@Project        : omega-miya
@Description    : plugin.py 数据库 CRUD 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound

if TYPE_CHECKING:
    from src.database.internal.plugin import PluginDAL


@pytest.fixture(scope='class')
async def test_plugin_name() -> str:
    return f'PLUGIN_NAME_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def test_plugin_module() -> str:
    return f'PLUGIN_MODULE_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def plugin_dal() -> AsyncGenerator['PluginDAL', None]:
    from src.database.internal.plugin import PluginDAL

    async with PluginDAL.create() as dal:
        yield dal


class TestPluginDAL:
    """PluginDAL CRUD 单元测试"""

    async def test_check_clear_table(self, plugin_dal) -> None:
        """清空数据表, 查回验证表行数为空"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        rows_num = await plugin_dal._count_all()

        assert rows_num == 0

    async def test_clear_all_rollback(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """_clear_all 不执行 commit, 外层事务 rollback 后数据应恢复"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
        )
        await plugin_dal.commit_session()

        await plugin_dal._clear_all()
        assert await plugin_dal._count_all() == 0

        await plugin_dal.rollback_session()
        assert await plugin_dal._count_all() == 1

    # ------------------------------------------------------------------ #
    # add
    # ------------------------------------------------------------------ #

    async def test_add_basic(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """插入一条记录 (enabled=1, info=None), 查回验证字段正确"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        result = await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
        )
        await plugin_dal.commit_session()

        assert result.plugin_name == test_plugin_name
        assert result.module_name == test_plugin_module
        assert result.enabled == 1
        assert result.info is None

        queried = await plugin_dal.query_unique(test_plugin_name, test_plugin_module)
        assert queried.plugin_name == test_plugin_name
        assert queried.module_name == test_plugin_module
        assert queried.enabled == 1
        assert queried.info is None

    async def test_add_with_info(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """带 info 插入, 验证 info 值正确"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        result = await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
            info='plugin info text',
        )
        await plugin_dal.commit_session()

        assert result.info == 'plugin info text'

        queried = await plugin_dal.query_unique(test_plugin_name, test_plugin_module)
        assert queried.info == 'plugin info text'

    async def test_add_enabled_values(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """分别用 enabled=0 和 enabled=-1 插入, 验证 enabled 字段正确"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        r0 = await plugin_dal.add(
            plugin_name=f'{test_plugin_name}_disabled',
            module_name=f'{test_plugin_module}_disabled',
            enabled=0,
        )
        await plugin_dal.commit_session()
        assert r0.enabled == 0

        r1 = await plugin_dal.add(
            plugin_name=f'{test_plugin_name}_invalid',
            module_name=f'{test_plugin_module}_invalid',
            enabled=-1,
        )
        await plugin_dal.commit_session()
        assert r1.enabled == -1

    async def test_add_duplicate_raises(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """对同一 (plugin_name, module_name) 插入两次, 预期 IntegrityError"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=-1,
        )
        await plugin_dal.commit_session()

        with pytest.raises(IntegrityError):
            await plugin_dal.add(
                plugin_name=test_plugin_name,
                module_name=test_plugin_module,
                enabled=0,
            )
            await plugin_dal.commit_session()

        # 回滚到正常状态
        await plugin_dal.rollback_session()

        queried = await plugin_dal.query_unique(test_plugin_name, test_plugin_module)
        assert queried.enabled == -1

    # ------------------------------------------------------------------ #
    # query_unique
    # ------------------------------------------------------------------ #

    async def test_query_unique_not_found(self, plugin_dal) -> None:
        """查询不存在的记录, 预期 NoResultFound"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        with pytest.raises(NoResultFound):
            await plugin_dal.query_unique('nonexistent_plugin', 'nonexistent_module')

    async def test_query_unique_normal(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """插入后查询, 验证返回值字段正确"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
            info='query test info',
        )
        await plugin_dal.commit_session()

        queried = await plugin_dal.query_unique(test_plugin_name, test_plugin_module)
        assert queried.plugin_name == test_plugin_name
        assert queried.module_name == test_plugin_module
        assert queried.enabled == 1
        assert queried.info == 'query test info'

    # ------------------------------------------------------------------ #
    # query_by_enable_status
    # ------------------------------------------------------------------ #

    async def test_query_by_enable_status_filtered(self, plugin_dal) -> None:
        """插入多条不同 enabled 状态的记录, 查询 enabled=1 只返回启用项"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(plugin_name='plugin_a', module_name='mod_a', enabled=1)
        await plugin_dal.add(plugin_name='plugin_b', module_name='mod_b', enabled=0)
        await plugin_dal.add(plugin_name='plugin_c', module_name='mod_c', enabled=1)
        await plugin_dal.add(plugin_name='plugin_d', module_name='mod_d', enabled=-1)
        await plugin_dal.commit_session()

        enabled = await plugin_dal.query_by_enable_status(enabled=1)
        assert len(enabled) == 2
        assert {item.plugin_name for item in enabled} == {'plugin_a', 'plugin_c'}
        for item in enabled:
            assert item.enabled == 1

    async def test_query_by_enable_status_default(self, plugin_dal) -> None:
        """默认参数 enabled=1 只返回启用项"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(plugin_name='plugin_a', module_name='mod_a', enabled=1)
        await plugin_dal.add(plugin_name='plugin_b', module_name='mod_b', enabled=0)
        await plugin_dal.commit_session()

        result = await plugin_dal.query_by_enable_status()
        assert len(result) == 1
        assert result[0].plugin_name == 'plugin_a'
        assert result[0].enabled == 1

    async def test_query_by_enable_status_disabled(self, plugin_dal) -> None:
        """查询 enabled=0 只返回禁用项"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(plugin_name='plugin_a', module_name='mod_a', enabled=1)
        await plugin_dal.add(plugin_name='plugin_b', module_name='mod_b', enabled=0)
        await plugin_dal.add(plugin_name='plugin_c', module_name='mod_c', enabled=-1)
        await plugin_dal.commit_session()

        disabled = await plugin_dal.query_by_enable_status(enabled=0)
        assert len(disabled) == 1
        assert disabled[0].plugin_name == 'plugin_b'
        assert disabled[0].enabled == 0

    async def test_query_by_enable_status_ordering(self, plugin_dal) -> None:
        """结果按 plugin_name 排序"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        # 故意按非字典序插入
        await plugin_dal.add(plugin_name='plugin_charlie', module_name='mod_c', enabled=1)
        await plugin_dal.add(plugin_name='plugin_alpha', module_name='mod_a', enabled=1)
        await plugin_dal.add(plugin_name='plugin_bravo', module_name='mod_b', enabled=1)
        await plugin_dal.commit_session()

        result = await plugin_dal.query_by_enable_status(enabled=1)
        result_names = [item.plugin_name for item in result]
        assert result_names == ['plugin_alpha', 'plugin_bravo', 'plugin_charlie']

    async def test_query_by_enable_status_empty(self, plugin_dal) -> None:
        """没有匹配状态时返回空列表"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(plugin_name='plugin_a', module_name='mod_a', enabled=1)
        await plugin_dal.commit_session()

        result = await plugin_dal.query_by_enable_status(enabled=0)
        assert result == []

    # ------------------------------------------------------------------ #
    # query_all
    # ------------------------------------------------------------------ #

    async def test_query_all_multiple(self, plugin_dal) -> None:
        """插入多条记录, 验证返回全部且按 plugin_name 排序"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        # 故意按非字典序插入
        await plugin_dal.add(plugin_name='plugin_charlie', module_name='mod_c', enabled=1)
        await plugin_dal.add(plugin_name='plugin_alpha', module_name='mod_a', enabled=0)
        await plugin_dal.add(plugin_name='plugin_bravo', module_name='mod_b', enabled=-1)
        await plugin_dal.commit_session()

        result = await plugin_dal.query_all()
        assert len(result) == 3
        result_names = [item.plugin_name for item in result]
        assert result_names == ['plugin_alpha', 'plugin_bravo', 'plugin_charlie']

    async def test_query_all_empty(self, plugin_dal) -> None:
        """空表时返回空列表"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        result = await plugin_dal.query_all()
        assert result == []

    # ------------------------------------------------------------------ #
    # add_update_exist
    # ------------------------------------------------------------------ #

    async def test_add_update_exist_insert(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """首次调用 add_update_exist, 验证为插入行为"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        result = await plugin_dal.add_update_exist(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
            info='insert info',
        )
        await plugin_dal.commit_session()

        assert result.plugin_name == test_plugin_name
        assert result.module_name == test_plugin_module
        assert result.enabled == 1
        assert result.info == 'insert info'

        queried = await plugin_dal.query_unique(test_plugin_name, test_plugin_module)
        assert queried.enabled == 1
        assert queried.info == 'insert info'

    async def test_add_update_exist_update(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """先 add 插入, 再 add_update_exist 更新 enabled 和 info, 验证返回新值"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
            info='original info',
        )
        await plugin_dal.commit_session()

        result = await plugin_dal.add_update_exist(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=0,
            info='updated info',
        )
        await plugin_dal.commit_session()

        assert result.enabled == 0
        assert result.info == 'updated info'

        queried = await plugin_dal.query_unique(test_plugin_name, test_plugin_module)
        assert queried.enabled == 0
        assert queried.info == 'updated info'

    async def test_add_update_exist_update_with_none_info(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """先 add 带 info, 再 add_update_exist 用 info=None 更新, 验证 info 被更新为 None"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
            info='original info',
        )
        await plugin_dal.commit_session()

        result = await plugin_dal.add_update_exist(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
            info=None,
        )
        await plugin_dal.commit_session()

        assert result.info is None

        queried = await plugin_dal.query_unique(test_plugin_name, test_plugin_module)
        assert queried.info is None

    # ------------------------------------------------------------------ #
    # delete
    # ------------------------------------------------------------------ #

    async def test_delete_existing(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """插入一条, delete 后用 query_unique 查不到 (抛 NoResultFound)"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
        )
        await plugin_dal.commit_session()

        await plugin_dal.delete(test_plugin_name, test_plugin_module)
        await plugin_dal.commit_session()

        with pytest.raises(NoResultFound):
            await plugin_dal.query_unique(test_plugin_name, test_plugin_module)

    async def test_delete_non_existing(self, plugin_dal) -> None:
        """删除不存在的记录, 不抛异常"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.delete('nonexistent_plugin', 'nonexistent_module')
        await plugin_dal.commit_session()

        assert await plugin_dal._count_all() == 0

    async def test_delete_only_affects_target(
            self,
            plugin_dal,
            test_plugin_name,
            test_plugin_module,
    ) -> None:
        """插入多条, delete 只删除目标记录, 其他不受影响"""
        await plugin_dal._clear_all()
        await plugin_dal.commit_session()

        await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=test_plugin_module,
            enabled=1,
        )
        await plugin_dal.add(
            plugin_name=test_plugin_name,
            module_name=f'{test_plugin_module}_other',
            enabled=1,
        )
        await plugin_dal.commit_session()

        await plugin_dal.delete(test_plugin_name, test_plugin_module)
        await plugin_dal.commit_session()

        # 目标记录已删除
        with pytest.raises(NoResultFound):
            await plugin_dal.query_unique(test_plugin_name, test_plugin_module)

        # 其他记录仍在
        remaining = await plugin_dal.query_all()
        assert len(remaining) == 1
        assert remaining[0].plugin_name == test_plugin_name
        assert remaining[0].module_name == f'{test_plugin_module}_other'

        assert await plugin_dal._count_all() == 1
