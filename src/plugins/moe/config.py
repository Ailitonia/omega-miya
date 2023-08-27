"""
@Author         : Ailitonia
@Date           : 2021/06/03 22:05
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Moe Plugin Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError

from src.resource import TemporaryResource


class MoePluginConfig(BaseModel):
    """Moe 插件配置"""
    # 查询图片模式, 启用精确匹配可能导致结果减少
    moe_plugin_enable_acc_mode: bool = False
    # 默认每次查询的图片数量
    moe_plugin_query_image_num: int = 3
    # 允许用户通过参数调整的每次查询的图片数量上限
    moe_plugin_query_image_limit: int = 10
    # 萌图默认自动撤回消息时间(设置 0 为不撤回)
    moe_plugin_moe_auto_recall_time: int = 90
    # 涩图默认自动撤回消息时间(设置 0 为不撤回)
    moe_plugin_setu_auto_recall_time: int = 30

    class Config:
        extra = "ignore"


@dataclass
class MoePluginResourceConfig:
    # 缓存处理后图片的位置
    default_processed_image_folder: TemporaryResource = TemporaryResource('pixiv', 'processed')
    # 默认导入图库时读取的 pids 文件路径
    default_database_import_file: TemporaryResource = TemporaryResource('moe_import_pid.txt')


try:
    moe_plugin_config = MoePluginConfig.parse_obj(get_driver().config)
    moe_plugin_resource_config = MoePluginResourceConfig()
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Moe 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Moe 插件配置格式验证失败, {e}')


__all__ = [
    'moe_plugin_config',
    'moe_plugin_resource_config'
]
