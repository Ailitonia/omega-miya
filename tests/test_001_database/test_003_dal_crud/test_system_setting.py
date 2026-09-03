"""
@Author         : Ailitonia
@Date           : 2026/8/29 22:10
@FileName       : test_system_setting
@Project        : omega-miya
@Description    : system_setting.py 数据库 CRUD 单元测试
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
    from src.database.internal.system_setting import SystemSettingDAL


@pytest.fixture(scope='class')
async def test_system_setting_name() -> str:
    return f'SETTING_NAME_{random.randint(0, 1000)}'


@pytest.fixture(scope='class')
async def test_system_setting_key() -> str:
    return f'SETTING_KEY_{random.randint(0, 1000)}'


@pytest.fixture(scope='class')
async def test_system_setting_value() -> str:
    return f'SETTING_VALUE_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'


@pytest.fixture(scope='class')
async def system_setting_dal() -> AsyncGenerator['SystemSettingDAL', None]:
    from src.database.internal.system_setting import SystemSettingDAL

    async with SystemSettingDAL.create() as dal:
        yield dal


class TestSystemSettingDAL:
    """SystemSettingDAL CRUD 单元测试"""

    async def test_check_clear_table(self, system_setting_dal) -> None:
        """清空数据表, 查回验证表行数为空"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        rows_num = await system_setting_dal._count_all()

        assert rows_num == 0

    async def test_clear_all_rollback(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """_clear_all 不执行 commit, 外层事务 rollback 后数据应恢复"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
        )
        await system_setting_dal.commit_session()

        await system_setting_dal._clear_all()
        assert await system_setting_dal._count_all() == 0

        await system_setting_dal.rollback_session()
        assert await system_setting_dal._count_all() == 1

    # ------------------------------------------------------------------ #
    # add
    # ------------------------------------------------------------------ #

    async def test_add_basic(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """插入一条带 info 的记录, 查回验证所有字段正确"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        result = await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
            info='some info',
        )
        await system_setting_dal.commit_session()

        assert result.setting_name == test_system_setting_name
        assert result.setting_key == test_system_setting_key
        assert result.setting_value == test_system_setting_value
        assert result.info == 'some info'

        queried = await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)
        assert queried.setting_value == test_system_setting_value
        assert queried.info == 'some info'

    async def test_add_without_info(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """info=None 插入, 验证 info 为 None"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        result = await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
        )
        await system_setting_dal.commit_session()

        assert result.info is None

        queried = await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)
        assert queried.info is None

    async def test_add_duplicate_raises(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """对同一 (setting_name, setting_key) 插入两次, 预期 IntegrityError"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
        )
        await system_setting_dal.commit_session()

        with pytest.raises(IntegrityError):
            await system_setting_dal.add(
                setting_name=test_system_setting_name,
                setting_key=test_system_setting_key,
                setting_value='another_value',
            )

        # 回滚到正常状态
        await system_setting_dal.rollback_session()

        queried = await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)
        assert queried.setting_value == test_system_setting_value

    # ------------------------------------------------------------------ #
    # query_unique
    # ------------------------------------------------------------------ #

    async def test_query_unique_not_found(self, system_setting_dal) -> None:
        """查询不存在的 key, 预期 NoResultFound"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        with pytest.raises(NoResultFound):
            await system_setting_dal.query_unique('nonexistent_name', 'nonexistent_key')

    async def test_query_unique_normal(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """插入后查询, 验证返回值字段正确"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
            info='query test info',
        )
        await system_setting_dal.commit_session()

        queried = await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)
        assert queried.setting_name == test_system_setting_name
        assert queried.setting_key == test_system_setting_key
        assert queried.setting_value == test_system_setting_value
        assert queried.info == 'query test info'

    # ------------------------------------------------------------------ #
    # query_series
    # ------------------------------------------------------------------ #

    async def test_query_series_multiple(self, system_setting_dal, test_system_setting_name) -> None:
        """同一 setting_name 插入多条不同 setting_key, 查回列表长度正确"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        keys = ['series_key_1', 'series_key_2', 'series_key_3']
        for key in keys:
            await system_setting_dal.add(
                setting_name=test_system_setting_name,
                setting_key=key,
                setting_value=f'value_{key}',
            )
        await system_setting_dal.commit_session()

        result = await system_setting_dal.query_series(test_system_setting_name)
        assert len(result) == len(keys)
        result_keys = {item.setting_key for item in result}
        assert result_keys == set(keys)

    async def test_query_series_empty(self, system_setting_dal) -> None:
        """查询不存在的 setting_name, 返回空列表"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        result = await system_setting_dal.query_series('nonexistent_setting_name')
        assert result == []

    async def test_query_series_isolated(self, system_setting_dal) -> None:
        """多个 setting_name 下有数据, query_series 只返回指定 name 的记录"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        await system_setting_dal.add(
            setting_name='name_alpha', setting_key='key_1', setting_value='v1',
        )
        await system_setting_dal.add(
            setting_name='name_alpha', setting_key='key_2', setting_value='v2',
        )
        await system_setting_dal.add(
            setting_name='name_beta', setting_key='key_3', setting_value='v3',
        )
        await system_setting_dal.commit_session()

        alpha = await system_setting_dal.query_series('name_alpha')
        assert len(alpha) == 2
        assert {item.setting_key for item in alpha} == {'key_1', 'key_2'}

        beta = await system_setting_dal.query_series('name_beta')
        assert len(beta) == 1
        assert beta[0].setting_key == 'key_3'

    # ------------------------------------------------------------------ #
    # query_all
    # ------------------------------------------------------------------ #

    async def test_query_all_multiple(self, system_setting_dal) -> None:
        """插入多条跨多个 setting_name 的记录, 验证返回全部且按 setting_name 排序"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        # 故意按非字典序插入, 验证返回按 setting_name 升序
        await system_setting_dal.add(
            setting_name='name_charlie', setting_key='key_c1', setting_value='v_c1',
        )
        await system_setting_dal.add(
            setting_name='name_alpha', setting_key='key_a1', setting_value='v_a1',
        )
        await system_setting_dal.add(
            setting_name='name_bravo', setting_key='key_b1', setting_value='v_b1',
        )
        await system_setting_dal.commit_session()

        result = await system_setting_dal.query_all()
        assert len(result) == 3
        result_names = [item.setting_name for item in result]
        assert result_names == ['name_alpha', 'name_bravo', 'name_charlie']

    async def test_query_all_empty(self, system_setting_dal) -> None:
        """空表时返回空列表"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        result = await system_setting_dal.query_all()
        assert result == []

    # ------------------------------------------------------------------ #
    # add_update_exist
    # ------------------------------------------------------------------ #

    async def test_add_update_exist_insert(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """首次调用 add_update_exist, 验证为插入行为"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        result = await system_setting_dal.add_update_exist(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
            info='insert info',
        )
        await system_setting_dal.commit_session()

        assert result.setting_name == test_system_setting_name
        assert result.setting_key == test_system_setting_key
        assert result.setting_value == test_system_setting_value
        assert result.info == 'insert info'

        queried = await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)
        assert queried.setting_value == test_system_setting_value
        assert queried.info == 'insert info'

    async def test_add_update_exist_update(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """先 add 插入, 再 add_update_exist 更新 value 和 info, 验证返回新值"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
            info='original info',
        )
        await system_setting_dal.commit_session()

        new_value = f'{test_system_setting_value}_updated'
        result = await system_setting_dal.add_update_exist(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=new_value,
            info='updated info',
        )
        await system_setting_dal.commit_session()

        assert result.setting_value == new_value
        assert result.info == 'updated info'

        queried = await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)
        assert queried.setting_value == new_value
        assert queried.info == 'updated info'

    async def test_add_update_exist_update_with_none_info(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """先 add 带 info, 再 add_update_exist 用 info=None 更新, 验证 info 被更新为 None"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
            info='original info',
        )
        await system_setting_dal.commit_session()

        new_value = f'{test_system_setting_value}_updated'
        result = await system_setting_dal.add_update_exist(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=new_value,
            info=None,
        )
        await system_setting_dal.commit_session()

        assert result.setting_value == new_value
        assert result.info is None

        queried = await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)
        assert queried.setting_value == new_value
        assert queried.info is None

    # ------------------------------------------------------------------ #
    # delete
    # ------------------------------------------------------------------ #

    async def test_delete_existing(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """插入一条, delete 后用 query_unique 查不到 (抛 NoResultFound)"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
        )
        await system_setting_dal.commit_session()

        queried = await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)
        assert queried.setting_value == test_system_setting_value
        assert queried.info is None

        await system_setting_dal.delete(test_system_setting_name, test_system_setting_key)
        await system_setting_dal.commit_session()

        with pytest.raises(NoResultFound):
            await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)

    async def test_delete_non_existing(self, system_setting_dal) -> None:
        """删除不存在的记录, 不抛异常"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        # 不应抛出异常
        await system_setting_dal.delete('nonexistent_name', 'nonexistent_key')
        await system_setting_dal.commit_session()

        assert await system_setting_dal._count_all() == 0

    async def test_delete_only_affects_target(
            self,
            system_setting_dal,
            test_system_setting_name,
            test_system_setting_key,
            test_system_setting_value,
    ) -> None:
        """插入多条, delete 只删除目标记录, 其他不受影响"""
        await system_setting_dal._clear_all()
        await system_setting_dal.commit_session()

        await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key=test_system_setting_key,
            setting_value=test_system_setting_value,
        )
        await system_setting_dal.add(
            setting_name=test_system_setting_name,
            setting_key='other_key',
            setting_value='other_value',
        )
        await system_setting_dal.commit_session()

        await system_setting_dal.delete(test_system_setting_name, test_system_setting_key)
        await system_setting_dal.commit_session()

        # 目标记录已删除
        with pytest.raises(NoResultFound):
            await system_setting_dal.query_unique(test_system_setting_name, test_system_setting_key)

        # 其他记录仍在
        remaining = await system_setting_dal.query_series(test_system_setting_name)
        assert len(remaining) == 1
        assert remaining[0].setting_key == 'other_key'
        assert remaining[0].setting_value == 'other_value'

        assert await system_setting_dal._count_all() == 1
