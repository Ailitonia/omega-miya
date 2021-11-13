"""
@Author         : Ailitonia
@Date           : 2021/11/13 19:46
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 识番插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseSettings


class Config(BaseSettings):
    # plugin custom config
    # 识图结果发送采用消息节点模式(仅限群组)
    enable_node_custom: bool = True

    class Config:
        extra = "ignore"
