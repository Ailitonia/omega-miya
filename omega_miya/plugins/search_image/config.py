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

    # 识图结果发送采用消息节点模式(仅限群组)
    enable_node_custom: bool = True

    # 相似图片功能启用发送图片后自动撤回, 默认撤回时间30秒
    auto_recall_time: int = 30
    enable_recommend_auto_recall: bool = True

    class Config:
        extra = "ignore"
