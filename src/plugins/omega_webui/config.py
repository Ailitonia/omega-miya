"""
@Author         : Ailitonia
@Date           : 2025/5/9 17:11:22
@FileName       : config.py
@Project        : omega-miya
@Description    : Omega WebUI 配置
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError


class OmegaWebUIConfig(BaseModel):
    """Omega WebUI 配置"""
    # 启用 WebUI
    enable_omega_webui: bool = False

    model_config = ConfigDict(extra='ignore')


try:
    omega_webui_config = get_plugin_config(OmegaWebUIConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>Omega WebUI 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'Omega WebUI 配置格式验证失败, {e}')

__all__ = [
    'omega_webui_config'
]
