"""
@Author         : Ailitonia
@Date           : 2021/06/13 18:48
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Pixiv Plugin Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ValidationError

from src.resource import TemporaryResource


class PixivPluginConfig(BaseModel):
    """Pixiv 插件配置"""
    # 默认自动撤回消息时间(设置 0 为不撤回)
    pixiv_plugin_auto_recall_time: int = 60
    # 单个作品发送图片数量限制, 避免单个作品图过多导致一次性发送过多图导致网络堵塞和风控
    pixiv_plugin_artwork_preview_page_limiting: int = 10

    class Config:
        extra = "ignore"


@dataclass
class PixivPluginResourceConfig:
    # 缓存处理后图片的位置
    default_processed_image_folder: TemporaryResource = TemporaryResource('pixiv', 'processed')


try:
    pixiv_plugin_config = get_plugin_config(PixivPluginConfig)
    pixiv_plugin_resource_config = PixivPluginResourceConfig()
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Pixiv 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Pixiv 插件配置格式验证失败, {e}')


__all__ = [
    'pixiv_plugin_config',
    'pixiv_plugin_resource_config'
]
