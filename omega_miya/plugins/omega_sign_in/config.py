"""
@Author         : Ailitonia
@Date           : 2021/07/17 2:04
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseSettings


class Config(BaseSettings):

    # plugin custom config
    favorability_alias: str = '好感度'
    energy_alias: str = '能量值'
    currency_alias: str = '金币'

    class Config:
        extra = "ignore"
