"""
@Author         : Ailitonia
@Date           : 2024/10/9 14:53:50
@FileName       : consts.py
@Project        : omega-miya
@Description    : 消息转储工具缓存配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from src.resource import TemporaryResource


@dataclass
class MessageTransferPath:
    """消息转储缓存配置"""

    # 缓存文件夹
    default_save_folder: TemporaryResource = TemporaryResource('message_transfer_utils')

    def get_target_folder(self, adapter_name: str, seg_type: str):
        return self.default_save_folder(adapter_name, seg_type)


save_path = MessageTransferPath()

__all__ = [
    'save_path',
]
