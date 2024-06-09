"""
@Author         : Ailitonia
@Date           : 2024/6/9 下午2:54
@FileName       : migrate
@Project        : nonebot2_miya
@Description    : alembic migration tools
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import sys
import pathlib

from alembic import command
from alembic.config import Config
from nonebot.log import logger

from .config import database_config


def construct_config() -> Config:
    prepend_sys_path = pathlib.Path(sys.path[0])
    script_location = prepend_sys_path.joinpath('alembic_scripts')
    file_template = '%%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s'
    sqlalchemy_url = database_config.connector.url.replace('%', '%%')

    alembic_cfg = Config()
    alembic_cfg.set_main_option('prepend_sys_path', str(prepend_sys_path.resolve()))
    alembic_cfg.set_main_option('script_location', str(script_location.resolve()))
    alembic_cfg.set_main_option('file_template', file_template)
    alembic_cfg.set_main_option('sqlalchemy.url', sqlalchemy_url)

    return alembic_cfg


def run_revision(message: str) -> None:
    logger.opt(colors=True).info(f'<lc>alembic</lc> | Creating DB revision {message!r}')
    command.revision(config=construct_config(), message=message, autogenerate=True)
    logger.opt(colors=True).success(f'<lc>alembic</lc> | Created DB revision {message!r} completed')


def run_upgrade_migrations(revision: str = 'head') -> None:
    logger.opt(colors=True).info(f'<lc>alembic</lc> | Running DB upgrading migrations to {revision!r}')
    command.upgrade(construct_config(), revision)
    logger.opt(colors=True).success(f'<lc>alembic</lc> | Migrated DB upgrading to {revision!r} completed')


def run_downgrade_migrations(revision: str = 'head') -> None:
    logger.opt(colors=True).info(f'<lc>alembic</lc> | Running DB downgrading migrations to {revision!r}')
    command.upgrade(construct_config(), revision)
    logger.opt(colors=True).success(f'<lc>alembic</lc> | Migrated DB downgrading to {revision!r} completed')


__all__ = [
    'run_revision',
    'run_upgrade_migrations',
    'run_downgrade_migrations'
]
