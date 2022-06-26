"""
@Author         : Ailitonia
@Date           : 2021/09/01 1:12
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : 配置文件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from omega_miya.local_resource import LocalResource, TmpResource


@dataclass
class TarotLocalResourceConfig:
    # 塔罗牌插件默认内置的静态资源文件路径
    image_resource_folder: LocalResource = LocalResource('images', 'tarot')
    default_font_file: LocalResource = LocalResource('fonts', 'fzzxhk.ttf')
    # 绘制图片保存路径
    default_save_folder: TmpResource = TmpResource('tarot', 'cards')


tarot_local_resource_config = TarotLocalResourceConfig()


__all__ = [
    'tarot_local_resource_config'
]
