"""
@Author         : Ailitonia
@Date           : 2024/6/9 下午2:54
@FileName       : migrate
@Project        : nonebot2_miya
@Description    : alembic migration tools
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import pathlib
import sys
from enum import StrEnum, unique
from typing import TYPE_CHECKING, Annotated, Literal

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from nonebot.log import logger
from nonebot.utils import run_sync
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

_ROOT_PATH = pathlib.Path(sys.path[0]).absolute()
"""项目根目录"""
_ALEMBIC_INI = _ROOT_PATH.joinpath('alembic.ini')
"""Alembic 配置文件"""
_ALEMBIC_CFG = Config(_ALEMBIC_INI)
"""构造 Alembic 配置"""
_ALEMBIC_VERSION_TABLE_NAME: Literal['alembic_version'] = 'alembic_version'
"""Alembic Version 表名"""
_ALEMBIC_VERSION_COLUMN_NAME: Literal['version_num'] = 'version_num'
"""Alembic Version 字段名"""


@unique
class MigrationStatus(StrEnum):
    """数据库迁移状态"""

    FRESH = 'fresh'  # 空数据库, 可直接初始化
    UPGRADABLE = 'upgradable'  # 数据库版本落后于最新版本, 可安全执行自动升级
    UP_TO_DATE = 'up_to_date'  # 数据库已是最新版本
    UNSTAMPED_DATABASE = 'unstamped_database'  # 数据库中存在业务数据表但未标记 Alembic 版本
    UNKNOWN_REVISION = 'unknown_revision'  # 数据库当前版本不在迁移脚本历史中
    MULTIPLE_CURRENT_REVISIONS = 'multiple_current_revisions'  # 数据库版本表中存在多条版本记录
    MULTIPLE_HEADS = 'multiple_heads'  # 迁移脚本存在多个 head 版本


class MigrationCheckResult(BaseModel):
    """数据库迁移状态检查结果"""

    status: MigrationStatus
    current_revisions: tuple[str, ...]  # 数据库当前版本记录
    head: str | None  # 迁移脚本最新版本
    message: Annotated[str, Field(default_factory=str)]  # 附加信息, 不安全时为原因及处理指引

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)

    @property
    def is_safe(self) -> bool:
        """当前状态是否可以安全地执行自动迁移"""
        return self.status in {MigrationStatus.FRESH, MigrationStatus.UPGRADABLE, MigrationStatus.UP_TO_DATE}


class ScriptRevisionsStatus(BaseModel):
    """迁移脚本版本信息"""

    heads: Annotated[list[str], Field(default_factory=list)]  # heads 列表
    known_revisions: Annotated[set[str], Field(default_factory=set)]  # 全部已知版本集合

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class DatabaseRevisionsStatus(BaseModel):
    """数据库版本记录及业务数据表状态"""

    current_revisions: Annotated[list[str], Field(default_factory=list)]  # 数据库当前版本列表
    has_business_tables: bool  # 是否存在业务数据表

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


def _get_script_revisions() -> ScriptRevisionsStatus:
    """读取迁移脚本版本信息 (同步函数, 纯文件读取, 不连接数据库)"""

    script = ScriptDirectory.from_config(_ALEMBIC_CFG)
    revisions_iter = script.walk_revisions()

    return ScriptRevisionsStatus.model_validate({
        'heads': script.get_heads(),
        'known_revisions': {revision.revision for revision in revisions_iter},
    })


def _inspect_database(connection: 'Connection') -> DatabaseRevisionsStatus:
    """检查数据库版本记录及业务数据表 (同步函数, 由 AsyncConnection.run_sync 调用)"""
    from sqlalchemy import column, inspect, select, table

    from .config import database_config

    table_names = inspect(connection).get_table_names()
    has_business_tables = any(name.startswith(database_config.db_prefix) for name in table_names)

    current_revisions = []
    if _ALEMBIC_VERSION_TABLE_NAME in table_names:
        version_query = select(table(_ALEMBIC_VERSION_TABLE_NAME, column(_ALEMBIC_VERSION_COLUMN_NAME)))
        current_revisions = list(connection.execute(version_query).scalars().all())

    return DatabaseRevisionsStatus.model_validate({
        'current_revisions': current_revisions,
        'has_business_tables': has_business_tables,
    })


async def check_migration_state() -> MigrationCheckResult:
    """检查数据库迁移状态, 用于启动时自动迁移的前置安全校验"""
    from .connector import get_engine

    script_revisions_status = _get_script_revisions()

    # 迁移脚本自身存在多个 head, 迁移历史已损坏, 无法自动迁移
    if len(script_revisions_status.heads) > 1:
        return MigrationCheckResult(
            status=MigrationStatus.MULTIPLE_HEADS,
            current_revisions=(),
            head=None,
            message=(
                f'迁移脚本存在多个 head 版本: {", ".join(script_revisions_status.heads)}, '
                '迁移历史已损坏, 请检查 alembic/versions 目录'
            ),
        )
    head = script_revisions_status.heads[0]

    async with get_engine().connect() as connection:
        database_revisions_status = await connection.run_sync(_inspect_database)

    # 数据库中没有版本记录
    if not database_revisions_status.current_revisions:
        if database_revisions_status.has_business_tables:
            # 存在业务数据表但未标记版本, 无法确认数据库结构版本, 直接升级会对已存在的表执行建表操作
            return MigrationCheckResult(
                status=MigrationStatus.UNSTAMPED_DATABASE,
                current_revisions=(),
                head=head,
                message=(
                    '检测到数据库中存在业务数据表, 但未发现 Alembic 版本记录, 无法确认数据库结构版本, 自动迁移已中止; '
                    '若数据库结构已与当前代码基线一致, 请执行 "python bot.py --database-stamp [revision-id]" '
                    '手动对齐数据库基线版本后重新启动'
                ),
            )
        # 空数据库, 可直接初始化
        return MigrationCheckResult(
            status=MigrationStatus.FRESH,
            current_revisions=(),
            head=head,
        )

    # 版本表中存在多条记录, 无法确认数据库当前版本
    if len(database_revisions_status.current_revisions) > 1:
        return MigrationCheckResult(
            status=MigrationStatus.MULTIPLE_CURRENT_REVISIONS,
            current_revisions=tuple(database_revisions_status.current_revisions),
            head=head,
            message=(
                f'数据库版本表中存在多条版本记录: {", ".join(database_revisions_status.current_revisions)}, '
                '无法确认数据库当前结构版本, 自动迁移已中止; '
                '请手动清理 alembic_version 表为唯一正确版本后重新启动'
            ),
        )

    current_revision = database_revisions_status.current_revisions[0]

    # 数据库已是最新版本
    if current_revision == head:
        return MigrationCheckResult(
            status=MigrationStatus.UP_TO_DATE,
            current_revisions=(current_revision,),
            head=head,
        )

    # 数据库当前版本不在迁移脚本历史中, 代码与数据库版本不匹配
    if current_revision not in script_revisions_status.known_revisions:
        return MigrationCheckResult(
            status=MigrationStatus.UNKNOWN_REVISION,
            current_revisions=(current_revision,),
            head=head,
            message=(
                f'数据库当前版本 {current_revision!r} 不在当前代码的迁移历史中, 自动迁移已中止; '
                '请执行 "python bot.py --database-check" 检查数据库状态, 确认代码与数据库版本匹配后, '
                f'可执行 "python bot.py --database-stamp [revision-id]" 手动对齐数据库基线版本'
            ),
        )

    # 数据库版本落后 (单一 head 下, 已知版本必为 head 的祖先), 可安全执行自动升级
    return MigrationCheckResult(
        status=MigrationStatus.UPGRADABLE,
        current_revisions=(current_revision,),
        head=head,
        message=f'数据库当前版本 {current_revision!r} 落后于最新版本 {head!r}, 将自动执行升级',
    )


def run_check_current() -> None:
    """执行数据库检查"""
    logger.opt(colors=True).debug('<lc>Alembic</lc> | Current database info')
    command.current(config=_ALEMBIC_CFG, verbose=True)
    logger.opt(colors=True).debug('<lc>Alembic</lc> | Head database version')
    command.heads(config=_ALEMBIC_CFG, verbose=True)
    logger.opt(colors=True).debug('<lc>Alembic</lc> | Checking database new upgrade version')
    command.check(config=_ALEMBIC_CFG)


def run_revision(message: str, *, autogenerate: bool = True) -> None:
    """执行生成数据库迁移版本"""
    logger.opt(colors=True).info(f'<lc>Alembic</lc> | Creating database revision {message!r}')
    command.revision(config=_ALEMBIC_CFG, message=message, autogenerate=autogenerate)
    logger.opt(colors=True).success(f'<lc>Alembic</lc> | Created database revision {message!r} succeed')


def run_stamp(revision_id: str) -> None:
    """执行标记数据库版本"""
    logger.opt(colors=True).info(f'<lc>Alembic</lc> | Stamp database as {revision_id!r}')
    command.stamp(config=_ALEMBIC_CFG, revision=revision_id)
    logger.opt(colors=True).success(f'<lc>Alembic</lc> | Stamped database as {revision_id!r} succeed')


def run_upgrade_migrations(revision: str = 'head') -> None:
    """执行数据库升级

    同步函数: 在独立线程中运行, env.py 内的 asyncio.run 才能正常工作"""
    logger.opt(colors=True).info(f'<lc>Alembic</lc> | Running database upgrading migrations to {revision!r}')
    command.upgrade(_ALEMBIC_CFG, revision)
    logger.opt(colors=True).success(f'<lc>Alembic</lc> | Upgraded database to {revision!r} succeed')


def run_downgrade_migrations(revision: str = 'head') -> None:
    """执行数据库降级

    同步函数: 在独立线程中运行, env.py 内的 asyncio.run 才能正常工作"""
    logger.opt(colors=True).info(f'<lc>Alembic</lc> | Running database downgrading migrations to {revision!r}')
    command.downgrade(_ALEMBIC_CFG, revision)
    logger.opt(colors=True).success(f'<lc>Alembic</lc> | Downgraded database to {revision!r} succeed')


async def async_migrate_to_head() -> None:
    """执行数据库升级到最新

    异步入口: 迁移是同步阻塞任务, 丢到线程里执行, 避免卡住事件循环。"""

    @run_sync
    def _upgrade_head() -> None:
        run_upgrade_migrations(revision='head')

    await _upgrade_head()


__all__ = [
    'MigrationCheckResult',
    'MigrationStatus',
    'async_migrate_to_head',
    'check_migration_state',
    'run_check_current',
    'run_revision',
    'run_stamp',
    'run_upgrade_migrations',
    'run_downgrade_migrations',
]
