"""
@Author         : Ailitonia
@Date           : 2021/06/12 20:45
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List, Dict, Union
from pydantic import BaseSettings


class Config(BaseSettings):
    # plugin custom config
    # 启用使用群组转发自定义消息节点的模式发送信息
    # 发送速度受限于网络上传带宽, 有可能导致超时或发送失败, 请酌情启用
    enable_node_custom: bool = True
    sub_id: str = 'pixivision'

    # 不推送包含以下 tag 的 article
    tag_block_list: List[Dict[str, Union[int, str]]] = [
        {'id': 206, 'name': '时尚男子'},
        {'id': 10, 'name': '有趣的'},
        {'id': 18, 'name': '恶搞'},
        {'id': 217, 'name': '恐怖'},
        # {'id': 32, 'name': '男孩子'},
        {'id': 88, 'name': '帅哥'},
        {'id': 89, 'name': '大叔'},
        {'id': 328, 'name': '男子的眼睛'},
        {'id': 344, 'name': '日本画'},
        {'id': 321, 'name': '绝望'},
        {'id': 472, 'name': '我的英雄学院'}
    ]

    class Config:
        extra = "ignore"
