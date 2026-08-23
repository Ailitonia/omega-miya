"""
@Author         : Ailitonia
@Date           : 2026/8/23 15:40
@FileName       : test_migration_check.py
@Project        : omega-miya
@Description    : src/database/migrate.py 迁移状态检查功能单元测试

注意:
- 所有 src.* 的导入一律放在测试函数体内, 原因见 tests/database/conftest.py
- TestInspectDatabase / TestCheckMigrationState 中的用例直接操作 .env.test 配置的测试数据库 (敏感操作),
  alembic_version 表及测试哨兵表的修改在测试结束后由 test_database_helper fixture 自动恢复
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import pytest


class TestMigrationCheckResult:
    """MigrationCheckResult.is_safe 属性测试"""

    @pytest.mark.parametrize(
        ('status_value', 'expected'),
        [
            ('fresh', True),
            ('upgradable', True),
            ('up_to_date', True),
            ('unstamped_database', False),
            ('unknown_revision', False),
            ('multiple_current_revisions', False),
            ('multiple_heads', False),
        ],
    )
    def test_is_safe(self, status_value: str, expected: bool) -> None:
        from src.database.migrate import MigrationCheckResult, MigrationStatus

        result = MigrationCheckResult(status=MigrationStatus(status_value), current_revisions=(), head='head_rev')

        assert result.is_safe is expected


class TestGetScriptRevisions:
    """迁移脚本版本信息读取测试 (使用项目真实迁移脚本)"""

    def test_single_head(self) -> None:
        """迁移脚本应保持单一 head 的线性历史"""
        from src.database.migrate import _get_script_revisions

        status = _get_script_revisions()

        assert len(status.heads) == 1

    def test_heads_in_known_revisions(self) -> None:
        """heads 必须是已知版本的子集"""
        from src.database.migrate import _get_script_revisions

        status = _get_script_revisions()

        assert set(status.heads).issubset(status.known_revisions)


class TestInspectDatabase:
    """数据库版本记录及业务数据表检查测试

    敏感操作: 以下用例直接修改 .env.test 配置的测试数据库, 测试结束后自动恢复
    """

    @staticmethod
    async def _run_inspect():
        from src.database.connector import engine
        from src.database.migrate import _inspect_database

        async with engine.connect() as connection:
            return await connection.run_sync(_inspect_database)

    async def test_no_version_table(self, test_database_helper) -> None:
        await test_database_helper.rebuild_versions(None)
        expected_business_tables = await test_database_helper.has_business_tables()

        status = await self._run_inspect()

        assert status.current_revisions == []
        assert status.has_business_tables is expected_business_tables

    async def test_single_version_record(self, test_database_helper) -> None:
        await test_database_helper.rebuild_versions(['rev_1'])

        status = await self._run_inspect()

        assert status.current_revisions == ['rev_1']

    async def test_multiple_version_records(self, test_database_helper) -> None:
        await test_database_helper.rebuild_versions(['rev_1', 'rev_2'])

        status = await self._run_inspect()

        assert sorted(status.current_revisions) == ['rev_1', 'rev_2']

    async def test_business_table_detection(self, test_database_helper) -> None:
        await test_database_helper.rebuild_versions(None)
        await test_database_helper.create_sentinel()

        status = await self._run_inspect()

        assert status.current_revisions == []
        assert status.has_business_tables is True


class TestCheckMigrationState:
    """数据库迁移状态检查分类逻辑测试

    敏感操作: 以下用例直接修改 .env.test 配置的测试数据库, 测试结束后自动恢复
    """

    async def test_multiple_heads(
            self,
            patch_script_revisions,
    ) -> None:
        patch_script_revisions(heads=['head_a', 'head_b'])

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.MULTIPLE_HEADS
        assert result.head is None
        assert not result.is_safe
        assert result.message.startswith('迁移脚本存在多个')

    async def test_fresh_database(
            self,
            test_database_helper,
            patch_script_revisions,
    ) -> None:
        patch_script_revisions(heads=['head_rev'])
        await test_database_helper.rebuild_versions(None)
        if await test_database_helper.has_business_tables():
            pytest.skip('测试数据库已存在业务数据表, 无法构造空库场景')

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.FRESH
        assert result.head == 'head_rev'
        assert result.is_safe
        assert not result.message

    async def test_fresh_database_with_empty_version_table(
            self,
            test_database_helper,
            patch_script_revisions,
    ) -> None:
        patch_script_revisions(heads=['head_rev'])
        await test_database_helper.rebuild_versions([])
        if await test_database_helper.has_business_tables():
            pytest.skip('测试数据库已存在业务数据表, 无法构造空库场景')

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.FRESH
        assert result.head == 'head_rev'
        assert result.is_safe
        assert not result.message

    async def test_unstamped_database(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'])
        await test_database_helper.rebuild_versions(None)
        await test_database_helper.create_sentinel()

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.UNSTAMPED_DATABASE
        assert not result.is_safe
        assert '--database-stamp' in result.message

    async def test_multiple_current_revisions(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'])
        await test_database_helper.rebuild_versions(['rev_1', 'rev_2'])

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.MULTIPLE_CURRENT_REVISIONS
        assert not result.is_safe
        assert 'rev_1' in result.message
        assert 'rev_2' in result.message

    async def test_up_to_date(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'], known_revisions={'head_rev', 'base_rev'})
        await test_database_helper.rebuild_versions(['head_rev'])

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.UP_TO_DATE
        assert result.current_revisions == ('head_rev',)
        assert result.is_safe

    async def test_unknown_revision(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'], known_revisions={'head_rev', 'base_rev'})
        await test_database_helper.rebuild_versions(['ghost_rev'])

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.UNKNOWN_REVISION
        assert not result.is_safe
        assert 'ghost_rev' in result.message
        assert '--database-stamp' in result.message

    async def test_upgradable(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'], known_revisions={'head_rev', 'base_rev'})
        await test_database_helper.rebuild_versions(['base_rev'])

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.UPGRADABLE
        assert result.is_safe
        assert 'base_rev' in result.message
        assert 'head_rev' in result.message
