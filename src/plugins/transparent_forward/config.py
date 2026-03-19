"""
@Author         : Ailitonia
@Date           : 2026/3/19 16:09
@FileName       : config
@Project        : omega-miya
@Description    : 透明转发插件配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class TransparentForwardPluginConfig(BaseModel):
    """TransparentForward 透明转发插件配置"""

    # 验证码缓存时间
    transparent_forward_plugin_verification_code_cache_ttl: int = Field(default=300)

    model_config = ConfigDict(extra='ignore')


try:
    transparent_forward_plugin_config = get_plugin_config(TransparentForwardPluginConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>TransparentForwardPlugin 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'TransparentForwardPlugin 配置格式验证失败, {e}')

__all__ = [
    'transparent_forward_plugin_config',
]
