"""
@Author         : Ailitonia
@Date           : 2021/06/03 22:05
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Moe Plugin Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from dataclasses import dataclass
from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError
from omega_miya.local_resource import TmpResource


class MoePluginConfig(BaseModel):
    """Moe 插件配置"""
    # 允许预览 r18 作品的权限节点
    moe_plugin_allow_r18_node: Literal['allow_r18'] = 'allow_r18'
    # 查询图片模式, 启用精确匹配可能导致结果减少
    moe_plugin_enable_acc_mode: bool = False
    # 默认每次查询的图片数量
    moe_plugin_query_image_num: int = 3
    # 允许用户通过参数调整的每次查询的图片数量上限
    moe_plugin_query_image_limit: int = 10
    # 启用使用闪照模式发送图片
    moe_plugin_enable_flash_mode: bool = True
    # 默认自动撤回消息时间
    moe_plugin_auto_recall_time: int = 30

    class Config:
        extra = "ignore"


@dataclass
class MoePluginResourceConfig:
    # 默认导入图库时读取的 pids 文件路径
    default_database_import_file: TmpResource = TmpResource('moe_import_pid.txt')


try:
    moe_plugin_resource_config = MoePluginResourceConfig()
    moe_plugin_config = MoePluginConfig.parse_obj(get_driver().config)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Moe 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Moe 插件配置格式验证失败, {e}')


__all__ = [
    'moe_plugin_config',
    'moe_plugin_resource_config'
]
