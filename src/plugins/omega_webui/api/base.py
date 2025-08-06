"""
@Author         : Ailitonia
@Date           : 2025/5/7 16:32:17
@FileName       : base.py
@Project        : omega-miya
@Description    : Omega WebUI 后端 API 基类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from src.service.omega_api import OmegaAPI

omega_webui_api = OmegaAPI('omega_webui_api', enable_token_verify=True)
"""Omega WebUI 后端 API 主体"""

__all__ = [
    'omega_webui_api',
]
