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
- 本目录测试直接复用 src.database 的数据库连接, 操作 .env.test 配置的测试数据库, 禁止将测试环境指向生产数据库运行
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
from collections.abc import AsyncGenerator
from typing import Any, ClassVar

import pytest
from nonebot.utils import run_sync
from sqlalchemy import Column, Integer, MetaData, String, Table, inspect, select
from sqlalchemy.engine import Connection

from tests.utils import unique_test_id


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


# ---------------------------------------------------------------------- #
# test_003_dal_crud 共享测试数据 fixtures (class 作用域, 每个消费类获得独立随机值)
# ---------------------------------------------------------------------- #


@pytest.fixture(scope='class')
def test_bot_type() -> str:
    """测试用 Bot 类型 (须为 BotType 枚举成员, 不可随机化)"""
    return 'OneBot V11'


@pytest.fixture(scope='class')
def test_bot_self_id() -> str:
    return unique_test_id('TEST_BOT')


@pytest.fixture(scope='class')
def test_sub_type() -> str:
    return unique_test_id('TEST_SUB_TYPE')


@pytest.fixture(scope='class')
def test_sub_id() -> str:
    return unique_test_id('TEST_SUB_ID')


@pytest.fixture(scope='class')
def test_sub_user_name() -> str:
    return unique_test_id('TEST_SUB_USER_NAME')


@pytest.fixture(scope='class')
def test_plugin_name() -> str:
    return unique_test_id('PLUGIN_NAME')


@pytest.fixture(scope='class')
def test_plugin_module() -> str:
    return unique_test_id('PLUGIN_MODULE')


@pytest.fixture(scope='class')
def test_history_message_id() -> str:
    return unique_test_id('MESSAGE_ID')


@pytest.fixture(scope='class')
def test_history_bot_self_id() -> str:
    return unique_test_id('BOT_SELF_ID')


@pytest.fixture(scope='class')
def test_history_event_entity_id() -> str:
    return unique_test_id('EVENT_ENTITY_ID')


@pytest.fixture(scope='class')
def test_history_user_entity_id() -> str:
    return unique_test_id('USER_ENTITY_ID')


@pytest.fixture(scope='class')
def test_history_message_type() -> str:
    return unique_test_id('MESSAGE_TYPE')


@pytest.fixture(scope='class')
def test_history_message_plain_text() -> str:
    return unique_test_id('MESSAGE_PLAIN_TEXT')


@pytest.fixture(scope='class')
def test_history_message_raw(
        test_history_message_type: str,
        test_history_message_plain_text: str,
) -> list[dict[str, Any]]:
    return [
        {'type': 'text', 'data': {'text': test_history_message_plain_text}},
        {'type': test_history_message_type, 'data': {'meta': 'test'}},
    ]


@pytest.fixture(scope='class')
def test_global_cache_name() -> str:
    return unique_test_id('CACHE_NAME')


@pytest.fixture(scope='class')
def test_global_cache_key() -> str:
    return unique_test_id('CACHE_KEY')


@pytest.fixture(scope='class')
def test_global_cache_value() -> str:
    return unique_test_id('CACHE_VALUE')


@pytest.fixture(scope='class')
def test_statistic_plugin_name() -> str:
    return unique_test_id('PLUGIN_NAME')


@pytest.fixture(scope='class')
def test_statistic_plugin_module() -> str:
    return unique_test_id('PLUGIN_MODULE')


@pytest.fixture(scope='class')
def test_statistic_call_entity_meta() -> dict[str, Any]:
    return {
        'id': random.randint(100000, 999999),
        'name': unique_test_id('ENTITY_META_NAME'),
        'message': unique_test_id('ENTITY_META_MESSAGE'),
    }


@pytest.fixture(scope='class')
def test_statistic_call_data() -> dict[str, Any]:
    return {
        'command': unique_test_id('CALL_COMMAND'),
        'data': {
            'target': unique_test_id('CALL_DATA_TARGET'),
            'payload': unique_test_id('CALL_DATA_PAYLOAD'),
        },
        'token': unique_test_id('CALL_TOKEN'),
    }


@pytest.fixture(scope='class')
def test_smc_source() -> str:
    return unique_test_id('TEST_SMC_SOURCE')


@pytest.fixture(scope='class')
def test_smc_m_type() -> str:
    return unique_test_id('TEST_SMC_M_TYPE')


@pytest.fixture(scope='class')
def test_smc_m_id() -> str:
    return unique_test_id('TEST_SMC_M_ID')


@pytest.fixture(scope='class')
def test_smc_m_uid() -> str:
    return unique_test_id('TEST_SMC_M_UID')


@pytest.fixture(scope='class')
def test_smc_title() -> str:
    return unique_test_id('TEST_SMC_TITLE')


@pytest.fixture(scope='class')
def test_smc_content() -> str:
    return unique_test_id('TEST_SMC_CONTENT')


@pytest.fixture(scope='class')
def test_content_raw_data(
        test_smc_source: str,
        test_smc_m_type: str,
        test_smc_m_id: str,
        test_smc_m_uid: str,
        test_smc_title: str,
        test_smc_content: str,
) -> dict[str, Any]:
    return {
        'id': test_smc_m_id,
        'type': test_smc_m_type,
        'uid': test_smc_m_uid,
        'content': {
            'title': test_smc_title,
            'body': test_smc_content,
        },
        'source': test_smc_source,
    }


@pytest.fixture(scope='class')
def test_system_setting_name() -> str:
    return unique_test_id('SETTING_NAME')


@pytest.fixture(scope='class')
def test_system_setting_key() -> str:
    return unique_test_id('SETTING_KEY')


@pytest.fixture(scope='class')
def test_system_setting_value() -> str:
    return unique_test_id('SETTING_VALUE')
