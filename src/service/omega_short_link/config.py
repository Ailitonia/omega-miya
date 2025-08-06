"""
@Author         : Ailitonia
@Date           : 2025/7/16 17:08:45
@FileName       : config.py
@Project        : omega-miya
@Description    : 短链接服务配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ShortLinkConfig(BaseModel):
    """OmegaShortLink 短链接服务配置"""

    # 启用短链接转发服务
    omega_short_link_enable_http_forward_service: bool = Field(default=False)
    # 外部访问域名
    omega_short_link_access_domain: str | None = Field(default=None)
    # 返回访问 URL 是是否使用 https
    omega_short_link_use_https: bool = Field(default=False)
    # 短链接缓存时间
    omega_short_link_cache_ttl: int = Field(default=86400 * 30)

    model_config = ConfigDict(extra='ignore')


try:
    short_link_config = get_plugin_config(ShortLinkConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>OmegaShortLink 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'OmegaShortLink 配置格式验证失败, {e}')

__all__ = [
    'short_link_config',
]
