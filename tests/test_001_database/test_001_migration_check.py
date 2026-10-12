"""
@Author         : Ailitonia
@Date           : 2026/8/23 15:40
@FileName       : test_001_migration_check.py
@Project        : omega-miya
@Description    : src/database/migrate.py 迁移状态检查功能单元测试

注意:
- 所有 src.* 的导入一律放在测试函数体内, 原因见 tests/test_001_database/conftest.py
- TestInspectDatabase / TestCheckMigrationState 中的用例直接操作 .env.test 配置的测试数据库
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator, Callable
from typing import ClassVar

import pytest
from nonebot.utils import run_sync
from sqlalchemy import Column, Integer, MetaData, String, Table, inspect, select
from sqlalchemy.engine import Connection


class _TestDatabaseMigrationHelper:
    """测试数据库迁移操作辅助类

    敏感操作警告: 本类方法会直接修改 .env.test 配置的测试数据库, 禁止将测试环境指向生产数据库
    """

    _alembic_version_table: ClassVar[Table] = Table(
        'alembic_version',
        MetaData(),
        Column('version_num', String(32), nullable=False),
    )
    """Alembic 版本表定义 (与 alembic 默认结构一致)"""

    def __init__(self) -> None:
        from src.database.config import database_config
        from src.database.connector import get_engine

        self._engine = get_engine()
        self._db_prefix = database_config.db_prefix

    @property
    def _test_business_table(self) -> Table:
        """测试用业务表 (仅用于测试中构造业务表存在场景)"""
        return Table(
            f'{self._db_prefix}test_already_business_table',
            MetaData(),
            Column('id', Integer, nullable=False),
        )

    @classmethod
    def _drop_all_tables(cls, connection: Connection) -> None:
        # 创建一个空 MetaData 并反射当前数据库中的所有表, 之后按依赖顺序删除
        metadata = MetaData()
        metadata.reflect(bind=connection)
        for table in reversed(metadata.sorted_tables):
            table.drop(connection, checkfirst=True)

    @classmethod
    def _drop_version_table(cls, connection: Connection) -> None:
        cls._alembic_version_table.drop(connection, checkfirst=True)

    @classmethod
    def _create_version_table(cls, connection: Connection, versions: list[str]) -> None:
        cls._alembic_version_table.create(connection, checkfirst=True)
        if versions:
            connection.execute(cls._alembic_version_table.insert(), [{'version_num': v} for v in versions])

    @classmethod
    def _query_all_versions(cls, connection: Connection) -> list[str]:
        table_names = inspect(connection).get_table_names()
        if cls._alembic_version_table.name not in table_names:
            return []
        versions = list(connection.execute(select(cls._alembic_version_table)).scalars().all())
        return versions

    def _drop_test_business_table(self, connection: Connection) -> None:
        self._test_business_table.drop(connection, checkfirst=True)

    def _create_test_business_table(self, connection: Connection) -> None:
        self._test_business_table.create(connection, checkfirst=True)

    async def drop_all_tables(self) -> None:
        """删除数据库所有表

        敏感操作: 直接删除测试数据库中所有表
        """
        async with self._engine.connect() as connection:
            await connection.run_sync(self._drop_all_tables)

    async def rebuild_versions(self, versions: list[str] | None) -> None:
        """重建 alembic_version 表到指定的版本记录

        敏感操作: 直接删除并重建测试数据库的 alembic_version 表

        :param versions: None 表示删除版本表, 空列表表示创建空版本表, 否则重建版本表并插入对应版本记录
        """
        async with self._engine.begin() as connection:
            await connection.run_sync(self._drop_version_table)

        if versions is not None:
            async with self._engine.begin() as connection:
                await connection.run_sync(self._create_version_table, versions)

    async def query_all_versions(self) -> list[str]:
        """查询 alembic_version 表中所有 version 记录"""
        async with self._engine.begin() as connection:
            versions = await connection.run_sync(self._query_all_versions)
        return versions

    async def delete_test_business_table(self) -> None:
        """删除测试用业务表"""
        async with self._engine.begin() as connection:
            await connection.run_sync(self._drop_test_business_table)

    async def create_test_business_table(self) -> None:
        """创建测试用业务表"""
        async with self._engine.begin() as connection:
            await connection.run_sync(self._create_test_business_table)

    def _get_already_tables(self, connection: Connection) -> list[str]:
        return [name for name in inspect(connection).get_table_names() if name.startswith(self._db_prefix)]

    async def count_already_tables(self) -> int:
        """计数测试数据库中已存在的数据表"""
        async with self._engine.connect() as connection:
            return len(await connection.run_sync(self._get_already_tables))

    async def has_already_tables(self) -> bool:
        """检查测试数据库中是否已存在数据表"""
        return (await self.count_already_tables()) > 0

    @staticmethod
    async def upgrade_to(revision: str = 'head') -> None:
        from src.database.migrate import run_upgrade_migrations

        @run_sync
        def _upgrade_to() -> None:
            run_upgrade_migrations(revision=revision)

        await _upgrade_to()

    @staticmethod
    async def downgrade_to(revision: str = 'base') -> None:
        from src.database.migrate import run_downgrade_migrations

        @run_sync
        def _downgrade_to() -> None:
            run_downgrade_migrations(revision=revision)

        await _downgrade_to()


@pytest.fixture(scope='class')
async def test_database_helper() -> AsyncGenerator[_TestDatabaseMigrationHelper, None]:
    """测试数据库操作辅助 fixture

    setup 阶段清空所有数据表, teardown 阶段恢复数据库到 HEAD 版本, 以便后续插件测试使用
    """
    helper = _TestDatabaseMigrationHelper()
    await helper.drop_all_tables()
    try:
        yield helper
    finally:
        await helper.drop_all_tables()
        await helper.upgrade_to('head')


@pytest.fixture
def patch_script_revisions(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """伪造迁移脚本版本信息"""

    def _patch(heads: list[str], known_revisions: set[str] | None = None) -> None:
        """伪造迁移脚本方法

        :param heads: 伪造的 heads 列表
        :param known_revisions: 伪造的已知版本集合, 缺省时取 heads 集合
        """
        import src.database.migrate as migrate_module

        script_revisions_status = migrate_module.ScriptRevisionsStatus(
            heads=heads,
            known_revisions=known_revisions if known_revisions is not None else set(heads),
        )
        monkeypatch.setattr(migrate_module, '_get_script_revisions', lambda: script_revisions_status)

    return _patch


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

    敏感操作: 以下用例直接修改 .env.test 配置的测试数据库
    """

    @staticmethod
    async def _run_inspect():
        from src.database.connector import get_engine
        from src.database.migrate import _inspect_database

        async with get_engine().connect() as connection:
            return await connection.run_sync(_inspect_database)

    async def test_no_version_table(self, test_database_helper) -> None:
        await test_database_helper.rebuild_versions(None)

        status = await self._run_inspect()

        assert status.current_revisions == []

    async def test_single_version_record(self, test_database_helper) -> None:
        await test_database_helper.rebuild_versions(['rev_1'])

        status = await self._run_inspect()

        assert status.current_revisions == ['rev_1']

    async def test_multiple_version_records(self, test_database_helper) -> None:
        await test_database_helper.rebuild_versions(['rev_1', 'rev_2'])

        status = await self._run_inspect()

        assert sorted(status.current_revisions) == ['rev_1', 'rev_2']

    async def test_business_table_detection(self, test_database_helper) -> None:
        await test_database_helper.drop_all_tables()
        await test_database_helper.rebuild_versions(None)
        await test_database_helper.create_test_business_table()

        status = await self._run_inspect()

        assert status.current_revisions == []
        assert status.has_business_tables is True

        await test_database_helper.rebuild_versions(['rev_1'])
        await test_database_helper.delete_test_business_table()

        status = await self._run_inspect()

        assert status.current_revisions == ['rev_1']
        assert status.has_business_tables is False


class TestCheckMigrationState:
    """数据库迁移状态检查分类逻辑测试

    敏感操作: 以下用例直接修改 .env.test 配置的测试数据库
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

    @pytest.mark.parametrize('versions', [None, []], ids=['no_version_table', 'empty_version_table'])
    async def test_fresh_database(
            self,
            versions: list[str] | None,
            test_database_helper,
            patch_script_revisions,
    ) -> None:
        patch_script_revisions(heads=['head_rev'])
        await test_database_helper.drop_all_tables()
        await test_database_helper.rebuild_versions(versions)

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.FRESH
        assert result.head == 'head_rev'
        assert result.is_safe
        assert not result.message

    async def test_unstamped_database(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'])
        await test_database_helper.drop_all_tables()
        await test_database_helper.rebuild_versions(None)
        await test_database_helper.create_test_business_table()

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.UNSTAMPED_DATABASE
        assert not result.is_safe
        assert result.message.startswith('检测到数据库中存在业务数据表')

    async def test_multiple_current_revisions(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'])
        await test_database_helper.drop_all_tables()
        await test_database_helper.rebuild_versions(['rev_1', 'rev_2'])

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.MULTIPLE_CURRENT_REVISIONS
        assert not result.is_safe
        assert 'rev_1' in result.message
        assert 'rev_2' in result.message

    async def test_up_to_date(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'], known_revisions={'head_rev', 'base_rev'})
        await test_database_helper.drop_all_tables()
        await test_database_helper.rebuild_versions(['head_rev'])

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.UP_TO_DATE
        assert result.current_revisions == ('head_rev',)
        assert result.is_safe

    async def test_unknown_revision(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'], known_revisions={'head_rev', 'base_rev'})
        await test_database_helper.drop_all_tables()
        await test_database_helper.rebuild_versions(['ghost_rev'])

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.UNKNOWN_REVISION
        assert not result.is_safe
        assert 'ghost_rev' in result.message

    async def test_upgradable(self, test_database_helper, patch_script_revisions) -> None:
        patch_script_revisions(heads=['head_rev'], known_revisions={'head_rev', 'base_rev'})
        await test_database_helper.drop_all_tables()
        await test_database_helper.rebuild_versions(['base_rev'])

        from src.database.migrate import MigrationStatus, check_migration_state

        result = await check_migration_state()

        assert result.status is MigrationStatus.UPGRADABLE
        assert result.is_safe
        assert 'base_rev' in result.message
        assert 'head_rev' in result.message


class TestCheckMigrationExecute:
    """数据库迁移测试

    敏感操作: 以下用例直接修改 .env.test 配置的测试数据库
    """

    async def test_migration_execute(self, test_database_helper) -> None:
        from src.database.migrate import _get_script_revisions

        status = _get_script_revisions()

        await test_database_helper.drop_all_tables()
        await test_database_helper.upgrade_to('head')

        upgraded_current_versions = await test_database_helper.query_all_versions()
        upgraded_has_already_tables = await test_database_helper.has_already_tables()

        assert len(upgraded_current_versions) == 1
        assert upgraded_current_versions[0] == status.heads[0]
        assert upgraded_has_already_tables is True

        await test_database_helper.downgrade_to('base')

        downgraded_current_versions = await test_database_helper.query_all_versions()
        downgraded_has_already_tables = await test_database_helper.has_already_tables()

        assert len(downgraded_current_versions) == 0
        assert downgraded_has_already_tables is False
