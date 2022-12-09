"""
@Author         : Ailitonia
@Date           : 2022/12/05 22:22
@FileName       : omega_base.py
@Project        : nonebot2_miya 
@Description    : Omega 基础服务, 封装了常用的数据库操作, 和一些常用工具类函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .internal import InternalEntity
from .adapters import OnebotV11EntityDepend


__all__ = [
    'InternalEntity',
    'OnebotV11EntityDepend'
]
