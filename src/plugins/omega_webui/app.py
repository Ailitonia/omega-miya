"""
@Author         : Ailitonia
@Date           : 2025/5/8 19:52:49
@FileName       : app.py
@Project        : omega-miya
@Description    : Omega WebUI 应用
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from src.service.omega_api import OmegaAPI

_WEBUI_APP = OmegaAPI('omega_webui')
"""Omega WebUI 应用主体"""


__all__ = []
