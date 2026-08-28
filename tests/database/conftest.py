"""
@Author         : Ailitonia
@Date           : 2026/8/23 15:40
@FileName       : conftest.py
@Project        : omega-miya
@Description    : database 单元测试 fixtures

注意:
- 测试模块在 pytest 收集阶段导入时 NoneBot 尚未初始化 (nonebug 在 session fixture 中才执行 nonebot.init()),
  此时顶层导入 src.* 会触发 src/database/config.py 的 get_plugin_config 失败并 sys.exit,
  因此所有 src.* 的导入一律放在 fixture/测试函数体内
- 本目录测试直接复用 src.database 的数据库连接, 操作 .env.test 配置的测试数据库
  (创建/删除 alembic_version 表及测试哨兵表), 禁止将测试环境指向生产数据库运行
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator
from typing import ClassVar

import pytest
from nonebot.utils import run_sync
from sqlalchemy import Column, MetaData, String, Table, inspect, select
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
        self._version_table_existed: bool = False
        self._original_versions: list[str] = []

    @classmethod
    def _check_need_snapshot_version_table(cls, connection: Connection) -> tuple[bool, list[str]]:
        """检查是否需要备份 alembic_version 表当前状态

        :return: tuple[version_table_existed, original_versions]
        """
        table_names = inspect(connection).get_table_names()
        if cls._alembic_version_table.name not in table_names:
            return False, []
        versions = [x for x in connection.execute(select(cls._alembic_version_table)).scalars().all()]
        return True, versions

    @classmethod
    def _drop_version_table(cls, connection: Connection) -> None:
        cls._alembic_version_table.drop(connection, checkfirst=True)

    @classmethod
    def _create_version_table(cls, connection: Connection, versions: list[str]) -> None:
        cls._alembic_version_table.create(connection, checkfirst=True)
        if versions:
            connection.execute(cls._alembic_version_table.insert(), [{'version_num': v} for v in versions])

    async def snapshot_version_table(self) -> None:
        """快照 alembic_version 表当前状态 (表是否存在及全部版本记录), 供测试结束后恢复"""
        async with self._engine.connect() as connection:
            self._version_table_existed, self._original_versions = await connection.run_sync(
                self._check_need_snapshot_version_table
            )

    async def restore_version_table(self) -> None:
        """恢复 alembic_version 表到快照状态"""
        async with self._engine.begin() as connection:
            await connection.run_sync(self._drop_version_table)

        if self._version_table_existed:
            async with self._engine.begin() as connection:
                await connection.run_sync(self._create_version_table, self._original_versions)

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

    def _get_already_tables(self, connection: Connection) -> list[str]:
        return [name for name in inspect(connection).get_table_names() if name.startswith(self._db_prefix)]

    async def count_already_tables(self) -> int:
        """检查测试数据库中是否已存在数据表"""
        async with self._engine.connect() as connection:
            return len(await connection.run_sync(self._get_already_tables))

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


@pytest.fixture
async def test_database_helper() -> AsyncGenerator[_TestDatabaseMigrationHelper, None]:
    """测试数据库操作辅助 fixture

    setup 阶段快照 alembic_version 表状态, teardown 阶段恢复原状并清理测试哨兵表
    """
    helper = _TestDatabaseMigrationHelper()
    await helper.snapshot_version_table()
    try:
        yield helper
    finally:
        await helper.restore_version_table()
