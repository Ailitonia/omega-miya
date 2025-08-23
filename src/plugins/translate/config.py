"""
@Author         : Ailitonia
@Date           : 2025/8/23 14:27:27
@FileName       : config.py
@Project        : omega-miya
@Description    : 翻译插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class TranslatePluginConfig(BaseModel):
    """翻译插件配置"""

    # 翻译时使用的 AI 服务名称, 为 None 则使用默认配置
    translate_plugin_ai_service_name: str | None = Field(default=None)
    # 翻译时使用的 AI 模型名称, 为 None 则使用默认配置
    translate_plugin_ai_model_name: str | None = Field(default=None)

    model_config = ConfigDict(extra='ignore')


try:
    translate_plugin_config = get_plugin_config(TranslatePluginConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>翻译插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'翻译插件配置格式验证失败, {e}')

__all__ = [
    'translate_plugin_config',
]
