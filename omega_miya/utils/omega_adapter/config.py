"""
@Author         : Ailitonia
@Date           : 2021/10/06 21:52
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseSettings


class Config(BaseSettings):
    pass

    class Config:
        extra = "ignore"
