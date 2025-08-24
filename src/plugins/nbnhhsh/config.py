"""
@Author         : Ailitonia
@Date           : 2025/4/15 16:16:01
@FileName       : config.py
@Project        : omega-miya
@Description    : Nbnhhsh 插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError

type JsonOutputType = Literal['json_schema', 'json_object', None]


class NbnhhshPluginConfig(BaseModel):
    """Nbnhhsh 插件配置"""

    # 是否启用 AI 解释
    nbnhhsh_plugin_enable_ai_description: bool = Field(default=False)

    # 解释时使用的 AI 服务名称, 为 None 则使用默认配置
    nbnhhsh_plugin_ai_description_service_name: str | None = Field(default=None)
    # 解释时使用的 AI 模型名称, 为 None 则使用默认配置
    nbnhhsh_plugin_ai_description_model_name: str | None = Field(default=None)
    # 解释时要求返回 JSON 格式, 有助于数据解析, 若 AI 服务不支持 JSON 输出则需要设置为 `None`
    nbnhhsh_plugin_ai_description_json_output: JsonOutputType = Field(default='json_object')

    # 识别图片时使用的 AI 服务名称, 为 None 则使用默认配置
    nbnhhsh_plugin_ai_vision_service_name: str | None = Field(default=None)
    # 识别图片时使用的 AI 模型名称, 为 None 则使用默认配置
    nbnhhsh_plugin_ai_vision_model_name: str | None = Field(default=None)
    # 识别图片时要求返回 JSON 格式, 有助于数据解析, 若 AI 服务不支持 JSON 输出则需要设置为 `None`
    nbnhhsh_plugin_ai_vision_json_output: JsonOutputType = Field(default='json_object')

    # 生成时的 Temperature 参数值
    nbnhhsh_plugin_ai_temperature: float = Field(default=0.5, ge=0, le=2)
    # 生成时的 Max Tokens 参数值
    nbnhhsh_plugin_ai_max_tokens: int = Field(default=4096)

    model_config = ConfigDict(extra='ignore')


try:
    nbnhhsh_plugin_config = get_plugin_config(NbnhhshPluginConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Nbnhhsh 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Nbnhhsh 插件配置格式验证失败, {e}')

__all__ = [
    'nbnhhsh_plugin_config',
]
