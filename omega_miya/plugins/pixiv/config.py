"""
@Author         : Ailitonia
@Date           : 2021/06/13 18:48
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseSettings


class Config(BaseSettings):
    # plugin custom config
    # 针对榜单/r18等消息启用使用群组转发自定义消息节点的模式发送信息
    # 发送速度受限于网络上传带宽, 有可能导致超时或发送失败, 请酌情启用
    enable_node_custom: bool = True
    # 自动撤回时间
    auto_recall_time: int = 30
    # 启动 gif 动图生成, 针对动图作品生成 gif 图片, 消耗资源较大, 请谨慎开启
    enable_generate_gif: bool = False

    class Config:
        extra = "ignore"
