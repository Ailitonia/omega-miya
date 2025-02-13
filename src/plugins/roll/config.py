"""
@Author         : Ailitonia
@Date           : 2025/2/13 19:32
@FileName       : config
@Project        : omega-miya
@Description    : 骰子插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class RollPluginConfig(BaseModel):
    """Moe 插件配置"""
    # 允许使用 AI 生成事件描述
    roll_plugin_enable_ai_generate_event: bool = False
    # 使用的 AI 服务名称, 为 None 则使用默认配置
    roll_plugin_enable_ai_service_name: str | None = None
    # 使用的 AI 模型名称, 为 None 则使用默认配置
    roll_plugin_enable_ai_model_name: str | None = None

    model_config = ConfigDict(extra='ignore')


try:
    roll_plugin_config = get_plugin_config(RollPluginConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Roll 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Roll 插件配置格式验证失败, {e}')

__all__ = [
    'roll_plugin_config',
]
