"""
@Author         : Ailitonia
@Date           : 2021/08/04 0:10
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseSettings


class Config(BaseSettings):

    # plugin custom config
    """
    检查模式, 是否启用检查池模式
    """
    enable_check_pool_mode: bool = True

    class Config:
        extra = "ignore"
