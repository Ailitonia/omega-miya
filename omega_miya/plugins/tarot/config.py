"""
@Author         : Ailitonia
@Date           : 2021/09/01 1:12
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 配置文件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Dict
from pydantic import BaseSettings
from .tarot_resources import BaseTarotResources, BiliTarotResources


class Config(BaseSettings):

    default_resources: BaseTarotResources = BiliTarotResources()
    # 为某些特殊定制要求 为不同群组分配不同资源文件
    group_resources: Dict[int, BaseTarotResources] = {
        0: BiliTarotResources()
    }

    class Config:
        extra = "ignore"

    def get_group_resources(self, group_id: int) -> BaseTarotResources:
        return self.group_resources.get(group_id, self.default_resources)
