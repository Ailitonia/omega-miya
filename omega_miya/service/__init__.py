"""
@Author         : Ailitonia
@Date           : 2022/04/13 18:47
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : Omega 服务模块, 包括权限、冷却、多 Bot 适配等组件都在这里
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .omega_processor_tools import init_processor_state


__all__ = [
    'init_processor_state'
]
