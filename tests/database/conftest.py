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

from collections.abc import AsyncGenerator, Callable
from typing import ClassVar

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, inspect, select
from sqlalchemy.engine import Connection


class _TestDatabaseHelper:
    """测试数据库操作辅助类

    敏感操作警告: 本类方法会直接修改 .env.test 配置的测试数据库,
    所有修改均由 test_database_helper fixture 在测试结束后自动恢复, 禁止将测试环境指向生产数据库
    """

    _alembic_version_table: ClassVar[Table] = Table(
        'alembic_version',
        MetaData(),
        Column('version_num', String(32), nullable=False),
    )
    """Alembic 版本表定义 (与 alembic 默认结构一致)"""

    def __init__(self) -> None:
        from src.database.config import database_config
        from src.database.connector import engine

        self._engine = engine
        self._db_prefix = database_config.db_prefix
        self._version_table_existed: bool = False
        self._original_versions: list[str] = []

    @property
    def _sentinel_table(self) -> Table:
        """测试用哨兵业务表 (测试专用命名, 用于构造业务表存在场景)"""
        return Table(
            f'{self._db_prefix}test_migration_check_sentinel',
            MetaData(),
            Column('id', Integer),
        )

    @classmethod
    def _check_need_snapshot_version_table(cls, connection: Connection) -> tuple[bool, list[str]]:
        """检查是否需要创建 alembic_version 表当前状态

        :return: tuple[version_table_existed, original_versions]
        """
        table_names = inspect(connection).get_table_names()
        if cls._alembic_version_table.name not in table_names:
            return False, []
        versions = [x for x in connection.execute(select(cls._alembic_version_table)).scalars().all()]
        return True, versions

    async def snapshot(self) -> None:
        """快照 alembic_version 表当前状态 (表是否存在及全部版本记录), 供测试结束后恢复"""
        async with self._engine.connect() as connection:
            self._version_table_existed, self._original_versions = await connection.run_sync(
                self._check_need_snapshot_version_table
            )

    async def restore(self) -> None:
        """清理测试哨兵表, 并恢复 alembic_version 表快照状态"""
        async with self._engine.begin() as connection:
            await connection.run_sync(self._drop_sentinel_table)

        async with self._engine.begin() as connection:
            await connection.run_sync(self._drop_version_table)

        if self._version_table_existed:
            async with self._engine.begin() as connection:
                await connection.run_sync(self._create_version_table, self._original_versions)

    @classmethod
    def _drop_version_table(cls, connection: Connection) -> None:
        cls._alembic_version_table.drop(connection, checkfirst=True)

    @classmethod
    def _create_version_table(cls, connection: Connection, versions: list[str]) -> None:
        cls._alembic_version_table.create(connection, checkfirst=True)
        if versions:
            connection.execute(cls._alembic_version_table.insert(), [{'version_num': v} for v in versions])

    def _drop_sentinel_table(self, connection: Connection) -> None:
        self._sentinel_table.drop(connection, checkfirst=True)

    def _create_sentinel_table(self, connection: Connection) -> None:
        self._sentinel_table.create(connection, checkfirst=True)

    def _check_business_tables(self, connection: Connection) -> bool:
        return any(name.startswith(self._db_prefix) for name in inspect(connection).get_table_names())

    async def create_sentinel(self) -> None:
        """创建测试哨兵业务表 (敏感操作: 直接在测试数据库中建表, 测试结束后由 fixture 自动删除)"""
        async with self._engine.begin() as connection:
            await connection.run_sync(self._create_sentinel_table)

    async def rebuild_versions(self, versions: list[str] | None) -> None:
        """重建 alembic_version 表版本记录

        敏感操作: 直接删除并重建测试数据库的 alembic_version 表, 测试结束后由 fixture 自动恢复

        :param versions: None 表示删除版本表, 空列表表示创建空版本表, 否则重建版本表并插入对应版本记录
        """
        async with self._engine.begin() as connection:
            await connection.run_sync(self._drop_version_table)
        if versions is not None:
            async with self._engine.begin() as connection:
                await connection.run_sync(self._create_version_table, versions)

    async def has_business_tables(self) -> bool:
        """检查测试数据库中是否存在业务数据表"""
        async with self._engine.connect() as connection:
            return await connection.run_sync(self._check_business_tables)


@pytest.fixture
async def test_database_helper() -> AsyncGenerator[_TestDatabaseHelper, None]:
    """测试数据库操作辅助 fixture

    setup 阶段快照 alembic_version 表状态, teardown 阶段恢复原状并清理测试哨兵表
    """
    helper = _TestDatabaseHelper()
    await helper.snapshot()
    try:
        yield helper
    finally:
        await helper.restore()


@pytest.fixture
def patch_script_revisions(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    """工厂 fixture: 伪造迁移脚本版本信息"""

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
