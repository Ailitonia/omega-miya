import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Explicitly import the database model, without relying on the side effects
# of the `nonebot.load_plugins` or `src.database` package import chain to load the model.
import src.database.schema  # noqa: F401
from src.database.config import database_config
from src.database.schema_base import OmegaDeclarativeBase

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
# overwrite the config of database URL, 转义 % 防止 configparser 插值解析
config.set_main_option('sqlalchemy.url', database_config.connector.url.replace('%', '%%'))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    # 注意: 必须指定 disable_existing_loggers=False, 否则 fileConfig 会禁用 alembic.ini 中未声明的
    # 所有已存在 logger (如 uvicorn / uvicorn.error), 导致迁移执行后 uvicorn 的启动/运行日志全部丢失,
    # 表现为 "Application startup complete" 等日志不再输出, 看似启动卡死。
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = OmegaDeclarativeBase.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        compare_type=True,
        render_as_batch=True,  # 为 SQLite 运行“批处理”迁移
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=True,  # 为 SQLite 运行“批处理”迁移
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
