"""
@Author         : Ailitonia
@Date           : 2025/2/8 16:54:48
@FileName       : consts.py
@Project        : omega-miya
@Description    : Omega API 常量
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal

TOKEN_HEADER_KEY: Literal['X-OmegaApi-Token'] = 'X-OmegaApi-Token'
"""Omega API 身份验证 Token 的 Header Key"""

__all__ = [
    'TOKEN_HEADER_KEY',
]
