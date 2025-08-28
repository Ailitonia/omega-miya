"""
@Author         : Ailitonia
@Date           : 2025/2/16 20:50
@FileName       : config
@Project        : omega-miya
@Description    : RoguelikeStory 插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class RoguelikeStoryPluginConfig(BaseModel):
    """RoguelikeStory 插件配置"""
    # 使用的 AI 服务名称, 为 None 则使用默认配置
    roguelike_story_plugin_ai_service_name: str | None = Field(default=None)
    # 使用的 AI 模型名称, 为 None 则使用默认配置
    roguelike_story_plugin_ai_model_name: str | None = Field(default=None)
    # 生成时的 Temperature 参数值
    roguelike_story_plugin_ai_temperature: float = Field(default=0.6, ge=0, le=2)
    # 生成时的 Max Tokens 参数值
    roguelike_story_plugin_ai_max_tokens: int = Field(default=4096)
    # 要求返回 JSON 格式, 有助于数据解析, 若 AI 服务不支持 JSON 输出则需要设置为 `None`
    roguelike_story_plugin_ai_json_output: Literal['json_schema', 'json_object', None] = Field(default='json_object')
    # 生成掷骰事件时是否使用 SFW 内容安全提示词
    roguelike_story_plugin_ai_safe_roll: bool = Field(default=True)

    model_config = ConfigDict(extra='ignore')


try:
    roguelike_story_plugin_config = get_plugin_config(RoguelikeStoryPluginConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>RoguelikeStory 插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'RoguelikeStory 插件配置格式验证失败, {e}')

__all__ = [
    'roguelike_story_plugin_config',
]
