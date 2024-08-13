"""
@Author         : Ailitonia
@Date           : 2024/8/1 14:56:53
@FileName       : config.py
@Project        : omega-miya
@Description    : Danbooru 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class BooruConfig(BaseModel):
    """Booru API 配置"""
    danbooru_username: str | None = None
    danbooru_api_key: str | None = None

    model_config = ConfigDict(extra="ignore")


try:
    booru_config = get_plugin_config(BooruConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Booru API 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Booru API 配置格式验证失败, {e}')


__all__ = [
    'booru_config',
]
