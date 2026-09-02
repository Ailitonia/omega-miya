"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:20
@FileName       : connector.py
@Project        : nonebot2_miya
@Description    : omega database connector
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from asyncio import current_task

from nonebot.log import logger
from nonebot.matcher import current_event, current_matcher
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from .config import database_config

_engine: AsyncEngine
_async_session_factory: async_sessionmaker[AsyncSession]
_scoped_session_factory: async_scoped_session[AsyncSession]


def _get_current_scoped_id() -> int | tuple[int, int]:
    """获取 scoped_session 对应 id"""
    try:
        return id(current_event.get(None)), id(current_matcher.get(None))
    except LookupError:
        return id(current_task())


def _patch_sqlite_foreign_keys_pragma(async_engine: AsyncEngine) -> None:
    """为 SQLite 启用外键

    针对 SQLite 外键默认不开启问题, 通过事件监听每次建立数据库连接时, 自动执行 PRAGMA foreign_keys=ON 命令
    Note: PRAGMA 是 SQLite 特有的扩展指令, 用于查询和设置运行参数或修改内部环境变量, 无法直接在其他数据库引擎中运行
    """
    from sqlalchemy import event

    @event.listens_for(async_engine.sync_engine, 'connect')
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    logger.opt(colors=True).info(f'<lc>Database</lc> | 已为 <lg>{database_config.database}</lg> 启用外键约束')


def _init_database() -> None:
    """创建数据库连接并初始化数据库引擎"""
    global _engine

    try:
        # 创建数据库连接
        _engine = create_async_engine(
            url=database_config.connector.url,
            echo=False,
            future=True,  # 使用 2.0 API，向后兼容
            pool_pre_ping=True,
            pool_recycle=1800,
            pool_timeout=30,
            **database_config.connector.connect_args,  # 数据库连接参数
        )
        logger.opt(colors=True).info(f'<lc>Database</lc> | 已配置 <lg>{database_config.database}</lg> 数据库连接')

        # 为 sqlite 启用外键约束
        if database_config.database == 'sqlite':
            _patch_sqlite_foreign_keys_pragma(async_engine=_engine)

    except Exception as e:
        import sys
        logger.opt(colors=True).critical(f'<lc>Database</lc> | <r>创建数据库连接失败</r>, 错误信息: {e}')
        sys.exit(f'创建数据库连接失败, {e}')


def _init_session_factory() -> None:
    """初始化会话工厂"""
    global _async_session_factory, _scoped_session_factory

    try:
        # autobegin=True 默认值, 在操作请求数据库访问时, 自动启动事务处理, 即相当于调用 Session.begin()
        # autobegin=False 可以防止在构建完成后, 或者调用 Session.rollback()/commit()/close() 等方法后, 事务被隐式地开始
        # autoflush=False 关闭查询前自动 flush 的隐式行为, 何时把变更刷入数据库完全由代码显式控制
        # expire_on_commit=False will prevent attributes from being expired after commit.
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            autobegin=True,
            autoflush=False,
            expire_on_commit=False,
        )

        _scoped_session_factory = async_scoped_session(
            session_factory=_async_session_factory,
            scopefunc=_get_current_scoped_id,
        )
        logger.opt(colors=True).info('<lc>Database</lc> | 已初始化数据库会话')
    except Exception as e:
        import sys
        logger.opt(colors=True).critical(f'<lc>Database</lc> | <r>创建数据库会话工厂失败</r>, 错误信息: {e}')
        sys.exit(f'创建数据库会话工厂失败, {e}')


def get_engine() -> AsyncEngine:
    """获取数据库全局 engine"""
    try:
        return _engine
    except NameError:
        _init_database()
    return _engine  # noqa: F821


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取数据库全局会话工厂"""
    try:
        return _async_session_factory
    except NameError:
        _init_session_factory()
    return _async_session_factory  # noqa: F821


def get_scoped_session_factory() -> async_scoped_session[AsyncSession]:
    """获取数据库全局 scoped 会话工厂"""
    try:
        return _scoped_session_factory
    except NameError:
        _init_session_factory()
    return _scoped_session_factory  # noqa: F821


# init database when import
_init_database()
_init_session_factory()


__all__ = [
    'get_engine',
    'get_session_factory',
    'get_scoped_session_factory',
]
