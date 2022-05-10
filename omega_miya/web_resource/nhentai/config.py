"""
@Author         : Ailitonia
@Date           : 2022/04/10 23:50
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Nhentai Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from omega_miya.local_resource import TmpResource


@dataclass
class NhentaiConfig:
    """Nhentai 配置"""
    # 默认的下载文件路径
    default_download_folder: TmpResource = TmpResource('nhentai', 'download')
    # 预览图生成路径
    default_preview_img_folder: TmpResource = TmpResource('nhentai', 'preview')
    default_preview_size: tuple[int, int] = (224, 327)  # 默认预览图缩略图大小


nhentai_config = NhentaiConfig()


__all__ = [
    'nhentai_config'
]
