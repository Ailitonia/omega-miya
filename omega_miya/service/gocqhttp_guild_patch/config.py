"""
@Author         : Ailitonia
@Date           : 2022/04/17 18:04
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Guild Patch Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from pydantic import BaseModel, ValidationError


class GuildPatchConfig(BaseModel):
    """Guild Patch 配置"""
    enable_guild_event_log: bool = False

    class Config:
        extra = "ignore"


try:
    guild_patch_config = GuildPatchConfig.parse_obj(get_driver().config)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>Guild Patch 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Guild Patch 配置格式验证失败, {e}')


__all__ = [
    'guild_patch_config'
]
