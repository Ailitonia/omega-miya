"""
@Author         : Ailitonia
@Date           : 2022/12/11 22:34
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Message tools config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from src.resource import TemporaryResource


@dataclass
class MessageToolsConfig:
    """Message Tools 配置"""
    # 默认的生成缓存文件路径
    tmp_message_data_folder: TemporaryResource = TemporaryResource('message_data')


message_tools_config = MessageToolsConfig()


__all__ = [
    'message_tools_config'
]
