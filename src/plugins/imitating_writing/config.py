"""
@Author         : Ailitonia
@Date           : 2025/8/28 14:55:20
@FileName       : config.py
@Project        : omega-miya
@Description    : 模仿写作插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ImitatingWritingPluginConfig(BaseModel):
    """模仿写作插件配置"""

    # 模仿写作使用的 AI 服务名称, 为 None 则使用默认配置
    imitating_writing_plugin_ai_service_name: str | None = Field(default=None)
    # 模仿写作使用的 AI 模型名称, 为 None 则使用默认配置
    imitating_writing_plugin_ai_model_name: str | None = Field(default=None)
    # 生成时的 Temperature 参数值
    imitating_writing_plugin_ai_temperature: float = Field(default=1.0, ge=0, le=2)
    # 生成时的 Max Tokens 参数值
    imitating_writing_plugin_ai_max_tokens: int = Field(default=4096)

    model_config = ConfigDict(extra='ignore')


try:
    imitating_writing_plugin_config = get_plugin_config(ImitatingWritingPluginConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>ImitatingWriting 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'ImitatingWriting 插件配置格式验证失败, {e}')

__all__ = [
    'imitating_writing_plugin_config',
]
