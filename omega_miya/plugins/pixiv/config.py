"""
@Author         : Ailitonia
@Date           : 2021/06/13 18:48
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Pixiv Plugin Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError


class PixivPluginConfig(BaseModel):
    """Pixiv 插件配置"""
    # 允许预览 r18 作品的权限节点
    pixiv_plugin_allow_r18_node: Literal['allow_r18'] = 'allow_r18'
    # pixiv 画师订阅 SubscriptionSource 的 sub_type
    pixiv_plugin_user_subscription_type: Literal['pixiv_user'] = 'pixiv_user'
    # 默认自动撤回消息时间
    pixiv_plugin_auto_recall_time: int = 30
    # 单个作品发送图片数量限制, 避免单个作品图过多导致一次性发送过多图导致网络堵塞和风控
    pixiv_plugin_artwork_preview_page_limiting: int = 10
    # 启动 gif 动图生成, 针对动图作品生成 gif 图片, 消耗资源较大, 请谨慎开启
    pixiv_plugin_enable_generate_gif: bool = False

    class Config:
        extra = "ignore"


try:
    pixiv_plugin_config = PixivPluginConfig.parse_obj(get_driver().config)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Pixiv 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Pixiv 插件配置格式验证失败, {e}')


__all__ = [
    'pixiv_plugin_config'
]
