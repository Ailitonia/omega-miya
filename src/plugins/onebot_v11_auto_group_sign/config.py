"""
@Author         : Ailitonia
@Date           : 2023/7/15 20:01
@FileName       : config
@Project        : nonebot2_miya
@Description    : 自动群打卡配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class AutoGroupSignConfig(BaseModel):
    """自动群打卡插件配置"""
    # 启用自动群打卡
    enable_auto_group_sign: bool = False
    # 自动群打卡延迟(每日零时之后, 单位秒)
    auto_group_sign_delay: int = 0

    model_config = ConfigDict(extra="ignore")


try:
    auto_group_sign_config = get_plugin_config(AutoGroupSignConfig)
except ValidationError as e:
    import sys
    logger.opt(colors=True).critical(f'<r>自动群打卡插件配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'自动群打卡插件配置格式验证失败, {e}')


__all__ = [
    'auto_group_sign_config'
]
