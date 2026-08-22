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

from alembic import command
from alembic.config import Config
from nonebot.log import logger
from nonebot.utils import run_sync

_ROOT_PATH = pathlib.Path(sys.path[0]).absolute()
"""项目根目录"""
_ALEMBIC_INI = _ROOT_PATH.joinpath('alembic.ini')
"""Alembic 配置文件"""
_ALEMBIC_CFG = Config(_ALEMBIC_INI)
"""构造 Alembic 配置"""


def run_check_current() -> None:
    """执行数据库检查"""
    logger.opt(colors=True).debug(f'<lc>Alembic</lc> | Current database info')
    command.current(config=_ALEMBIC_CFG, verbose=True)
    logger.opt(colors=True).debug(f'<lc>Alembic</lc> | Head database version')
    command.heads(config=_ALEMBIC_CFG, verbose=True)
    logger.opt(colors=True).debug(f'<lc>Alembic</lc> | Checking database new upgrade version')
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
    'async_migrate_to_head',
    'run_check_current',
    'run_revision',
    'run_stamp',
    'run_upgrade_migrations',
    'run_downgrade_migrations',
]
