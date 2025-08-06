"""
@Author         : Ailitonia
@Date           : 2025/5/7 15:44:56
@FileName       : omega_webui.py
@Project        : omega-miya
@Description    : Omega WebUI
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.log import logger

from .config import omega_webui_config

if omega_webui_config.enable_omega_webui:
    from . import api as api
    from . import app as app

    logger.success('Omega WebUI 已启用')


__all__ = []
