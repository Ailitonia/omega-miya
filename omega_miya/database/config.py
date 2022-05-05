"""
@Author         : Ailitonia
@Date           : 2022/02/21 10:12
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : database config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from enum import Enum, unique
from typing import Literal
from pydantic import BaseModel, IPvAnyAddress, ValidationError


@unique
class DatabaseDriver(Enum):
    """数据库驱动"""
    asyncmy = 'asyncmy'
    aiomysql = 'aiomysql'


class DatabaseConfig(BaseModel):
    """数据库链接配置"""
    database: Literal['mysql']  # 数据库类型
    db_driver: DatabaseDriver  # 数据库驱动
    db_host: IPvAnyAddress  # 数据库 IP 地址
    db_port: int  # 数据库端口
    db_user: str  # 数据库用户名
    db_password: str  # 数据库密码
    db_name: str  # 数据库名称
    db_prefix: str  # 数据表前缀

    class Config:
        extra = "ignore"


try:
    database_config = DatabaseConfig.parse_obj(get_driver().config)  # 导入并验证数据库配置
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>数据库配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'数据库配置格式验证失败, {e}')


__all__ = [
    'database_config'
]
