"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:19
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : omega database config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from enum import Enum, unique
from nonebot import get_driver, logger
from pydantic import BaseModel, IPvAnyAddress, ValidationError
from typing import Literal
from urllib.parse import quote
import os
import pathlib
import sys


@unique
class MysqlDriver(Enum):
    """mysql 数据库驱动"""
    asyncmy = 'asyncmy'
    aiomysql = 'aiomysql'


@unique
class PostgresqlDriver(Enum):
    """PostgreSQL 数据库驱动"""
    asyncpg = 'asyncpg'


@unique
class SQLiteDriver(Enum):
    """SQLite 数据库驱动"""
    aiosqlite = 'aiosqlite'


class DatabaseConnector(BaseModel):
    """数据库链接对象"""
    url: str
    connect_args: dict


class DatabaseType(BaseModel):
    """数据库类型"""
    database: Literal['mysql', 'postgresql', 'sqlite']  # 数据库类型

    class Config:
        extra = "ignore"

    @property
    def connector(self) -> DatabaseConnector:
        raise NotImplementedError

    @property
    def table_args(self) -> dict | None:
        return None


class MysqlDatabaseConfig(DatabaseType):
    """mysql 数据库链接配置"""
    db_driver: MysqlDriver  # 数据库驱动
    db_host: IPvAnyAddress  # 数据库 IP 地址
    db_port: int = 3306  # 数据库端口
    db_user: str  # 数据库用户名
    db_password: str  # 数据库密码
    db_name: str  # 数据库名称
    db_prefix: str  # 数据表前缀

    @property
    def connector(self) -> DatabaseConnector:
        return DatabaseConnector(
            url=f'{self.database}+{self.db_driver.value}://{self.db_user}'
                f':{quote(str(self.db_password))}@{self.db_host}:{self.db_port}/{self.db_name}',
            connect_args={
                'connect_args': {"use_unicode": True, "charset": "utf8mb4"}
            }
        )

    @property
    def table_args(self) -> dict:
        return {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8mb4'}


class PostgresqlDatabaseConfig(DatabaseType):
    """PostgreSQL 数据库链接配置"""
    db_driver: PostgresqlDriver
    db_host: IPvAnyAddress
    db_port: int = 5432
    db_user: str
    db_password: str
    db_name: str
    db_prefix: str

    @property
    def connector(self) -> DatabaseConnector:
        return DatabaseConnector(
            url=f'{self.database}+{self.db_driver.value}://{self.db_user}'
                f':{quote(str(self.db_password))}@{self.db_host}:{self.db_port}/{self.db_name}',
            connect_args={
                'connect_args': {"server_settings": {"jit": "off"}}
            }
        )


class SQLiteDatabaseConfig(DatabaseType):
    """SQLite 数据库链接配置"""
    db_driver: SQLiteDriver
    db_name: str
    db_prefix: str

    @property
    def connector(self) -> DatabaseConnector:
        database_path = pathlib.Path(os.path.abspath(sys.path[0])).joinpath(f'{self.db_name}.db').resolve()
        return DatabaseConnector(
            url=f'{self.database}+{self.db_driver.value}:///{database_path}',
            connect_args={}
        )


try:
    database_type = DatabaseType.parse_obj(get_driver().config)  # 导入并验证数据库类型
    match database_type.database:  # 验证数据库配置
        case 'mysql':
            database_config = MysqlDatabaseConfig.parse_obj(get_driver().config)
        case 'postgresql':
            database_config = PostgresqlDatabaseConfig.parse_obj(get_driver().config)
        case 'sqlite':
            database_config = SQLiteDatabaseConfig.parse_obj(get_driver().config)
        case _:
            raise ValueError(f'illegal database type: {database_type.database}')
except (ValidationError, ValueError) as e:
    logger.opt(colors=True).critical(f'<r>数据库配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'数据库配置格式验证失败, {e}')


__all__ = [
    'database_config'
]
