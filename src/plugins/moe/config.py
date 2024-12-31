"""
@Author         : Ailitonia
@Date           : 2021/06/03 22:05
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Moe Plugin Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from .consts import ALLOW_MOE_PLUGIN_ARTWORK_ORIGIN


class MoePluginConfig(BaseModel):
    """Moe 插件配置"""
    # 默认查询的作品来源
    moe_plugin_default_origin: ALLOW_MOE_PLUGIN_ARTWORK_ORIGIN = 'pixiv'
    # 默认每次查询的图片数量
    moe_plugin_query_image_num: int = 3
    # 允许用户通过参数调整的每次查询的图片数量上限
    moe_plugin_query_image_limit: int = 10
    # 萌图默认自动撤回消息时间(设置 0 为不撤回)
    moe_plugin_moe_auto_recall_time: int = 90
    # 涩图默认自动撤回消息时间(设置 0 为不撤回)
    moe_plugin_setu_auto_recall_time: int = 30

    model_config = ConfigDict(extra='ignore')


try:
    moe_plugin_config = get_plugin_config(MoePluginConfig)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Moe 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Moe 插件配置格式验证失败, {e}')


__all__ = [
    'moe_plugin_config',
]
