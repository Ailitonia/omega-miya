"""
@Author         : Ailitonia
@Date           : 2022/03/30 20:27
@FileName       : __init__.py.py
@Project        : nonebot2_miya 
@Description    : Onebot Api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from ._api import BaseOnebotApi as Onebot
from .gocq import Gocqhttp


__all__ = [
    'Onebot',
    'Gocqhttp'
]
