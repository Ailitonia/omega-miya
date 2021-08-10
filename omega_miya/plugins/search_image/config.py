"""
@Author         : Ailitonia
@Date           : 2021/06/16 22:53
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseSettings


class Config(BaseSettings):
    # plugin custom config
    # 识图引擎开关, 使用优先级saucenao>iqdb>ascii2d
    enable_saucenao: bool = True
    enable_iqdb: bool = True
    enable_ascii2d: bool = True

    class Config:
        extra = "ignore"
