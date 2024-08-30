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

from src.resource import StaticResource, TemporaryResource


@dataclass
class TarotLocalResourceConfig:
    # 塔罗牌插件默认内置的静态资源文件路径
    image_resource_folder: StaticResource = StaticResource('images', 'tarot')
    default_font_file: StaticResource = StaticResource('fonts', 'fzzxhk.ttf')
    # 绘制图片保存路径
    default_save_folder: TemporaryResource = TemporaryResource('tarot', 'cards')


tarot_local_resource_config = TarotLocalResourceConfig()


__all__ = [
    'tarot_local_resource_config',
]
